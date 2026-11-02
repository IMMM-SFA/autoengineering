"""Actual local cancellation of two exposed authored, unstarted guests.

Use the production executor and cleanup paths. No model, fitting, scoring or
provider work is permitted. Every consumed case retains its original charge.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_attach import GuestAttachCancelled
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture

CASES = {
    "cancel_after_create": ("created", "guest executor cancelled", "creation-cleanup"),
    "cancel_before_start": ("start_intent", "guest dispatch cancelled", "guest-watchdog"),
}


class Cancellation:
    """Persist the exact original owner transition before signaling cancellation."""

    def __init__(self, root, store, grant, phase):
        self.root, self.store, self.grant, self.phase = root, store, grant, phase
        self.triggered = False

    def __call__(self):
        if self.triggered:
            return True
        owner_root = self.root / "work" / self.grant.digest
        if not (owner_root / "owner.json").is_file():
            return False
        owner = GuestOwnerJournal(owner_root, suite_root=self.store.root)
        state = owner.replay()
        if state.phase != self.phase:
            return False
        fixture.save(
            self.root,
            "cancellation-trigger.json",
            {
                "owner_digest": owner.manifest.digest,
                "phase": state.phase,
                "event_digest": state.events[-1].digest,
                "grant_digest": self.grant.digest,
            },
        )
        self.triggered = True
        return True


class ObservedAPI:
    """Record real API attempts and refuse any container START before sending it.

    This wrapper fabricates no response. The watchdog is a separate production
    process and records its own cleanup intent/response/absence evidence.
    """

    def __init__(self, api, root):
        self.api, self.root = api, root
        self.original = api._request
        self.creations = self.starts = self.deletions = 0
        self.calls = 0
        root.mkdir(mode=0o700)
        api._request = self.request

    def request(self, method, path, value=None, *, deadline, cancelled=None):
        if method == "POST" and path.endswith("/start"):
            self.starts += 1
            raise RuntimeError("zero-start cancellation control attempted container START")
        if method == "POST" and path.startswith("/containers/create"):
            self.creations += 1
            if self.creations > 1:
                raise RuntimeError("cancellation control attempted a second CREATE")
        if method == "DELETE":
            self.deletions += 1
            if self.deletions > 1:
                raise RuntimeError("cancellation control attempted a second owner DELETE")
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
        return status, raw


def prepare(frozen_fixture, resources, environment, *, resource_digest, output):
    frozen_fixture = checked_directory(frozen_fixture)
    output = Path(output).absolute()
    fixture.build.guest_image._public_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("cancellation output must be absent")
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
        "schema": "utility-guest-cancellation-controls-v1",
        "case_requests": requests,
        "case_policy": {name: list(value) for name, value in CASES.items()},
        "scope_digest": digest(str(output)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "max_container_creations": 2,
        "max_container_starts": 0,
        "max_control_watchdogs": 1,
        "scientific_starts_allowed": 0,
        "fitting_starts_allowed": 0,
        "scoring_starts_allowed": 0,
        "active_seconds_per_case": 20,
        "cleanup_seconds_per_case": 10,
        "post_cleanup_observation_seconds_per_case": 10,
        "automatic_retries": 0,
        "runtime_qualified": False,
        "scope": "known exposed authored frozen fixture; two unstarted cancellation cases",
    }
    fixture.save(output, "request.json", q)
    durable_write(output / "runner.py.txt", Path(__file__).read_bytes())
    return q


def run_case(root, case):
    q, binding = fixture.read(root, "request.json"), fixture.read(root, "bindings.json")
    if fixture.build._endpoint(binding["endpoint"]) != q["endpoint"]:
        raise ValueError("cancellation local endpoint changed")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(q["grant"])
    if grant.inference.forcing.prior_exposure != "exposed" or grant.inference.timeout_seconds != 20:
        raise ValueError("cancellation fixture exposure or original timeout differs")
    api = GuestDaemonAPI(
        binding["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    if api.profile.to_dict() != q["daemon"]:
        raise ValueError("cancellation daemon implementation differs")
    observed = ObservedAPI(api, root / "api-observations")
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
    phase, reason, cleanup_name = CASES[case]
    cancellation = Cancellation(root, store, grant, phase)
    fixture.save(
        root,
        "control-intent.json",
        {
            "case": case,
            "grant_digest": grant.digest,
            "cancel_at_phase": phase,
            "expected_exception": "GuestAttachCancelled",
            "expected_reason": reason,
            "creations_reserved": 1,
            "container_starts_allowed": 0,
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
            request_id="cancellation-reserve",
            operation="reserve",
            resources=grant.resources,
            **args,
        )
        store.append(request_id="cancellation-start", operation="start", **args)
        ref = put_bytes(
            store.root,
            grant.to_json().encode(),
            name="confirmation-grant.json",
            media_type="application/json",
            producer="authored-cancellation",
        )
        store.append(
            request_id="cancellation-access",
            operation="confirmation_access",
            result_digest=ref.sha256,
            **args,
        )
        try:
            executor.execute(grant, cancelled=cancellation)
        except GuestAttachCancelled as error:
            error_reason = str(error)
        else:
            raise ValueError("cancellation control unexpectedly completed inference")
    owner_root = root / "work" / grant.digest
    owner = GuestOwnerJournal(owner_root, suite_root=store.root)
    state = owner.replay()
    created = state.observations["created"]
    cid = created["Id"]
    cleanup_root = owner_root / "control" / cleanup_name
    outcome = fixture.read(cleanup_root, "outcome.json")
    if (
        not cancellation.triggered
        or error_reason != reason
        or observed.creations != 1
        or observed.starts != 0
        or state.phase != phase
        or created["State"]["Running"] is not False
        or created["State"]["StartedAt"] != "0001-01-01T00:00:00Z"
        or outcome["result"] != "absent"
        or outcome["container_id"] != cid
        or not outcome["delete_intended"]
        or outcome["kill_intended"]
    ):
        raise ValueError("cancellation transition, unstarted state or original cleanup differs")
    if case == "cancel_before_start" and outcome["reason"] != "cancelled":
        raise ValueError("watchdog did not observe cancellation")
    absent = api.inspect(cid, deadline=time.monotonic() + 10)
    fixture.save(root, "post-cleanup-observation.json", {"container_id": cid, "inspect": absent})
    if absent is not None:
        raise ValueError("original cancelled container remains present")
    result = {
        "case": case,
        "passed": True,
        "container_id": cid,
        "owner_digest": owner.manifest.digest,
        "grant_digest": grant.digest,
        "phase": phase,
        "reason": error_reason,
        "container_creations": 1,
        "container_starts": 0,
        "scientific_starts": 0,
        "original_container_absent": True,
        "cleanup": outcome,
        "owner_api_requests": observed.calls,
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
        raise ValueError("cancellation source, request or scope changed")
    if tuple(
        q[name]
        for name in (
            "max_container_creations",
            "max_container_starts",
            "max_control_watchdogs",
            "scientific_starts_allowed",
            "fitting_starts_allowed",
            "scoring_starts_allowed",
            "active_seconds_per_case",
            "cleanup_seconds_per_case",
            "post_cleanup_observation_seconds_per_case",
            "automatic_retries",
            "runtime_qualified",
        )
    ) != (2, 0, 1, 0, 0, 0, 20, 10, 10, 0, False):
        raise ValueError("cancellation original bounds differ")
    for case in CASES:
        if digest(fixture.read(root / case, "request.json")) != q["case_requests"][case]:
            raise ValueError("prepared cancellation case changed")
    intent = root / "execution-intent.json"
    if intent.exists() or intent.is_symlink():
        raise ValueError("cancellation controls consumed; no retries")
    fixture.save(
        root, "execution-intent.json", {"request_digest": expected_digest, "starts_allowed": 0}
    )
    results = [run_case(root / case, case) for case in CASES]
    done = {
        "schema": "utility-guest-cancellation-completion-v1",
        "request_digest": expected_digest,
        "results": results,
        "all_passed": True,
        "container_creations": 2,
        "container_starts": 0,
        "scientific_starts": 0,
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
