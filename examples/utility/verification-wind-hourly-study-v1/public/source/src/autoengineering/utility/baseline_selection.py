"""Metadata-only baseline selection followers with original child-result lineage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef, ModelSnapshot
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import StoreError
from .confirmation import read_selected_state, selected_artifact_evidence
from .contracts import sha256


def execution_protocol_digest(spec):
    return (
        spec.baseline_reuse.comparison_protocol_digest
        if spec.baseline_reuse
        else spec.protocol_digest
    )


def follower_group(spec, cell_digest):
    policy = spec.baseline_reuse
    if policy is None or policy.selection_reuse != "frozen_reference":
        return None
    return next(
        (
            g
            for g in policy.groups
            if cell_digest in g.cell_digests and cell_digest != g.source_cell_digest
        ),
        None,
    )


def validate_selection_campaign(spec, task_id, campaign):
    policy = spec.baseline_reuse
    if policy is None or policy.selection_reuse != "frozen_reference":
        return
    baseline = getattr(campaign, "baseline", None)
    model = baseline.model if baseline is not None else campaign.model
    parameters = baseline.parameters if baseline is not None else campaign.baseline_configuration
    cells = {c.digest: c for c in spec.cells}
    for group in policy.groups:
        if cells[group.source_cell_digest].task_id == task_id and (
            group.model_digest != model.digest
            or group.configuration_digest != digest(dict(parameters))
        ):
            raise StoreError("baseline reuse differs from the supplied fixed reference")


@dataclass(frozen=True)
class BaselineSelectionReference(Record):
    schema: Literal["utility-baseline-selection-reference-v1"]
    suite_digest: str
    policy_digest: str
    source_cell_digest: str
    target_cell_digest: str
    source_result_digest: str

    def _validate(self):
        for name in (
            "suite_digest",
            "policy_digest",
            "source_cell_digest",
            "target_cell_digest",
            "source_result_digest",
        ):
            sha256(getattr(self, name))


def _summary(store, result, profile):
    from .controller import UtilityController

    child, _ = UtilityController(store)._child(result["child_digest"])
    summaries = [
        unique_json(read_bytes(child.root, ArtifactRef.from_dict(r)).decode())
        for r in result["case_result"]["evidence"]
    ]
    matches = [
        s
        for s in summaries
        if isinstance(s, dict)
        and s.get("profile") == profile
        and s.get("cell") == result["cell_digest"]
        and "selection" in s
    ]
    if len(matches) != 1 or result["case_result"]["status"] != "passed":
        raise StoreError("baseline reference lacks one original completed selection")
    return matches[0]


def _check_selection(store, group, chosen):
    if chosen is None:
        return ()
    if not isinstance(chosen, dict) or set(chosen) != {"model", "selected_state"}:
        raise StoreError("baseline reference selection is malformed")
    model_ref, state_ref = (ArtifactRef.from_dict(chosen[k]) for k in ("model", "selected_state"))
    model = ModelSnapshot.from_json(read_bytes(store.root, model_ref).decode())
    state = read_selected_state(store.root, state_ref)
    if (
        model_ref.sha256 != group.model_digest
        or state.model != model
        or digest(state.to_dict()["configuration"]) != group.configuration_digest
    ):
        raise StoreError("baseline reference model or default parameters differ")
    return (model_ref, model, state_ref, state)


def reuse_selection_reference(coordinator, batch, case_id, cell):
    group = follower_group(coordinator.store.spec, cell.digest)
    if group is None:
        return False
    source_attempt = "child-" + group.source_cell_digest[:48]
    prefix = coordinator.store.replay()
    result = coordinator.runtime._verify_result_prefix(
        source_attempt, prefix["attempts"], prefix["events"]
    )
    summary = _summary(coordinator.store, result, coordinator.plan.schema)
    if "baseline_reference" in summary:
        raise StoreError("baseline source cannot itself be a reference")
    chosen = summary["selection"]
    checked = _check_selection(coordinator.store, group, chosen)
    source_finish = next(
        e for e in prefix["events"] if e.attempt_id == source_attempt and e.operation == "finish"
    )
    proof = BaselineSelectionReference(
        "utility-baseline-selection-reference-v1",
        coordinator.store.spec.digest,
        coordinator.store.spec.baseline_reuse.digest,
        group.source_cell_digest,
        cell.digest,
        source_finish.result_digest,
    )
    refs = []
    if checked:
        model_ref, model, state_ref, state = checked
        refs.extend(
            (
                selected_artifact_evidence(batch, model_ref, model.to_dict(), "model"),
                selected_artifact_evidence(batch, state_ref, state.to_dict(), "selected_state"),
            )
        )
    evidence = batch.evidence(
        {
            "profile": coordinator.plan.schema,
            "cell": cell.digest,
            "selection": chosen,
            "baseline_reference": proof.to_dict(),
            "outcome": "shared_reference",
            "reference_outcome": summary.get("outcome"),
            "scientific_attempts": 0,
            "scientific_evaluations": 0,
            "native_reports": [],
        }
    )
    coordinator.fault("baseline_reference_evidence_saved")
    batch.finish_case(case_id, "passed", (evidence, *refs))
    coordinator.fault("baseline_reference_case_finished")
    return True


def validate_reference_result(store, result, attempts, events):
    group = follower_group(store.spec, result["cell_digest"])
    if group is None:
        return
    from .controller import UtilityController

    controller = UtilityController(store)
    child, _ = controller._child(result["child_digest"])
    case = next(c for c in child.spec.cases if c.id == result["case_id"])
    if case.kind != "reference" or any(
        r.case_id == case.id for r in child.replay().reservations.values()
    ):
        raise StoreError("baseline reference contains physical work")
    raw = [
        unique_json(read_bytes(child.root, ArtifactRef.from_dict(r)).decode())
        for r in result["case_result"]["evidence"]
    ]
    summaries = [r for r in raw if isinstance(r, dict) and "baseline_reference" in r]
    if len(summaries) != 1:
        raise StoreError("baseline reference proof is missing or ambiguous")
    summary = summaries[0]
    proof = BaselineSelectionReference.from_dict(summary["baseline_reference"])
    source_attempt = "child-" + group.source_cell_digest[:48]
    source = controller._verify_result_prefix(source_attempt, attempts, events)
    finished = next(e for e in events if e.operation == "finish" and e.attempt_id == source_attempt)
    expected = BaselineSelectionReference(
        "utility-baseline-selection-reference-v1",
        store.spec.digest,
        store.spec.baseline_reuse.digest,
        group.source_cell_digest,
        result["cell_digest"],
        finished.result_digest,
    )
    original = _summary(store, source, summary.get("profile"))
    if (
        proof != expected
        or summary.get("cell") != result["cell_digest"]
        or result["case_result"]["status"] != "passed"
        or "baseline_reference" in original
        or summary.get("selection") != original["selection"]
    ):
        raise StoreError("baseline reference differs from its original child result")
    _check_selection(store, group, summary["selection"])


def allocate_selection_costs(store, records):
    policy = store.spec.baseline_reuse
    if policy is None or policy.selection_reuse != "frozen_reference":
        return records
    by_source = {g.source_cell_digest: g for g in policy.groups}
    result = []
    for record in records:
        group = by_source.get(record.cell_digests[0]) if len(record.cell_digests) == 1 else None
        if record.category in ("selection", "training") and group is not None:
            record = replace(record, cell_digests=group.cell_digests, allocation=group.allocation)
        result.append(record)
    return result


def selection_reference_costs(store, state):
    """Expose unmeasured copy overhead rather than manufacturing zero duration."""
    from .costs import CostRecord

    records = []
    for allocation, status in state["attempts"].values():
        if allocation.phase != "selection" or status != "finished":
            continue
        group = follower_group(store.spec, allocation.cell_digest)
        if group is not None:
            source = digest({"suite": store.spec.digest, "reference": allocation.to_dict()})
            records.append(
                CostRecord(
                    "cost-" + source[:48],
                    source,
                    "selection",
                    "baseline_reference_copy_duration",
                    "s",
                    None,
                    (allocation.cell_digest,),
                    (1.0,),
                )
            )
    return records
