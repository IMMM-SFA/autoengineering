"""Reconstruct conformance evidence without host, profile or science execution."""

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import sha256
from autoengineering.campaign.serialization import unique_json
from autoengineering.campaign.store import StoreError
from .batch import BatchStore
from .conformance_protocol import IMPLEMENTED_CASES
from .report import evidence_report
from .store import WorkerStore


def _live_complete(report, proofs):
    if report["status"] != "completed" or set(proofs) != set(IMPLEMENTED_CASES):
        return False
    for name, proof in proofs.items():
        if proof.get("kind") != name or proof.get("passed") is not True:
            return False
        providers = [
            proof.get("provider"),
            proof.get("request"),
            proof.get("ownership"),
            *proof.get("providers", {}).values(),
        ]
        if not any(providers) or any(
            value and (value.get("verified") is not True or value.get("unit_attestation_only"))
            for value in providers
        ):
            return False
    return True


def reconstruct_report(batch, preparation_digest):
    report = batch.report()
    projection = batch.replay()
    proofs = {}
    for name, result in projection.finished.items():
        proofs[name] = unique_json(
            read_bytes(batch.root, result.evidence[0], max_bytes=65536).decode()
        )
    for case in ("roles", "malformed"):
        if case in proofs:
            worker_store = WorkerStore(batch.root / "cases" / case / "worker")
            evidence_report(worker_store)
            if worker_store.replay().events[-1].digest != proofs[case]["worker_head"]:
                raise StoreError("conformance worker evidence changed after its verdict")
    active = report["active_case"]
    worker_root = batch.root / "cases" / (active or "unused") / "worker"
    if active in ("roles", "malformed") and worker_root.exists():
        worker = evidence_report(WorkerStore(worker_root))
        if (
            worker["pending_invocations"]
            or worker["pending_campaign_actions"]
            or (worker["physical_work"] or {}).get("cost_is_uncertain", False)
        ):
            report["status"] = "reconciliation_required"
    if report["active_case"] == "owner_loss":
        report["status"] = "reconciliation_required"
    missing = [case.id for case in batch.spec.cases if case.id not in IMPLEMENTED_CASES]
    if report["status"] not in ("failed", "reconciliation_required") and missing:
        report["status"] = "incomplete"
    return {
        **report,
        "preparation_digest": preparation_digest,
        "implemented_execution_handlers": list(IMPLEMENTED_CASES),
        "missing_execution_handlers": missing,
        "live_conformance_complete": _live_complete(report, proofs),
        "case_verdicts": proofs,
    }


def read_report(root, *, expected_digest):
    batch = BatchStore(root, expected_digest=expected_digest)
    path = confined_file(batch.root, "origin.json")
    if path.stat().st_size > 65536:
        raise StoreError("conformance origin exceeds limit")
    origin = unique_json(path.read_text())
    if (
        set(origin) != {"version", "preparation_digest", "batch_digest"}
        or origin["version"] != "conformance-runtime-1.0"
        or origin["batch_digest"] != batch.digest
    ):
        raise StoreError("conformance origin binding mismatch")
    sha256(origin["preparation_digest"])
    return reconstruct_report(batch, origin["preparation_digest"])
