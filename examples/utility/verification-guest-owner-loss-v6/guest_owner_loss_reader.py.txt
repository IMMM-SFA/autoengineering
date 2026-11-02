"""Verify saved exact-child loss, original cleanup and captured-result recovery."""

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
from examples.utility import guest_owner_loss_controls as controls
from examples.utility import guest_inference_smoke as fixture


def read_completion(root, *, expected_digest):
    root = checked_directory(root)
    q, done = (fixture.read(root, name) for name in ("request.json", "complete.json"))
    if (
        digest(done) != expected_digest
        or done["request_digest"] != digest(q)
        or q["schema"] != "utility-guest-owner-loss-controls-v1"
        or done["schema"] != "utility-guest-owner-loss-completion-v1"
        or q["case_policy"] != {name: list(value) for name, value in controls.CASES.items()}
        or q["runner_sha256"] != hashlib.sha256(fixture.raw(root, "runner.py.txt")).hexdigest()
        or set(q["case_requests"]) != set(controls.CASES)
        or len(done["results"]) != 4
        or (
            done["all_passed"],
            done["container_creations"],
            done["container_starts"],
            done["charged_inference_starts"],
            done["runtime_qualified"],
        )
        != (True, 4, 2, 2, False)
    ):
        raise ValueError("saved owner-loss source, matrix or completion differs")
    results = []
    for case, (stage, phase, starts) in controls.CASES.items():
        scope = checked_directory(root / case)
        prepared = fixture.read(scope, "request.json")
        result = fixture.read(scope, "control-result.json")
        if (
            digest(prepared) != q["case_requests"][case]
            or prepared["runner_sha256"]
            != hashlib.sha256(fixture.raw(scope, "runner.py.txt")).hexdigest()
            or result != done["results"][len(results)]
        ):
            raise ValueError("saved owner-loss case or prepared producer differs")
        owner = GuestOwnerJournal(scope / "owner")
        state = owner.replay()
        m = owner.manifest
        verify_guest_inputs(owner.root, m.job, m.launch, m.claim)
        marker = fixture.read(scope, "stage-ready.json")
        launched = fixture.read(scope, "child-launched.json")
        stopped = fixture.read(scope, "child-stopped.json")
        intent = fixture.read(scope, "child-intent.json")
        code = 0 if case == "watchdog_child_loss_before_start" else -9
        head = next(e.digest for e in state.events if e.operation == phase)
        cid = state.observations["created"]["Id"]
        if (
            intent
            != {"case": case, "nonce": marker["nonce"], "controller_sha256": q["runner_sha256"]}
            or launched != {"case": case, "nonce": marker["nonce"], "pid": marker["child_pid"]}
            or stopped != {"pid": marker["child_pid"], "nonce": marker["nonce"], "returncode": code}
            or marker["case"] != case
            or marker["stage"] != stage
            or marker["journal_phase"] != phase
            or marker["journal_head"] != head
            or marker["owner_digest"] != m.digest
            or marker["container_id"] != cid
            or m.job.grant.to_dict() != prepared["grant"]
            or m.job.grant.inference.forcing.prior_exposure != "exposed"
        ):
            raise ValueError("saved loss transition differs from exact owned child")
        if code == -9:
            if fixture.read(scope, "owner-kill-intent.json") != {
                "pid": marker["child_pid"],
                "nonce": marker["nonce"],
                "signal": "SIGKILL",
            }:
                raise ValueError("saved owner signal differs from exact owned child")
        else:
            ready = fixture.read(owner.root / "control/guest-watchdog", "ready.json")
            report = fixture.read(scope, "child-result.json")
            if (
                marker["watchdog_pid"] != ready["watchdog_pid"]
                or marker["watchdog_returncode"] != -9
                or report
                != {
                    "case": case,
                    "reason": "original guest watchdog is not live within its deadline",
                    "container_creations": 1,
                    "container_starts": 0,
                    "watchdog_killed": True,
                }
                or (scope / "owner-kill-intent.json").exists()
            ):
                raise ValueError("saved watchdog loss or START refusal differs")
        if (
            case == "owner_loss_running"
            and state.observations["started"]["State"]["Running"] is not True
        ):
            raise ValueError("owner loss lacks an originally running guest")
        guard = owner.root / "control/guest-watchdog"
        plan = GuestWatchdogPlan.from_dict(fixture.read(guard, "plan.json"))
        outcome = read_outcome(guard, owner, plan)
        if (
            plan.owner_pid != marker["child_pid"]
            or outcome.to_dict() != result["cleanup"]
            or outcome.result != "absent"
            or outcome.container_id != cid
            or not outcome.delete_intended
            or outcome.reason != ("owner_lost" if starts else "startup_refused")
            or result["case"] != case
            or result["container_id"] != cid
            or result["owner_digest"] != m.digest
            or result["stage"] != stage
            or result["phase_at_loss"] != phase
            or (
                result["passed"],
                result["owner_returncode"],
                result["container_creations"],
                result["container_starts"],
                result["charged_inference_starts"],
                result["inference_elapsed_seconds"],
                result["original_container_absent"],
                result["retry_daemon_requests"],
                result["parent_composite_reservation_retained"],
                result["runtime_qualified"],
            )
            != (True, code, 1, starts, starts, None, True, 0, True, False)
        ):
            raise ValueError("saved owner-loss acceptance or original cleanup differs")
        if case == "owner_loss_before_watchdog_ready" and (guard / "ready.json").exists():
            raise ValueError("before-watchdog loss unexpectedly has readiness")
        if case == "owner_loss_after_capture":
            store = SuiteStore(scope / "suite")
            grant = CompositeConfirmationGrant.from_dict(prepared["grant"])
            executor = GuestRoutingExecutor.for_recovery(
                store, grant, Path("/unavailable-original-work")
            )
            observed = executor.recover(grant)
            if (
                observed.to_dict() != result["recovered"]
                or observed.status != "success"
                or observed.lifecycle_seconds is not None
                or observed.container_id != cid
            ):
                raise ValueError(
                    "original captured result did not replay with unknown lifecycle time"
                )
        elif result["recovered"] is not None or (owner.root / "bootstrap-capture.json").exists():
            raise ValueError("uncaptured interruption supplied a model result")
        if fixture.read(scope, "post-cleanup-observation.json") != {
            "container_id": cid,
            "inspect": None,
        }:
            raise ValueError("saved exact original absence differs")
        child_calls = [
            fixture.read(scope / "child-api", p.name)
            for p in sorted((scope / "child-api").glob("*-intent.json"))
        ]
        parent_calls = [
            fixture.read(scope / "parent-api", p.name)
            for p in sorted((scope / "parent-api").glob("*-intent.json"))
        ]
        if (
            sum(
                v["method"] == "POST" and v["path"].startswith("/containers/create")
                for v in child_calls
            )
            != 1
            or sum(v["method"] == "POST" and v["path"].endswith("/start") for v in child_calls)
            != starts
            or any(v["method"] == "POST" for v in parent_calls)
            or parent_calls[-1] != {"method": "GET", "path": f"/containers/{cid}/json"}
            or fixture.read(scope / "parent-api", f"{len(parent_calls):03d}-response.json")[
                "status"
            ]
            != 404
        ):
            raise ValueError("saved owner/parent API counts or absence differ")
        results.append(
            {
                "case": case,
                "container_id": cid,
                "container_starts": starts,
                "charged_inference_starts": starts,
                "cleanup_result": "absent",
                "captured_result_replayed": result["recovered"] is not None,
            }
        )
    return {
        "completion_digest": expected_digest,
        "results": results,
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
