"""Reconstruct native comparison evidence without host or scientific imports."""

from autoengineering.agents.batch import BatchStore
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.records import sha256
from autoengineering.campaign.store import StoreError

from .comparison_status import read_json, reconstruct_report as common_report
from .native_evidence import file_digest, read_json_artifact, verify_provider

VERSION = "native-matched-runtime-1.0"


def reconstruct_report(batch, preparation_digest):
    value = common_report(batch, preparation_digest)
    active = value["active_case"]
    if active in ("single_agent", "four_role"):
        control = batch.root / "cases" / active / "worker/processes"
        if (control / "supervision.json").exists() and not (control / "interruption.json").exists():
            value["status"] = "reconciliation_required"
    complete = value["status"] == "completed" and set(value["route_verdicts"]) == {
        "scripted",
        "single_agent",
        "four_role",
    }
    for name, receipt in value["route_verdicts"].items():
        worker = WorkerStore(batch.root / "cases" / name / "worker")
        if receipt["kind"] != "native_matched_leaf_river_development":
            raise StoreError("native case verdict has another evidence kind")
        complete = complete and receipt["passed"] is True
        if name == "scripted":
            if worker.spec.host.kind != "fake" or receipt["provider_proofs"]:
                raise StoreError("scripted case claims native proof")
            continue
        interruption = receipt["interruption"]
        calls = worker.replay().invocations
        call = calls[interruption["call_id"]]
        proof = read_json_artifact(batch, interruption["evidence"])
        if read_json(worker.root / "processes", "interruption.json") != interruption:
            raise StoreError("native interruption verdict changed after case verdict")
        if (
            proof["call_digest"] != call.digest
            or call.state != "host_failure"
            or call.usage
            or call.resolved_model is not None
            or call.elapsed_seconds is not None
        ):
            raise StoreError("native interruption no longer binds the original unknown call")
        for path, expected in proof["bindings"].items():
            if file_digest(worker.root / "processes", path) != expected:
                raise StoreError("native interruption evidence changed after verdict")
        for name in (
            "upstream/attempt/process/launch-gate.json",
            "upstream/attempt/provider-intent.json",
            "upstream/attempt/provider-result.json",
        ):
            path = worker.root / "processes" / call.id / name
            if path.exists() or path.is_symlink():
                raise StoreError("native interruption unexpectedly passed preflight")
        expected_calls = set(calls) - {interruption["call_id"]}
        if set(receipt["provider_proofs"]) != expected_calls:
            raise StoreError("native verdict omits physical role calls")
        # Inspect every saved proof even after an earlier call is unverified.
        # A failed case must still expose corrupt or missing later evidence.
        checks = [
            verify_provider(batch, worker, calls[key], p)
            for key, p in receipt["provider_proofs"].items()
        ]
        verified = all(checks)
        complete = (
            complete
            and receipt["passed"] is True
            and interruption["passed"] is True
            and not interruption.get("unit_attestation_only")
            and verified
            and bool(expected_calls)
        )
    return {
        **value,
        "kind": "native_matched_leaf_river_development",
        "live_model_evidence": "complete" if complete else "incomplete",
        "measured_leaf_river_execution": "complete" if complete else "incomplete",
        "native_worker_interruption": "complete" if complete else "incomplete",
        "live_comparison_complete": bool(complete),
        "confirmation": "confirmation_not_attempted",
    }


def read_report(root, *, expected_digest):
    batch = BatchStore(root, expected_digest=expected_digest)
    origin = read_json(batch.root, "origin.json")
    if (
        set(origin)
        != {
            "version",
            "preparation_digest",
            "batch_digest",
            "conformance_runtime_digest",
            "conformance_prerequisite",
        }
        or origin["version"] != VERSION
        or origin["batch_digest"] != batch.digest
        or batch.spec.id != "matched-leaf-native-v1"
        or batch.spec.host.kind != "codex"
    ):
        raise StoreError("native comparison origin differs")
    sha256(origin["preparation_digest"])
    sha256(origin["conformance_runtime_digest"])
    proof = origin["conformance_prerequisite"]
    if proof["conformance_runtime_digest"] != origin["conformance_runtime_digest"]:
        raise StoreError("native comparison conformance pin differs")
    return {
        **reconstruct_report(batch, origin["preparation_digest"]),
        "conformance_prerequisite": proof,
    }
