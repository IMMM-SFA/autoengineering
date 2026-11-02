"""Offline closure checks for the initial learned-routing selection profile."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import math
from typing import Literal

from autoengineering.adapters.contracts import TrainingArtifactBundle, TrainingResult
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef, TimeContract
from autoengineering.campaign.serialization import Record, unique_json
from .hydrology_training import (
    RoutingTrainingProfile,
    TrainingWork,
    read_training_costs,
    routing_training_identity,
)


@dataclass(frozen=True)
class RoutingSelectionArtifacts(Record):
    schema: Literal["utility-routing-selection-artifacts-v1"]
    fit: ArtifactRef
    profile: ArtifactRef
    intent: ArtifactRef
    result: ArtifactRef
    bundle: ArtifactRef
    lifecycle: ArtifactRef

    def _validate(self):
        refs = self.references()
        if len({r.path for r in refs}) != len(refs):
            raise ValueError("trained selection needs distinct closure artifacts")
        for ref in refs:
            if (
                ref.media_type != "application/json"
                or len(Path(ref.path).parts) != 3
                or Path(ref.path).parts[:2] != ("artifacts", ref.sha256)
            ):
                raise ValueError("trained selection requires portable JSON artifacts")

    def references(self):
        return (self.fit, self.profile, self.intent, self.result, self.bundle, self.lifecycle)


def verify_routing_selection(root, bound):
    """Verify bytes and selected scientific identity, without model imports or fitting.

    Child attestation remains the parent authority at suite sealing. This function
    does not assert that an execution profile has been admitted or supervised.
    """
    refs = bound.training
    if sum(ref.size_bytes for ref in (refs.profile, refs.intent, refs.result)) > 4 * 1024 * 1024:
        raise ValueError("trained selection companion bytes exceed the parent capture limit")
    raw = {
        ref.path: read_bytes(root, ref, max_bytes=4 * 1024 * 1024 if ref == refs.profile else 65536)
        for ref in refs.references()
    }
    profile = RoutingTrainingProfile.from_json(raw[refs.profile.path].decode())
    bundle = TrainingArtifactBundle.from_json(raw[refs.bundle.path].decode())
    if bundle.primary != refs.fit or {r.to_json() for r in bundle.companions} != {
        r.to_json() for r in (refs.profile, refs.intent, refs.result)
    }:
        raise ValueError("trained selection bundle differs from its closure")
    work = TrainingWork.from_json(raw[refs.result.path].decode())
    if work.status != "trained" or work.trained_artifact != refs.fit:
        raise ValueError("trained selection lacks a successful original training result")
    lifecycle = unique_json(raw[refs.lifecycle.path].decode())
    if not isinstance(lifecycle, dict):
        raise ValueError("trained selection lifecycle must be a mapping")
    if (
        lifecycle.get("schema_version") != "2.0"
        or refs.lifecycle.producer != bound.evaluation.attempt_id
        or refs.lifecycle.sha256 != bound.evaluation.provenance.get("lifecycle_record")
    ):
        raise ValueError("trained selection lifecycle belongs to another evaluation")
    seconds = lifecycle.get("elapsed_seconds")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("trained selection lifecycle duration is invalid")
    if (
        len(
            [
                ref
                for ref in bound.evaluation.outputs
                if ref.sha256 == lifecycle.get("output_sha256")
            ]
        )
        != 1
    ):
        raise ValueError("trained selection lifecycle output differs from its evaluation")
    training = TrainingResult.from_dict(lifecycle["training"])
    if TrainingResult.from_dict(lifecycle["worker_training"]) != training:
        raise ValueError("trained selection portable worker and parent references differ")
    if training.artifact is None:
        raise ValueError("trained selection lifecycle has no frozen fit")
    bundle_text = training.artifact.metadata.get("training_bundle")
    if not isinstance(bundle_text, str) or ArtifactRef.from_json(bundle_text) != refs.bundle:
        raise ValueError("trained selection lifecycle names another bundle")
    primary = replace(
        training.artifact,
        metadata={k: v for k, v in training.artifact.metadata.items() if k != "training_bundle"},
    )
    if primary != refs.fit:
        raise ValueError("trained selection lifecycle names another fit")
    seed_text = bound.evaluation.provenance.get("execution_seed", "")
    if not seed_text.isascii() or not seed_text.isdigit() or str(int(seed_text)) != seed_text:
        raise ValueError("trained selection lacks its canonical execution seed")
    if not bound.model.inputs:
        raise ValueError("trained selection has no daily meteorological interface")
    clock = bound.model.inputs[0].time
    if not bound.model.inputs[0].grid_id:
        raise ValueError("trained selection requires its declared basin grid")
    if (
        not isinstance(clock, TimeContract)
        or clock.dates[: len(profile.fitting_dates)] != profile.fitting_dates
        or clock.warmup_mask
        != (True,) * profile.warmup_rows + (False,) * (len(clock.dates) - profile.warmup_rows)
    ):
        raise ValueError("trained selection fitting prefix or initialization differs")
    inputs = {
        "precip_mm": ("mm", "interval_total"),
        "tmean_c": ("degC", "interval_mean"),
        "tmax_c": ("degC", "instantaneous"),
        "tmin_c": ("degC", "instantaneous"),
        "day_of_year": ("day", "instantaneous"),
    }
    outputs = {
        "prediction": ("mm/day", "interval_mean"),
        "aet": ("mm/day", "interval_mean"),
        "pet": ("mm/day", "interval_mean"),
        "soil": ("mm", "instantaneous"),
        "reservoir": ("mm", "instantaneous"),
        "initial_soil": ("mm", None),
        "initial_reservoir": ("mm", None),
    }
    if {p.name for p in bound.model.inputs} != set(inputs) or {
        p.name for p in bound.model.outputs
    } != set(outputs):
        raise ValueError("trained selection daily interface differs")
    for port in (*bound.model.inputs, *bound.model.outputs):
        units, semantics = (inputs | outputs)[port.name]
        expected = (
            None
            if semantics is None
            else replace(
                clock,
                semantics=semantics,
                timestamp="end" if port.name in ("soil", "reservoir") else "start",
            )
        )
        if (
            port.units != units
            or port.time != expected
            or port.dimensions != (() if expected is None else ("time",))
            or port.dtype_family != "numeric"
            or port.coordinates
            or port.coordinate_digest != bound.model.implementations["site"]
            or port.grid_id != bound.model.inputs[0].grid_id
        ):
            raise ValueError("trained selection port units, timing or site metadata differ")
    identity = routing_training_identity(bound.model, bound.configuration, int(seed_text), profile)
    costs = read_training_costs(
        root,
        refs.intent,
        refs.result,
        identity=identity,
        profile=profile,
        seed=int(seed_text),
        cell_digest="0" * 64,
    )
    if any(r.quantity is None for r in costs):
        raise ValueError("trained selection has unresolved training work")
    if training.status == "trained":
        count = next(r.quantity for r in costs if r.resource == "training_routing_starts")
        if training.cost != count:
            raise ValueError("selected training cost differs from the original receipt")
        if work.training_seconds > seconds:
            raise ValueError("training work exceeds its enclosing lifecycle duration")
    elif training.cost is not None:
        raise ValueError("frozen inference cannot declare another training cost")
    return refs.references()
