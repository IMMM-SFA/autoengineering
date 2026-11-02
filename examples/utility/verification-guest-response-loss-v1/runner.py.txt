"""Drop real local CREATE/START acknowledgments before the executor sees them.

The daemon operation is real; its successful response is saved, then withheld by
this qualification wrapper. This tests producer-side response loss, not a network
outage. No retry, fitting, scoring or private-label access is permitted.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_creation_cleanup import read_creation_cleanup
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_watchdog import GuestWatchdogPlan, read_outcome
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture

CASES = {
    "lost_create_response": ("create_intent", 0, "creation-cleanup"),
    "lost_start_response": ("start_intent", 1, "guest-watchdog"),
}


class ResponseLost(ConnectionError):
    pass


class ObservedAPI:
    def __init__(self, api, root, case):
        if case not in CASES:
            raise ValueError("unknown response-loss case")
        self.original, self.root, self.case = api._request, root, case
        self.creations = self.starts = self.deletions = self.calls = 0
        self.dropped = False
        self.created_id = None
        root.mkdir(mode=0o700)
        api._request = self.request

    def request(self, method, path, value=None, *, deadline, cancelled=None):
        create = method == "POST" and path.startswith("/containers/create")
        start = method == "POST" and path.endswith("/start")
        if create:
            self.creations += 1
            if self.creations > 1:
                raise RuntimeError("response-loss control refused repeated CREATE")
        if start:
            self.starts += 1
            if self.starts > CASES[self.case][1]:
                raise RuntimeError("response-loss control refused unallowed/repeated START")
        if method == "DELETE":
            self.deletions += 1
            if self.deletions > 1:
                raise RuntimeError("response-loss control refused repeated owner DELETE")
        self.calls += 1
        index = f"{self.calls:03d}"
        fixture.save(self.root, index + "-intent.json", {"method": method, "path": path})
        status, raw = self.original(method, path, value, deadline=deadline, cancelled=cancelled)
        fixture.save(
            self.root,
            index + "-response.json",
            {
                "status": status,
                "body_size": len(raw),
                "body_sha256": hashlib.sha256(raw).hexdigest(),
            },
        )
        if create and status == 201:
            self.created_id = unique_json(raw.decode())["Id"]
        drop = (create and self.case == "lost_create_response") or (
            start and self.case == "lost_start_response"
        )
        if drop:
            expected = 201 if create else 204
            if self.dropped or status != expected:
                raise ValueError("original acknowledgment is not the expected first success")
            fixture.save(
                self.root,
                "withheld-response.json",
                {
                    "case": self.case,
                    "call": self.calls,
                    "method": method,
                    "path": path,
                    "status": status,
                    "body": unique_json(raw.decode()) if raw else None,
                    "body_size": len(raw),
                    "body_sha256": hashlib.sha256(raw).hexdigest(),
                },
            )
            durable_write(self.root / "withheld-response-body.bin", raw)
            self.dropped = True
            raise ResponseLost("authored acknowledgment loss: " + self.case)
        return status, raw


def prepare(frozen_fixture, resources, environment, *, resource_digest, output):
    frozen_fixture = checked_directory(frozen_fixture)
    output = Path(output).absolute()
    fixture.build.guest_image._public_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("response-loss output must be absent")
    output.mkdir(mode=0o700)
    requests = {}
    for case in CASES:
        q = fixture.prepare(
            frozen_fixture / "owner",
            frozen_fixture / "suite",
            frozen_fixture / "source",
            frozen_fixture / "drivers",
            resources,
            environment,
            resource_digest=resource_digest,
            output=output / case,
        )
        requests[case] = digest(q)
    q = {
        "schema": "utility-guest-response-loss-controls-v1",
        "case_requests": requests,
        "case_policy": {name: list(value) for name, value in CASES.items()},
        "scope_digest": digest(str(output)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "max_container_creations": 2,
        "max_container_starts": 1,
        "max_control_watchdogs": 1,
        "max_charged_inference_starts": 1,
        "fitting_starts_allowed": 0,
        "scoring_starts_allowed": 0,
        "active_seconds_per_case": 20,
        "cleanup_seconds_per_case": 10,
        "post_cleanup_observation_seconds_per_case": 10,
        "automatic_retries": 0,
        "runtime_qualified": False,
        "scope": "real daemon operations; producer wrapper withholds successful acknowledgments",
    }
    fixture.save(output, "request.json", q)
    durable_write(output / "runner.py.txt", Path(__file__).read_bytes())
    return q


def run_case(root, case):
    q, binding = fixture.read(root, "request.json"), fixture.read(root, "bindings.json")
    if fixture.build._endpoint(binding["endpoint"]) != q["endpoint"]:
        raise ValueError("response-loss local endpoint changed")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(q["grant"])
    if grant.inference.forcing.prior_exposure != "exposed" or grant.inference.timeout_seconds != 20:
        raise ValueError("response-loss exposure or original timeout differs")
    api = GuestDaemonAPI(
        binding["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    if api.profile.to_dict() != q["daemon"]:
        raise ValueError("response-loss daemon implementation differs")
    observed = ObservedAPI(api, root / "api-observations", case)
    executor = GuestRoutingExecutor(
        store,
        root / "source",
        root / "drivers",
        root / "work",
        sources=tuple(ArtifactRef.from_dict(v) for v in q["sources"]),
        lock=ArtifactRef.from_dict(q["lock"]),
        guest=fixture.guest_resources.validate_profile(q["guest"]),
        environment=ArtifactRef.from_dict(q["environment"]),
        api=api,
        publisher_digest=publisher_identity(),
    )
    phase, starts, cleanup_name = CASES[case]
    fixture.save(
        root,
        "control-intent.json",
        {
            "case": case,
            "grant_digest": grant.digest,
            "withhold": case,
            "expected_exception": "ResponseLost",
            "expected_reason": "authored acknowledgment loss: " + case,
            "creations_reserved": 1,
            "container_starts_reserved": starts,
            "automatic_retries": 0,
        },
    )
    with store.writer():
        args = dict(
            cell_digest=grant.cell_digest,
            attempt_id="confirmation-" + grant.cell_digest[:48],
            child_digest=grant.digest,
            phase="confirmation",
        )
        store.append(
            request_id="response-loss-reserve",
            operation="reserve",
            resources=grant.resources,
            **args,
        )
        store.append(request_id="response-loss-start", operation="start", **args)
        ref = put_bytes(
            store.root,
            grant.to_json().encode(),
            name="confirmation-grant.json",
            media_type="application/json",
            producer="authored-response-loss",
        )
        store.append(
            request_id="response-loss-access",
            operation="confirmation_access",
            result_digest=ref.sha256,
            **args,
        )
        try:
            executor.execute(grant)
        except ResponseLost as error:
            error_reason = str(error)
        else:
            raise ValueError("response-loss control unexpectedly completed inference")
        before = observed.calls
        try:
            executor.execute(grant)
        except StoreError as error:
            retry_reason = str(error)
            if (
                retry_reason
                != "guest attempt already intended; explicit saved-evidence recovery only"
            ):
                raise
        else:
            raise ValueError("response-loss original grant permitted redispatch")
        if observed.calls != before:
            raise ValueError("redispatch refusal contacted the daemon")
    owner_root = root / "work" / grant.digest
    owner = GuestOwnerJournal(owner_root, suite_root=store.root)
    state = owner.replay()
    cleanup_root = owner_root / "control" / cleanup_name
    if case == "lost_create_response":
        outcome = read_creation_cleanup(owner)
        started_observed = False
    else:
        plan = GuestWatchdogPlan.from_dict(fixture.read(cleanup_root, "plan.json"))
        outcome = read_outcome(cleanup_root, owner, plan)
        from autoengineering.campaign.artifacts import read_bytes

        before = unique_json(read_bytes(cleanup_root, outcome.before).decode())
        started_observed = before["State"]["StartedAt"] != "0001-01-01T00:00:00Z"
        if outcome.reason != "owner_lost":
            raise ValueError("watchdog did not observe original owner pipe loss")
    cid = outcome.container_id
    if (
        state.phase != phase
        or observed.creations != 1
        or observed.starts != starts
        or not observed.dropped
        or error_reason != "authored acknowledgment loss: " + case
        or outcome.result != "absent"
        or cid != observed.created_id
        or not outcome.delete_intended
        or started_observed != bool(starts)
    ):
        raise ValueError("response loss, original phase/start or exact owned cleanup differs")
    forbidden_files = (
        ("daemon-create-response.json",)
        if starts == 0
        else (
            "control/guest-dispatch/start-response.json",
            "bootstrap-capture.json",
            "worker-result.json",
        )
    )
    if any((owner_root / name).exists() for name in forbidden_files):
        raise ValueError("withheld acknowledgment or unattempted inference was committed")
    absent = api.inspect(cid, deadline=time.monotonic() + 10)
    fixture.save(root, "post-cleanup-observation.json", {"container_id": cid, "inspect": absent})
    if absent is not None:
        raise ValueError("original response-loss container remains present")
    result = {
        "case": case,
        "passed": True,
        "container_id": cid,
        "owner_digest": owner.manifest.digest,
        "grant_digest": grant.digest,
        "phase": phase,
        "reason": error_reason,
        "container_creations": 1,
        "container_starts": starts,
        "charged_inference_starts": starts,
        "started_observed": started_observed,
        "model_result_observed": False,
        "inference_elapsed_seconds": None,
        "original_container_absent": True,
        "cleanup": outcome.to_dict(),
        "owner_api_requests": observed.calls,
        "retry_refusal": retry_reason,
        "retry_daemon_requests": 0,
        "parent_composite_reservation_retained": True,
        "runtime_qualified": False,
    }
    fixture.save(root, "control-result.json", result)
    return result


def execute(root, *, expected_digest):
    root = checked_directory(root)
    q = fixture.read(root, "request.json")
    if (
        digest(q) != expected_digest
        or q["scope_digest"] != digest(str(root))
        or q["runner_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        or q["case_policy"] != {name: list(value) for name, value in CASES.items()}
        or tuple(q["case_requests"]) != tuple(CASES)
    ):
        raise ValueError("response-loss source, scope or request changed")
    if tuple(
        q[name]
        for name in (
            "max_container_creations",
            "max_container_starts",
            "max_control_watchdogs",
            "max_charged_inference_starts",
            "fitting_starts_allowed",
            "scoring_starts_allowed",
            "active_seconds_per_case",
            "cleanup_seconds_per_case",
            "post_cleanup_observation_seconds_per_case",
            "automatic_retries",
            "runtime_qualified",
        )
    ) != (2, 1, 1, 1, 0, 0, 20, 10, 10, 0, False):
        raise ValueError("response-loss original bounds differ")
    for case in CASES:
        if digest(fixture.read(root / case, "request.json")) != q["case_requests"][case]:
            raise ValueError("prepared response-loss case changed")
    intent = root / "execution-intent.json"
    if intent.exists() or intent.is_symlink():
        raise ValueError("response-loss controls consumed; no retries")
    fixture.save(
        root, "execution-intent.json", {"request_digest": expected_digest, "starts_reserved": 1}
    )
    results = [run_case(root / case, case) for case in CASES]
    done = {
        "schema": "utility-guest-response-loss-completion-v1",
        "request_digest": expected_digest,
        "results": results,
        "all_passed": True,
        "container_creations": 2,
        "container_starts": 1,
        "charged_inference_starts": 1,
        "runtime_qualified": False,
    }
    fixture.save(root, "complete.json", done)
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("fixture", "resources", "environment", "output"):
        prep.add_argument(name, type=Path)
    prep.add_argument("--resource-digest", required=True)
    run = sub.add_parser("execute")
    run.add_argument("root", type=Path)
    run.add_argument("--expected-digest", required=True)
    a = p.parse_args()
    result = (
        prepare(
            a.fixture,
            a.resources,
            a.environment,
            resource_digest=a.resource_digest,
            output=a.output,
        )
        if a.command == "prepare"
        else execute(a.root, expected_digest=a.expected_digest)
    )
    print(canonical_json({"digest": digest(result), "schema": result["schema"]}))


if __name__ == "__main__":
    main()
