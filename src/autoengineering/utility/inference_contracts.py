"""Metadata contracts for frozen routing inference; no driver reads or execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef, DataContract, TimeContract
from autoengineering.campaign.serialization import Record, digest, unique_json
from .hydrology_training import RoutingTrainingProfile


@dataclass(frozen=True)
class FrozenRoutingInference(Record):
    schema: Literal["utility-frozen-routing-inference-v1"]
    selected_state: ArtifactRef
    runtime_profile: ArtifactRef
    forcing: DataContract
    seed: int
    timeout_seconds: float
    output_limit_bytes: int

    def _validate(self):
        if self.seed < 0 or not 0 < self.timeout_seconds <= 60:
            raise ValueError("frozen inference needs a nonnegative seed and bounded timeout")
        if not 0 < self.output_limit_bytes <= 64 * 1024 * 1024:
            raise ValueError("frozen inference output limit exceeds its supported bound")
        if (
            self.selected_state.media_type != "application/json"
            or self.runtime_profile.media_type != "application/json"
        ):
            raise ValueError("frozen inference requires JSON state and runtime metadata")
        if (
            self.forcing.role != "forcing"
            or self.forcing.prior_exposure == "unknown"
            or self.forcing.artifact.media_type != "application/x-npz"
            or self.forcing.artifact.size_bytes > 64 * 1024 * 1024
        ):
            raise ValueError("frozen inference permits only bounded NPZ forcing")
        if any(
            not isinstance(p.time, TimeContract) or len(p.time.dates) > 20000
            for p in self.forcing.ports
        ):
            raise ValueError("frozen routing inference requires bounded daily drivers")

    @property
    def minimum_reserved_seconds(self):
        # Existing private vector lifecycle: 64 s. Model stop grace: 5 + 5 s.
        return self.timeout_seconds + 74.0

    def validate_selection(self, root, selected_ref, bound):
        from .confirmation import TrainedSelectedState

        if self.selected_state != selected_ref or not isinstance(bound, TrainedSelectedState):
            raise ValueError("frozen inference differs from the trained selected state")
        if bound.evaluation.provenance.get("execution_seed") != str(self.seed):
            raise ValueError("frozen inference seed differs from the original fit")
        original = bound.model.inputs
        if len(original) != len(self.forcing.ports):
            raise ValueError("frozen inference driver interface differs from selection")
        first = self.forcing.ports[0].time
        for old, new in zip(original, self.forcing.ports):
            clock = new.time
            if not isinstance(old.time, TimeContract) or new != replace(old, time=clock):
                raise ValueError("frozen inference driver semantics differ from selection")
            prefix = len(old.time.dates)
            if (
                clock.dates[:prefix] != old.time.dates
                or clock.warmup_mask
                != old.time.warmup_mask + (False,) * (len(clock.dates) - prefix)
                or clock
                != replace(
                    old.time,
                    dates=clock.dates,
                    warmup_mask=clock.warmup_mask,
                    scoring_mask=clock.scoring_mask,
                )
                or (clock.dates, clock.warmup_mask, clock.scoring_mask)
                != (first.dates, first.warmup_mask, first.scoring_mask)
            ):
                raise ValueError("frozen inference daily replay or initialization differs")
        document = unique_json(
            read_bytes(root, self.runtime_profile, max_bytes=4 * 1024 * 1024).decode()
        )
        if (
            not isinstance(document, dict)
            or set(document) != {"schema", "site", "training_profile", "selected_state"}
            or document["schema"] != "utility-routing-runtime-v1"
        ):
            raise ValueError("frozen inference runtime profile is unsupported")
        if ArtifactRef.from_dict(document["selected_state"]) != self.selected_state:
            raise ValueError("frozen inference runtime profile names another selection")
        profile = RoutingTrainingProfile.from_dict(document["training_profile"])
        original_profile = RoutingTrainingProfile.from_json(
            read_bytes(root, bound.training.profile, max_bytes=4 * 1024 * 1024).decode()
        )
        if (
            profile != original_profile
            or profile.digest != bound.model.implementations.get("training")
            or digest(document["site"]) != bound.model.implementations.get("site")
        ):
            raise ValueError("frozen inference runtime profile differs from its original fit")
