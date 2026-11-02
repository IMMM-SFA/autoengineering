"""Verify saved unstarted-cancellation evidence without a daemon or model call."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory
from autoengineering.utility.guest_creation_cleanup import read_creation_cleanup
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_inputs import verify_guest_inputs
from autoengineering.utility.guest_watchdog import GuestWatchdogPlan, read_outcome
from examples.utility import guest_cancellation_controls as controls
from examples.utility import guest_inference_smoke as fixture


def read_completion(root, *, expected_digest):
    root = checked_directory(root)
    q, done = (fixture.read(root, name) for name in ("request.json", "complete.json"))
    if (
        digest(done) != expected_digest
        or done["request_digest"] != digest(q)
        or q["schema"] != "utility-guest-cancellation-controls-v1"
        or done["schema"] != "utility-guest-cancellation-completion-v1"
        or q["case_policy"] != {name: list(policy) for name, policy in controls.CASES.items()}
        or q["runner_sha256"] != hashlib.sha256(fixture.raw(root, "runner.py.txt")).hexdigest()
        or (
            done["all_passed"],
            done["container_creations"],
            done["container_starts"],
            done["scientific_starts"],
            done["runtime_qualified"],
        )
        != (True, 2, 0, 0, False)
    ):
        raise ValueError("saved cancellation request, completion or producer differs")
    if set(q["case_requests"]) != set(controls.CASES) or len(done["results"]) != 2:
        raise ValueError("saved cancellation matrix differs")
    results = []
    for case, (phase, reason, cleanup_name) in controls.CASES.items():
        scope = checked_directory(root / case)
        prepared = fixture.read(scope, "request.json")
        result = fixture.read(scope, "control-result.json")
        if (
            digest(prepared) != q["case_requests"][case]
            or prepared["runner_sha256"]
            != hashlib.sha256(fixture.raw(scope, "runner.py.txt")).hexdigest()
            or result != done["results"][len(results)]
        ):
            raise ValueError("saved cancellation case or prepared producer differs")
        owner = GuestOwnerJournal(scope / "owner")
        state = owner.replay()
        m = owner.manifest
        verify_guest_inputs(owner.root, m.job, m.launch, m.claim)
        cid = state.observations["created"]["Id"]
        trigger = fixture.read(scope, "cancellation-trigger.json")
        if trigger != {
            "owner_digest": m.digest,
            "phase": phase,
            "event_digest": state.events[-1].digest,
            "grant_digest": m.job.grant.digest,
        }:
            raise ValueError("saved cancellation trigger differs from original transition")
        cleanup = owner.root / "control" / cleanup_name
        if case == "cancel_after_create":
            outcome = read_creation_cleanup(owner)
        else:
            plan = GuestWatchdogPlan.from_dict(fixture.read(cleanup, "plan.json"))
            outcome = read_outcome(cleanup, owner, plan)
            if outcome.reason != "cancelled":
                raise ValueError("original watchdog did not observe cancellation")
        if (
            outcome.to_dict() != result["cleanup"]
            or outcome.result != "absent"
            or outcome.container_id != cid
            or not outcome.delete_intended
            or outcome.kill_intended
            or state.phase != phase
            or m.job.grant.to_dict() != prepared["grant"]
            or m.job.grant.inference.forcing.prior_exposure != "exposed"
            or result["case"] != case
            or result["reason"] != reason
            or result["owner_digest"] != m.digest
            or result["container_id"] != cid
            or result["grant_digest"] != m.job.grant.digest
            or (
                result["passed"],
                result["container_creations"],
                result["container_starts"],
                result["scientific_starts"],
                result["original_container_absent"],
                result["parent_composite_reservation_retained"],
                result["runtime_qualified"],
            )
            != (True, 1, 0, 0, True, True, False)
        ):
            raise ValueError("saved cancellation acceptance or original cleanup differs")
        post = fixture.read(scope, "post-cleanup-observation.json")
        if post != {"container_id": cid, "inspect": None}:
            raise ValueError("saved post-cleanup absence differs")
        intents = sorted((scope / "api-observations").glob("*-intent.json"))
        calls = [fixture.read(scope, str(path.relative_to(scope))) for path in intents]
        if (
            len(calls) != result["owner_api_requests"]
            or sum(
                v["method"] == "POST" and v["path"].startswith("/containers/create") for v in calls
            )
            != 1
            or any(v["method"] == "POST" and v["path"].endswith("/start") for v in calls)
            or calls[-1] != {"method": "GET", "path": f"/containers/{cid}/json"}
        ):
            raise ValueError("saved original API attempt log differs")
        response = fixture.read(scope / "api-observations", f"{len(calls):03d}-response.json")
        if response["status"] != 404:
            raise ValueError("saved last actual API response is not absence")
        results.append(
            {
                "case": case,
                "container_id": cid,
                "phase": phase,
                "cleanup_result": outcome.result,
                "container_starts": 0,
            }
        )
    return {
        "completion_digest": expected_digest,
        "results": results,
        "new_container_creations": 0,
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
