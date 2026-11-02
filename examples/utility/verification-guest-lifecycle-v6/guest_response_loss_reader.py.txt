"""Verify original response-loss and cleanup proof without a daemon or model."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory
from autoengineering.utility.guest_creation_cleanup import read_creation_cleanup
from autoengineering.utility.guest_inputs import verify_guest_inputs
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_watchdog import GuestWatchdogPlan, read_outcome
from examples.utility import guest_response_loss_controls as controls
from examples.utility import guest_inference_smoke as fixture


def read_completion(root, *, expected_digest):
    root = checked_directory(root)
    q, done = (fixture.read(root, name) for name in ("request.json", "complete.json"))
    if (
        digest(done) != expected_digest
        or done["request_digest"] != digest(q)
        or q["schema"] != "utility-guest-response-loss-controls-v1"
        or done["schema"] != "utility-guest-response-loss-completion-v1"
        or q["case_policy"] != {name: list(policy) for name, policy in controls.CASES.items()}
        or q["runner_sha256"] != hashlib.sha256(fixture.raw(root, "runner.py.txt")).hexdigest()
        or (
            done["all_passed"],
            done["container_creations"],
            done["container_starts"],
            done["charged_inference_starts"],
            done["runtime_qualified"],
        )
        != (True, 2, 1, 1, False)
        or set(q["case_requests"]) != set(controls.CASES)
        or len(done["results"]) != 2
    ):
        raise ValueError("saved response-loss matrix, completion or producer differs")
    results = []
    for case, (phase, starts, cleanup_name) in controls.CASES.items():
        scope = checked_directory(root / case)
        prepared = fixture.read(scope, "request.json")
        result = fixture.read(scope, "control-result.json")
        if (
            digest(prepared) != q["case_requests"][case]
            or prepared["runner_sha256"]
            != hashlib.sha256(fixture.raw(scope, "runner.py.txt")).hexdigest()
            or result != done["results"][len(results)]
        ):
            raise ValueError("saved response-loss case or prepared producer differs")
        owner = GuestOwnerJournal(scope / "owner")
        state = owner.replay()
        m = owner.manifest
        verify_guest_inputs(owner.root, m.job, m.launch, m.claim)
        cleanup = owner.root / "control" / cleanup_name
        if starts == 0:
            outcome = read_creation_cleanup(owner)
        else:
            plan = GuestWatchdogPlan.from_dict(fixture.read(cleanup, "plan.json"))
            outcome = read_outcome(cleanup, owner, plan)
            if outcome.reason != "owner_lost":
                raise ValueError("original watchdog did not observe owner pipe loss")
        cid = outcome.container_id
        before = unique_json(read_bytes(cleanup, outcome.before).decode())
        started = before["State"]["StartedAt"] != "0001-01-01T00:00:00Z"
        if (
            outcome.to_dict() != result["cleanup"]
            or outcome.result != "absent"
            or not outcome.delete_intended
            or state.phase != phase
            or started != bool(starts)
            or m.job.grant.to_dict() != prepared["grant"]
            or m.job.grant.inference.forcing.prior_exposure != "exposed"
            or result["case"] != case
            or result["reason"] != "authored acknowledgment loss: " + case
            or result["owner_digest"] != m.digest
            or result["container_id"] != cid
            or result["grant_digest"] != m.job.grant.digest
            or (
                result["passed"],
                result["container_creations"],
                result["container_starts"],
                result["charged_inference_starts"],
                result["started_observed"],
                result["model_result_observed"],
                result["inference_elapsed_seconds"],
                result["original_container_absent"],
                result["parent_composite_reservation_retained"],
                result["runtime_qualified"],
                result["retry_daemon_requests"],
            )
            != (True, 1, starts, starts, bool(starts), False, None, True, True, False, 0)
            or result["retry_refusal"]
            != "guest attempt already intended; explicit saved-evidence recovery only"
        ):
            raise ValueError("saved response-loss acceptance or exact original cleanup differs")
        api = scope / "api-observations"
        withheld = fixture.read(api, "withheld-response.json")
        raw = fixture.raw(api, "withheld-response-body.bin")
        if (
            withheld["case"] != case
            or withheld["method"] != "POST"
            or withheld["status"] != (201 if starts == 0 else 204)
            or withheld["body_size"] != len(raw)
            or withheld["body_sha256"] != hashlib.sha256(raw).hexdigest()
            or withheld["body"] != (unique_json(raw.decode()) if raw else None)
            or (starts == 0 and withheld["body"]["Id"] != cid)
            or (starts == 1 and raw != b"")
        ):
            raise ValueError("saved withheld actual response differs")
        calls = [fixture.read(api, p.name) for p in sorted(api.glob("*-intent.json"))]
        if (
            len(calls) != result["owner_api_requests"]
            or sum(
                v["method"] == "POST" and v["path"].startswith("/containers/create") for v in calls
            )
            != 1
            or sum(v["method"] == "POST" and v["path"].endswith("/start") for v in calls) != starts
            or calls[-1] != {"method": "GET", "path": f"/containers/{cid}/json"}
            or not 1 <= withheld["call"] <= len(calls)
            or calls[withheld["call"] - 1] != {"method": "POST", "path": withheld["path"]}
        ):
            raise ValueError("saved original API attempt log differs")
        captured = fixture.read(api, f"{withheld['call']:03d}-response.json")
        if captured != {key: withheld[key] for key in ("status", "body_size", "body_sha256")}:
            raise ValueError("withheld response differs from original transport capture")
        if fixture.read(api, f"{len(calls):03d}-response.json")["status"] != 404:
            raise ValueError("saved final API response is not absence")
        if fixture.read(scope, "post-cleanup-observation.json") != {
            "container_id": cid,
            "inspect": None,
        }:
            raise ValueError("saved post-cleanup absence differs")
        missing = (
            ["daemon-create-response.json"]
            if starts == 0
            else [
                "control/guest-dispatch/start-response.json",
                "bootstrap-capture.json",
                "worker-result.json",
            ]
        )
        if any((owner.root / name).exists() for name in missing):
            raise ValueError("withheld response or unobserved inference is committed")
        results.append(
            {
                "case": case,
                "container_id": cid,
                "journal_phase": phase,
                "container_starts": starts,
                "charged_inference_starts": starts,
                "cleanup_result": outcome.result,
                "retry_daemon_requests": 0,
            }
        )
    return {
        "completion_digest": expected_digest,
        "results": results,
        "new_container_creations": 0,
        "new_container_starts": 0,
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
