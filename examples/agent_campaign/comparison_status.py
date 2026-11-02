"""Read matched comparison evidence without hosts, models or array loading."""

from __future__ import annotations

from autoengineering.agents.batch import BatchStore
from autoengineering.agents.report import evidence_report
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef, sha256
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import EventStore, StoreError

CURRENT_VERSION = "synthetic-matched-comparison-1.1"
READABLE_VERSIONS = ("synthetic-matched-comparison-1.0", CURRENT_VERSION)


def read_json(root, name, limit=65536):
    with confined_file(root, name).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("comparison metadata exceeds allowance")
    return unique_json(raw.decode())


def reconstruct_report(batch, preparation_digest):
    """Read journals and saved verdicts, without executing models or loading arrays."""
    sha256(preparation_digest)
    value = batch.report()
    receipts = {}
    for name, result in batch.replay().finished.items():
        receipt = unique_json(read_bytes(batch.root, result.evidence[0]).decode())
        root = batch.root / "cases" / name
        control = receipt["invalid_candidate_control"]
        if canonical_json(read_json(root, "invalid-interface.json")) != canonical_json(control):
            raise StoreError("comparison invalid-candidate receipt changed")
        read_bytes(root, ArtifactRef.from_dict(control["invalid_snapshot"]), max_bytes=1048576)
        worker = WorkerStore(root / "worker")
        evidence_report(worker)
        if (
            worker.replay().events[-1].digest != receipt["worker_head"]
            or EventStore(root / "campaign").replay().events[-1].digest
            != receipt["scientific_head"]
        ):
            raise StoreError("comparison evidence changed after verdict")
        read_bytes(batch.root, ArtifactRef.from_dict(receipt["worker_report"]), max_bytes=1048576)
        receipts[name] = receipt
    active = batch.replay().active_case
    active_worker = None
    if active is not None and (batch.root / "cases" / active / "worker").exists():
        active_worker = evidence_report(WorkerStore(batch.root / "cases" / active / "worker"))
        if (
            active_worker["pending_invocations"]
            or active_worker["pending_campaign_actions"]
            or (active_worker["physical_work"] or {}).get("cost_is_uncertain", False)
        ):
            value["status"] = "reconciliation_required"
    return {
        **value,
        "preparation_digest": preparation_digest,
        "kind": "authored_synthetic_dry_run",
        "live_model_evidence": "not_attempted",
        "measured_leaf_river_execution": "not_attempted",
        "native_worker_interruption": "not_attempted",
        "live_comparison_complete": False,
        "reservation_counts": "cumulative_for_original_runtime",
        "active_worker_report": active_worker,
        "route_verdicts": receipts,
    }


def read_report(root, *, expected_digest):
    batch = BatchStore(root, expected_digest=expected_digest)
    origin = read_json(batch.root, "origin.json")
    if (
        set(origin) != {"version", "preparation_digest", "batch_digest"}
        or origin["version"] not in READABLE_VERSIONS
        or origin["batch_digest"] != batch.digest
        or batch.spec.id != "synthetic-matched-pet-v1"
        or batch.spec.host.kind != "fake"
    ):
        raise StoreError("comparison origin or kind differs")
    sha256(origin["preparation_digest"])
    return reconstruct_report(batch, origin["preparation_digest"])
