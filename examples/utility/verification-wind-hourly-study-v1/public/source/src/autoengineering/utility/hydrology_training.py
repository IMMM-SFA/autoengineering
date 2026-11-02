"""Offline contracts and cost reconstruction for conservative routing training."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest
from .contracts import identifier, sha256
from .costs import CostRecord
from .exposure import iso_date


def routing_training_identity(model, parameters, seed, profile):
    """Identity of the fixed learned routing profile, independent of replay length."""
    site = model.implementations.get("site")
    sha256(site)
    if (
        type(seed) is not int
        or seed < 0
        or set(parameters) != {"capacity", "pet"}
        or parameters["pet"] not in ("hamon", "hargreaves")
        or type(parameters["capacity"]) not in (int, float)
        or not 20 <= parameters["capacity"] <= 200
    ):
        raise ValueError("learned routing parameters or seed differ")
    implementations = {
        "site": site,
        "pet": parameters["pet"],
        "soil": "bucket-v1",
        "routing": "logistic-storage-release-v1",
        "training": profile.digest,
    }
    if dict(model.implementations) != implementations or model.graph_digest != digest(
        {"site": site, "routing": "logistic-storage-release-v1", "training": profile.digest}
    ):
        raise ValueError("learned routing graph or implementation identity differs")
    return digest(
        {
            "site": site,
            "training": profile.digest,
            "graph": model.graph_digest,
            "implementations": dict(model.implementations),
            "sources": [r.to_dict() for r in model.source_bundle],
            "environment": model.dependency_bundle,
            "parameters": dict(parameters),
            "seed": seed,
            "initialization": "soil=capacity/2;reservoir=0",
        }
    )


@dataclass(frozen=True)
class RoutingTrainingProfile(Record):
    fitting_dates: tuple[str, ...]
    warmup_rows: int
    valid_mask: tuple[bool, ...]
    max_rollouts: int
    schema: Literal["learned-hydrology-training-profile-v1"] = (
        "learned-hydrology-training-profile-v1"
    )

    def _validate(self):
        dates = [iso_date(day) for day in self.fitting_dates]
        if not 20 <= len(dates) <= 20000 or any(
            (b - a).days != 1 for a, b in zip(dates, dates[1:])
        ):
            raise ValueError("training requires a bounded contiguous daily prefix")
        if (
            not 0 <= self.warmup_rows < len(dates)
            or len(self.valid_mask) != len(dates)
            or any(self.valid_mask[: self.warmup_rows])
            or sum(self.valid_mask) < 20
        ):
            raise ValueError("training requires at least 20 usable fitting labels outside warmup")
        if not 3 <= self.max_rollouts <= 1000:
            raise ValueError("training rollout cap must be between 3 and 1000")


@dataclass(frozen=True)
class RoutingFit(Record):
    identity: str
    fitting_data_digest: str
    fitting_forcing_digest: str
    coefficients: tuple[float, ...]
    seed: int
    routing_rollouts: int
    simulated_days: int
    flux_preparation_runs: int
    training_seconds: float
    scipy_version: str
    algorithm: str = "bounded-trf-least-squares-v1"
    cost_unit: str = "routing_rollouts"
    feature: str = "log1p(available_reservoir_mm/100)"
    schema: Literal["learned-hydrology-fit-v1"] = "learned-hydrology-fit-v1"

    def _validate(self):
        from autoengineering.utility.contracts import sha256

        for value in (self.identity, self.fitting_data_digest, self.fitting_forcing_digest):
            sha256(value)
        if len(self.coefficients) != 2 or not (
            -6 <= self.coefficients[0] <= 6 and 0 <= self.coefficients[1] <= 3
        ):
            raise ValueError("trained routing coefficients outside supported bounds")
        if self.routing_rollouts < 1 or self.simulated_days < 1 or self.flux_preparation_runs != 1:
            raise ValueError("invalid training work record")
        if self.training_seconds < 0 or not self.scipy_version:
            raise ValueError("invalid training duration or environment")
        if (
            self.algorithm != "bounded-trf-least-squares-v1"
            or self.cost_unit != "routing_rollouts"
            or self.feature != "log1p(available_reservoir_mm/100)"
        ):
            raise ValueError("unsupported training algorithm, cost unit or feature")


@dataclass(frozen=True)
class TrainingIntent(Record):
    schema: Literal["learned-routing-training-intent-v2"]
    training_id: str
    identity: str
    seed: int
    max_rollouts: int
    fitting_days: int

    def _validate(self):
        identifier(self.training_id)
        sha256(self.identity)
        if not 3 <= self.max_rollouts <= 1000 or not 20 <= self.fitting_days <= 20000:
            raise ValueError("invalid training intent limits")


@dataclass(frozen=True)
class TrainingWork(Record):
    schema: Literal["learned-routing-training-result-v2"]
    training_id: str
    identity: str
    status: Literal["trained", "failed"]
    training_seconds: float
    routing_rollouts: int
    reserved_routing_days: int
    completed_routing_rollouts: int
    completed_routing_days: int
    partial_routing_work_unknown: bool
    flux_preparation_runs: int
    completed_flux_preparation_runs: int
    partial_flux_work_unknown: bool
    trained_artifact: ArtifactRef | None

    def _validate(self):
        identifier(self.training_id)
        sha256(self.identity)
        if (
            self.training_seconds < 0
            or not 0 <= self.completed_routing_rollouts <= self.routing_rollouts
            or self.routing_rollouts > 1000
            or min(self.reserved_routing_days, self.completed_routing_days) < 0
            or not 0 <= self.completed_flux_preparation_runs <= self.flux_preparation_runs <= 1
        ):
            raise ValueError("invalid training work quantities")
        if self.partial_routing_work_unknown != (
            self.routing_rollouts != self.completed_routing_rollouts
        ) or self.partial_flux_work_unknown != (
            self.flux_preparation_runs != self.completed_flux_preparation_runs
        ):
            raise ValueError("training partial-work flags differ from counts")
        if (self.status == "trained") != (self.trained_artifact is not None):
            raise ValueError("training artifact and terminal status differ")
        if self.routing_rollouts and self.completed_flux_preparation_runs != 1:
            raise ValueError("routing work precedes completed flux preparation")
        if self.status == "trained" and (
            self.partial_flux_work_unknown
            or self.partial_routing_work_unknown
            or self.completed_flux_preparation_runs != 1
            or self.completed_routing_rollouts < 1
        ):
            raise ValueError("trained result has incomplete work")


def read_training_costs(
    root: Path,
    intent_ref: ArtifactRef,
    result_ref: ArtifactRef | None,
    *,
    identity: str,
    profile: RoutingTrainingProfile,
    seed: int,
    cell_digest: str,
) -> tuple[CostRecord, ...]:
    """Reconstruct one committed attempt, without sources, labels or model imports.

    Callers supply authoritative committed references and the frozen expected
    identity/profile/seed. This reader does not establish process supervision or
    decide which references a campaign committed. A missing result is unresolved.
    """
    if not isinstance(profile, RoutingTrainingProfile) or type(seed) is not int:
        raise ValueError("training reader requires the frozen profile and integer seed")
    sha256(identity)
    sha256(cell_digest)
    intent = TrainingIntent.from_json(read_bytes(root, intent_ref, max_bytes=65536).decode())
    if (
        intent.identity != identity
        or intent.seed != seed
        or intent.max_rollouts != profile.max_rollouts
        or intent.fitting_days != len(profile.fitting_dates)
    ):
        raise ValueError("training intent differs from frozen identity or limits")
    work = None
    if result_ref is not None:
        work = TrainingWork.from_json(read_bytes(root, result_ref, max_bytes=65536).decode())
        n = intent.fitting_days
        if (
            work.identity != identity
            or work.training_id != intent.training_id
            or work.routing_rollouts > intent.max_rollouts
            or work.reserved_routing_days != work.routing_rollouts * n
            or work.completed_routing_days != work.completed_routing_rollouts * n
        ):
            raise ValueError("training result differs from its original intent")
        if work.trained_artifact is not None:
            fit = RoutingFit.from_json(
                read_bytes(root, work.trained_artifact, max_bytes=65536).decode()
            )
            if (
                fit.identity != identity
                or fit.seed != seed
                or fit.routing_rollouts != work.routing_rollouts
                or fit.simulated_days != work.completed_routing_days
                or fit.flux_preparation_runs != work.completed_flux_preparation_runs
                or fit.training_seconds > work.training_seconds
            ):
                raise ValueError("frozen fit differs from its training work")
    quantities = {
        "training_starts": ("count", 1.0),
        "training_routing_starts": (
            "count",
            None if work is None else float(work.routing_rollouts),
        ),
        "training_routing_completions": (
            "count",
            None if work is None else float(work.completed_routing_rollouts),
        ),
        "training_reserved_routing_days": (
            "count",
            None if work is None else float(work.reserved_routing_days),
        ),
        "training_completed_routing_days": (
            "count",
            None if work is None else float(work.completed_routing_days),
        ),
        "training_flux_starts": (
            "count",
            None if work is None else float(work.flux_preparation_runs),
        ),
        "training_flux_completions": (
            "count",
            None if work is None else float(work.completed_flux_preparation_runs),
        ),
        "training_elapsed": ("s", None if work is None else work.training_seconds),
        "training_partial_routing_days": (
            "count",
            None if work is None or work.partial_routing_work_unknown else 0.0,
        ),
        "training_partial_flux_days": (
            "count",
            None if work is None or work.partial_flux_work_unknown else 0.0,
        ),
    }
    return tuple(
        CostRecord(
            "training-cost-" + digest({"source": intent_ref.sha256, "resource": name})[:48],
            intent_ref.sha256,
            "training",
            name,
            units,
            value,
            (cell_digest,),
            (1.0,),
        )
        for name, (units, value) in quantities.items()
    )
