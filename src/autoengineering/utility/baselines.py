"""Explicit allocation of one deterministic baseline receipt across logical cells."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from autoengineering.campaign.serialization import Record
from .contracts import sha256
from .costs import CostRecord


@dataclass(frozen=True)
class SharedBaseline(Record):
    score_digest: str
    cell_digests: tuple[str, ...]
    allocation: tuple[float, ...]
    profile: Literal["deterministic_frozen_reference"] = "deterministic_frozen_reference"

    def _validate(self):
        sha256(self.score_digest)
        if not self.cell_digests or len(set(self.cell_digests)) != len(self.cell_digests):
            raise ValueError("shared baseline needs unique assigned cells")
        for cell in self.cell_digests:
            sha256(cell)
        if len(self.allocation) != len(self.cell_digests) or any(v < 0 for v in self.allocation):
            raise ValueError("shared baseline allocations must align and be nonnegative")
        if abs(sum(self.allocation)-1.) > 1e-12:
            raise ValueError("shared baseline exclusive allocations must sum to one")

    def validate(self, spec):
        cells = {cell.digest: cell for cell in spec.cells}
        kinds = {route.route_id: route.kind for route in spec.routes}
        selected = [cells.get(identity) for identity in self.cell_digests]
        if any(cell is None or kinds[cell.route_id] != "baseline" for cell in selected):
            raise ValueError("shared baseline can allocate only assigned unchanged-baseline cells")
        if len({cell.task_id for cell in selected}) != 1:
            raise ValueError("shared baseline cannot combine different tasks")
        if len({cell.scenario_digest for cell in selected}) != 1:
            raise ValueError("shared baseline cannot combine different scenario identities")

    def validate_selections(self, selections):
        states = [selections.get(cell) for cell in self.cell_digests]
        if any(state is None or state.status != "selected" or state.selected_state is None for state in states):
            raise ValueError("shared baseline requires selected immutable parameter states")
        if len({(state.model.sha256, state.selected_state.sha256) for state in states}) != 1:
            raise ValueError("shared baseline selections must pin the same model and parameter state")

    def allocate_cost(self, receipt: CostRecord) -> CostRecord:
        """Keep one physical quantity while declaring its exclusive logical shares."""
        from dataclasses import replace
        if receipt.source_digest != self.score_digest:
            raise ValueError("baseline cost receipt must reference its physical score evidence")
        return replace(receipt, cell_digests=self.cell_digests, allocation=self.allocation)


def validate_shared_scores(spec, scores, allocations):
    if len({allocation.score_digest for allocation in allocations}) != len(allocations):
        raise ValueError("duplicate shared baseline allocation")
    by_source = {}
    for score in scores:
        by_source.setdefault(score.score_digest, []).append(score)
    declared = {allocation.score_digest: allocation for allocation in allocations}
    policy = spec.baseline_reuse
    if policy is not None:
        groups = {group.cell_digests: group for group in policy.groups}
        shared_cells = set()
        for allocation in allocations:
            group = groups.get(allocation.cell_digests)
            if group is None or allocation.allocation != group.allocation:
                raise ValueError("allocation differs from frozen baseline reuse policy")
            actual = by_source.get(allocation.score_digest, [])
            if any(score.status != "success" or score.feasible is not True for score in actual):
                raise ValueError("frozen baseline reuse requires successful feasible scores")
            shared_cells.update(allocation.cell_digests)
        followers = {
            cell for group in policy.groups for cell in group.cell_digests
            if cell != group.source_cell_digest
        }
        if any(score.cell_digest in followers - shared_cells for score in scores):
            raise ValueError("frozen baseline follower requires its declared source allocation")
    for allocation in allocations:
        allocation.validate(spec)
        actual = by_source.get(allocation.score_digest, [])
        if {score.cell_digest for score in actual} != set(allocation.cell_digests):
            raise ValueError("baseline allocation must match every referenced logical score")
        payloads = [score.to_dict() for score in actual]
        for payload in payloads:
            payload.pop("cell_digest")
        if any(payload != payloads[0] for payload in payloads):
            raise ValueError("shared baseline values/status must come from one unchanged receipt")
    for identity, group in by_source.items():
        if len(group) > 1 and identity not in declared:
            raise ValueError("duplicate physical score reference; explicit baseline allocation required")
