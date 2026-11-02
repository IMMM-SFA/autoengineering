"""Declared local routing runtime; independent task admission remains separate."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from autoengineering.adapters.contracts import AdapterRegistration
from autoengineering.campaign.artifacts import put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record
from autoengineering.campaign.store import checked_directory
from autoengineering.utility.confirmation import TrainedSelectedState, read_selected_state
from autoengineering.utility.hydrology_training import RoutingTrainingProfile
from .hydrology_learned import LearnedRoutingAdapter, load_training
from .hydrology_site import HydrologySite

ADAPTER_ID = "hydrology-learned-routing-v1"
PROFILE_PATH = "routing-runtime.json"
SOURCES = (
    "examples/leaf_river/models/__init__.py",
    "examples/campaign_contracts/hydrology.py",
    "examples/leaf_river/models/pet_hamon.py",
    "examples/leaf_river/models/pet_hargreaves.py",
    "examples/leaf_river/models/soil_moisture.py",
    "examples/utility/hydrology_partitions.py",
    "examples/utility/hydrology_site.py",
    "examples/utility/hydrology_learned.py",
    "examples/utility/hydrology_runtime.py",
)


@dataclass(frozen=True)
class RoutingRuntimeProfile(Record):
    schema: Literal["utility-routing-runtime-v1"]
    site: HydrologySite
    training_profile: RoutingTrainingProfile
    selected_state: ArtifactRef | None


class RegisteredRoutingAdapter(LearnedRoutingAdapter):
    def __init__(self, profile, root, selected):
        self.source_root = root
        self.selected = selected
        frozen = None
        if selected is not None:
            fit = replace(
                selected.training.fit,
                metadata=dict(selected.training.fit.metadata)
                | {
                    "training_bundle": selected.training.bundle.to_json(),
                },
            )
            frozen = load_training(root, fit)
        super().__init__(profile.site, profile.training_profile, frozen)

    def prepare(self, context):
        if self.selected is not None:
            # Capture later uses only this attempt's scratch, never original roots.
            artifacts = Path(context.scratch_path) / "artifacts"
            artifacts.mkdir(mode=0o700, exist_ok=True)
            checked_directory(artifacts)
            for ref in self.selected.training.references():
                saved = put_bytes(
                    Path(context.scratch_path),
                    read_bytes(self.source_root, ref),
                    name=Path(ref.path).name,
                    media_type=ref.media_type,
                    producer=ref.producer,
                )
                if saved.path != ref.path or saved.sha256 != ref.sha256:
                    raise ValueError("frozen routing closure is not portable")
        return super().prepare(context)


def registration(spec, root, runtime_root):
    declared = {r.path: r for r in spec.provenance.sources}
    ref = declared.get(PROFILE_PATH)
    if ref is None or ref.media_type != "application/json":
        raise ValueError("learned routing requires its declared runtime profile")
    profile = RoutingRuntimeProfile.from_json(
        read_bytes(root, ref, max_bytes=4 * 1024 * 1024).decode()
    )
    trained = spec.training is not None and ADAPTER_ID in spec.training.adapter_ids
    selected = None
    if profile.selected_state is None:
        if not trained:
            raise ValueError("learned routing requires explicit fitting permission")
        fitting = next(d for d in spec.data if d.id == spec.training.fitting_data_id)
        clock = fitting.ports[0].time
        if (
            clock.dates != profile.training_profile.fitting_dates
            or clock.scoring_mask != profile.training_profile.valid_mask
            or sum(clock.warmup_mask) != profile.training_profile.warmup_rows
        ):
            raise ValueError("runtime training profile differs from its fitting grant")
    else:
        if trained:
            raise ValueError("frozen routing inference cannot receive fitting permission")
        if declared.get(profile.selected_state.path) != profile.selected_state:
            raise ValueError("frozen routing selection is absent from declared closure")
        selected = read_selected_state(root, profile.selected_state)
        if not isinstance(selected, TrainedSelectedState):
            raise ValueError("frozen routing requires a trained selected state")
        for artifact in selected.training.references():
            if declared.get(artifact.path) != artifact:
                raise ValueError("frozen routing training closure is not declared")
        original = RoutingTrainingProfile.from_json(
            read_bytes(root, selected.training.profile).decode()
        )
        if original != profile.training_profile:
            raise ValueError("frozen routing profile differs from its original fit")

    def factory():
        from importlib import import_module

        # The registry checks every declared module's loaded source location.
        # Include the preparation bridge even when this attempt only infers.
        for path in SOURCES:
            module = path.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
            import_module(module)
        return RegisteredRoutingAdapter(profile, root, selected)

    return AdapterRegistration(ADAPTER_ID, "1", factory, SOURCES, source_root=runtime_root)
