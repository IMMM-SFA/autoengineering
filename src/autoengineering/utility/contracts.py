"""Immutable, identity-bound utility matrices and explicit resource caps."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Literal

from autoengineering.campaign.serialization import Record


def identifier(value: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,95}", value):
        raise ValueError("identifier must be a lowercase portable name")


def sha256(value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("identity must be a SHA-256 digest")


def unique(values: tuple[str, ...], label: str) -> None:
    if not values or len(set(values)) != len(values):
        raise ValueError(f"{label} must be nonempty and unique")


@dataclass(frozen=True)
class ResourceCap(Record):
    name: str
    units: Literal["count", "s", "USD", "CPU-s", "GPU-s"]
    limit: float
    enforcement: Literal["reservation", "observed"]

    def _validate(self):
        identifier(self.name)
        if self.limit < 0:
            raise ValueError("resource limits must be nonnegative")
        if self.units == "count" and self.limit != int(self.limit):
            raise ValueError("count limits must be integral")


@dataclass(frozen=True)
class BudgetSpec(Record):
    regime: Literal["fixed_evaluations", "fixed_total_cost"]
    caps: tuple[ResourceCap, ...]
    confirmation_reserve: tuple[ResourceCap, ...]

    def _validate(self):
        unique(tuple(c.name for c in self.caps), "resource caps")
        required = {"scientific_starts", "host_invocations", "training_starts", "active_time"}
        caps = {c.name: c for c in self.caps}
        if not required <= caps.keys():
            raise ValueError("budget needs scientific, host, training and active-time caps")
        for name in required:
            cap = caps[name]
            units = "s" if name == "active_time" else "count"
            if cap.units != units or cap.enforcement != "reservation":
                raise ValueError("required caps must use reserved counts or seconds")
        names = tuple(c.name for c in self.confirmation_reserve)
        if len(names) != len(set(names)):
            raise ValueError("duplicate confirmation reserve")
        for reserve in self.confirmation_reserve:
            cap = caps.get(reserve.name)
            if (
                cap is None
                or cap.units != reserve.units
                or cap.enforcement != reserve.enforcement
                or reserve.limit > cap.limit
            ):
                raise ValueError("confirmation reserve must fit the matching total cap")
        if not any(
            c.name == "scientific_starts" and c.limit > 0 for c in self.confirmation_reserve
        ):
            raise ValueError("confirmation needs an explicit scientific-start reserve")


@dataclass(frozen=True)
class TaskSpec(Record):
    task_id: str
    family: Literal["hydrology", "solar", "engineering", "wind", "hybrid"]
    dossier_digest: str
    partition_digest: str
    outcome_digest: str
    candidate_digests: tuple[str, ...]
    required_capabilities: tuple[str, ...]

    @classmethod
    def from_dict(cls, value):
        if (
            cls is TaskSpec
            and isinstance(value, Mapping)
            and value.get("schema") == "utility-task-scoring-v2"
        ):
            return ScoredTaskSpec.from_dict(value)
        return super().from_dict(value)

    @property
    def scoring_outcome_identity(self):
        """Legacy tasks keep their original direct outcome binding."""
        return self.outcome_digest

    def _validate(self):
        identifier(self.task_id)
        for value in (self.dossier_digest, self.partition_digest, self.outcome_digest):
            sha256(value)
        unique(self.candidate_digests, "candidates")
        for value in self.candidate_digests:
            sha256(value)
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise ValueError("duplicate required capability")
        for value in self.required_capabilities:
            identifier(value)


@dataclass(frozen=True)
class ScoredTaskSpec(TaskSpec):
    """Preserve selection acceptance and separately bind a confirmation outcome."""

    schema: Literal["utility-task-scoring-v2"]
    scoring_outcome_digest: str

    def _validate(self):
        super()._validate()
        sha256(self.scoring_outcome_digest)

    @property
    def scoring_outcome_identity(self):
        return self.scoring_outcome_digest


@dataclass(frozen=True)
class RouteSpec(Record):
    route_id: str
    kind: Literal[
        "baseline",
        "conventional",
        "single_agent",
        "multi_agent",
        "no_investigator",
        "no_implementer",
        "no_reviewer",
        "expert",
    ]
    configuration_digest: str
    grants_digest: str

    def _validate(self):
        identifier(self.route_id)
        sha256(self.configuration_digest)
        sha256(self.grants_digest)


@dataclass(frozen=True)
class ComparisonCell(Record):
    task_id: str
    route_id: str
    regime: Literal["fixed_evaluations", "fixed_total_cost"]
    repetition: int
    seed: int
    scenario_digest: str

    def _validate(self):
        identifier(self.task_id)
        identifier(self.route_id)
        sha256(self.scenario_digest)
        if self.repetition < 0 or not 0 <= self.seed < 2**63:
            raise ValueError("invalid repetition or seed")

    @property
    def pair_key(self) -> tuple:
        return self.task_id, self.regime, self.repetition, self.scenario_digest


@dataclass(frozen=True)
class BaselineReuseGroup(Record):
    cell_digests: tuple[str, ...]
    source_cell_digest: str
    model_digest: str
    configuration_digest: str
    scorer_digest: str
    allocation: tuple[float, ...]

    def _validate(self):
        unique(self.cell_digests, "baseline reuse cells")
        for value in (
            *self.cell_digests,
            self.source_cell_digest,
            self.model_digest,
            self.configuration_digest,
            self.scorer_digest,
        ):
            sha256(value)
        if len(self.cell_digests) < 2 or self.source_cell_digest not in self.cell_digests:
            raise ValueError("baseline reuse needs a source and at least one follower")
        if (
            len(self.allocation) != len(self.cell_digests)
            or any(v < 0 for v in self.allocation)
            or abs(sum(self.allocation) - 1.0) > 1e-12
        ):
            raise ValueError("baseline reuse allocations must align and sum to one")


@dataclass(frozen=True)
class BaselineReusePolicy(Record):
    schema: Literal["utility-baseline-reuse-v1", "utility-baseline-reuse-v2"]
    comparison_protocol_digest: str
    groups: tuple[BaselineReuseGroup, ...]
    profile: Literal["deterministic_frozen_reference"] = "deterministic_frozen_reference"
    on_failure: Literal["retain_source_leave_followers_unscored"] = (
        "retain_source_leave_followers_unscored"
    )

    selection_reuse: Literal["none", "frozen_reference"] = "none"

    def to_dict(self):
        result = super().to_dict()
        if self.selection_reuse == "none":
            result.pop("selection_reuse")
        return result

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("schema") == "utility-baseline-reuse-v1"
            and "selection_reuse" in value
        ):
            raise ValueError("legacy baseline policy rejects selection reuse fields")
        return super().from_dict(value)

    def _validate(self):
        if (self.schema == "utility-baseline-reuse-v2") != (
            self.selection_reuse == "frozen_reference"
        ):
            raise ValueError("selection reuse requires explicit baseline policy v2")
        sha256(self.comparison_protocol_digest)
        if not self.groups:
            raise ValueError("baseline reuse requires explicit groups")
        cells = tuple(c for group in self.groups for c in group.cell_digests)
        unique(cells, "nonoverlapping baseline reuse cells")


@dataclass(frozen=True)
class UtilitySuiteSpec(Record):
    schema: Literal["utility-suite-v1", "utility-suite-v2"]
    suite_id: str
    tasks: tuple[TaskSpec, ...]
    routes: tuple[RouteSpec, ...]
    budgets: tuple[BudgetSpec, ...]
    cells: tuple[ComparisonCell, ...]
    source_digest: str
    lock_digest: str
    analysis_digest: str
    exposure_digest: str
    protocol_digest: str
    baseline_reuse: BaselineReusePolicy | None = None

    def to_dict(self):
        result = super().to_dict()
        if self.baseline_reuse is None:
            result.pop("baseline_reuse")
        return result

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("schema") == "utility-suite-v1"
            and "baseline_reuse" in value
        ):
            raise ValueError("legacy suite rejects baseline reuse fields")
        return super().from_dict(value)

    def _validate(self):
        identifier(self.suite_id)
        for value in (
            self.source_digest,
            self.lock_digest,
            self.analysis_digest,
            self.exposure_digest,
            self.protocol_digest,
        ):
            sha256(value)
        if (self.schema == "utility-suite-v2") != (self.baseline_reuse is not None):
            raise ValueError("baseline reuse requires explicit suite schema v2")
        if self.baseline_reuse is not None and self.protocol_digest != self.baseline_reuse.digest:
            raise ValueError("baseline reuse differs from frozen protocol")
        unique(tuple(t.task_id for t in self.tasks), "tasks")
        unique(tuple(r.route_id for r in self.routes), "routes")
        unique(tuple(b.regime for b in self.budgets), "regimes")
        unique(tuple(c.digest for c in self.cells), "cells")
        tasks = {t.task_id for t in self.tasks}
        routes = {r.route_id for r in self.routes}
        regimes = {b.regime for b in self.budgets}
        keys = set()
        pairs = {}
        for cell in self.cells:
            if (
                cell.task_id not in tasks
                or cell.route_id not in routes
                or cell.regime not in regimes
            ):
                raise ValueError("cell references an unknown task, route or regime")
            key = (cell.task_id, cell.route_id, cell.regime, cell.repetition)
            if key in keys:
                raise ValueError("conflicting cell ID")
            keys.add(key)
            block = (cell.task_id, cell.regime, cell.repetition)
            pair = (cell.seed, cell.scenario_digest)
            if block in pairs and pairs[block] != pair:
                raise ValueError("paired routes must share seed and scenario")
            pairs[block] = pair
        for task, regime, repetition in pairs:
            if any((task, route, regime, repetition) not in keys for route in routes):
                raise ValueError("paired blocks must contain every assigned route")
        if {c.task_id for c in self.cells} != tasks or {c.regime for c in self.cells} != regimes:
            raise ValueError("matrix must cover every assigned task and regime")
        adaptive = [r for r in self.routes if r.kind not in ("baseline", "expert")]
        if len({r.grants_digest for r in adaptive}) > 1:
            raise ValueError("adaptive routes must receive equivalent scientific grants")

        if self.baseline_reuse is not None:
            by_cell = {c.digest: c for c in self.cells}
            by_route = {r.route_id: r for r in self.routes}
            by_task = {t.task_id: t for t in self.tasks}
            for group in self.baseline_reuse.groups:
                assigned = [by_cell.get(c) for c in group.cell_digests]
                if any(c is None or by_route[c.route_id].kind != "baseline" for c in assigned):
                    raise ValueError("baseline reuse requires assigned unchanged-baseline cells")
                if len({(c.task_id, c.scenario_digest) for c in assigned}) != 1:
                    raise ValueError("baseline reuse requires the same task and scenario")
                if self.baseline_reuse.selection_reuse == "frozen_reference":
                    order = {c.digest: i for i, c in enumerate(self.cells)}
                    if order[group.source_cell_digest] != min(order[c] for c in group.cell_digests):
                        raise ValueError(
                            "baseline reference source must precede followers in frozen order"
                        )
                if group.model_digest not in by_task[assigned[0].task_id].candidate_digests:
                    raise ValueError("baseline reuse model is outside the frozen task catalogue")

    def child_batches(self) -> tuple[tuple[ComparisonCell, ...], ...]:
        """Bound allocation groups without issuing fresh budgets or launching work."""
        return tuple(self.cells[i : i + 32] for i in range(0, len(self.cells), 32))
