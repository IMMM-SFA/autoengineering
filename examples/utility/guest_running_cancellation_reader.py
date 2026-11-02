"""Verify saved running cancellation without a daemon or new inference."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_inputs import verify_guest_inputs
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_watchdog import GuestWatchdogPlan, read_outcome
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture


def read_completion(root, *, expected_digest):
    root = checked_directory(root)
    control, q, done = (
        fixture.read(root, name)
        for name in ("control-request.json", "request.json", "complete.json")
    )
    if (
        digest(done) != expected_digest
        or done["request_digest"] != digest(control)
        or control["prepared_request_digest"] != digest(q)
        or control["runner_sha256"]
        != hashlib.sha256(fixture.raw(root, "controller.py.txt")).hexdigest()
        or control["helper_sha256"]
        != hashlib.sha256(fixture.raw(root, "helper.py.txt")).hexdigest()
        or q["runner_sha256"] != hashlib.sha256(fixture.raw(root, "runner.py.txt")).hexdigest()
        or done["schema"] != "utility-running-guest-cancellation-completion-v1"
        or control["schema"] != "utility-running-guest-cancellation-v1"
        or (
            done["container_creations"],
            done["container_starts"],
            done["charged_inference_starts"],
            done["retry_daemon_requests"],
            done["parent_composite_reservation_retained"],
            done["inference_elapsed_seconds"],
            done["all_passed"],
            done["runtime_qualified"],
        )
        != (1, 1, 1, 0, True, None, True, False)
    ):
        raise ValueError("saved running cancellation source, request or acceptance differs")
    owner = GuestOwnerJournal(root / "owner")
    state = owner.replay()
    m = owner.manifest
    verify_guest_inputs(owner.root, m.job, m.launch, m.claim)
    if (
        m.job.grant.to_dict() != q["grant"]
        or m.job.grant.inference.forcing.prior_exposure != "exposed"
        or state.observations["started"]["State"]["Running"] is not True
    ):
        raise ValueError("saved running cancellation lacks original running exposed guest")
    started = next(e for e in state.events if e.operation == "started")
    if fixture.read(root, "cancellation-trigger.json") != {
        "owner_digest": m.digest,
        "grant_digest": m.job.grant.digest,
        "event_digest": started.digest,
        "phase": "started",
        "running": True,
        "boundary": "before_input_transfer",
    }:
        raise ValueError("saved running cancellation transition differs")
    guard = owner.root / "control/guest-watchdog"
    plan = GuestWatchdogPlan.from_dict(fixture.read(guard, "plan.json"))
    outcome = read_outcome(guard, owner, plan)
    if (
        outcome.to_dict() != done["cleanup"]
        or outcome.reason != "cancelled"
        or outcome.result != "absent"
        or not outcome.delete_intended
        or outcome.container_id != done["container_id"]
        or (owner.root / "bootstrap-capture.json").exists()
    ):
        raise ValueError("saved running cancellation original cleanup differs")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(q["grant"])
    executor = GuestRoutingExecutor.for_recovery(store, grant, Path("/unavailable-original-work"))
    result = executor.recover(grant)
    if (
        result.to_dict() != done["recovered"]
        or result.status != "infrastructure_failure"
        or result.result is not None
        or result.lifecycle_seconds is not None
        or result.container_starts != 1
        or result.container_id != outcome.container_id
    ):
        raise ValueError(
            "cancelled failure was changed into model result, zero time or new execution"
        )
    cid = outcome.container_id
    if fixture.read(root, "post-cleanup-observation.json") != {
        "container_id": cid,
        "inspect": None,
    }:
        raise ValueError("saved original cancellation absence differs")
    api = root / "api-observations"
    calls = [fixture.read(api, p.name) for p in sorted(api.glob("*-intent.json"))]
    if (
        sum(v["method"] == "POST" and v["path"].startswith("/containers/create") for v in calls)
        != 1
        or sum(v["method"] == "POST" and v["path"].endswith("/start") for v in calls) != 1
        or calls[-1] != {"method": "GET", "path": f"/containers/{cid}/json"}
        or fixture.read(api, f"{len(calls):03d}-response.json")["status"] != 404
    ):
        raise ValueError("saved original cancellation API counts or absence differ")
    return {
        "completion_digest": expected_digest,
        "container_id": cid,
        "status": result.status,
        "model_result": None,
        "lifecycle_seconds": None,
        "charged_inference_starts": 1,
        "new_container_starts": 0,
        "new_processes": 0,
        "runtime_qualified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--expected-digest", required=True)
    a = p.parse_args()
    print(canonical_json(read_completion(a.root, expected_digest=a.expected_digest)))


if __name__ == "__main__":
    main()
