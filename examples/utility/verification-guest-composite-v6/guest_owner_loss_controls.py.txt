"""Four actual owned-process loss controls over an exposed frozen fixture.

Only exact Popen handles are killed. Original container cleanup and saved-only
recovery retain charges and unknown time. No fitting/scoring/provider work.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import uuid4

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.utility import guest_dispatch
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_watchdog import GuestWatchdogPlan, read_outcome
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture

CASES = {
    "owner_loss_before_watchdog_ready": ("watchdog_intended", "created", 0),
    "owner_loss_running": ("before_guest_input", "started", 1),
    "owner_loss_after_capture": ("guest_capture_saved", "started", 1),
    "watchdog_child_loss_before_start": ("after_guest_attach", "created", 0),
}


class APIJournal:
    def __init__(self, api, root, *, starts_allowed, create_allowed):
        self.original, self.root = api._request, root
        self.starts_allowed, self.create_allowed = starts_allowed, create_allowed
        self.calls = self.starts = self.creations = self.deletions = 0
        root.mkdir(mode=0o700)
        api._request = self.request

    def request(self, method, path, value=None, *, deadline, cancelled=None):
        if method == "POST" and path.startswith("/containers/create"):
            self.creations += 1
            if self.creations > self.create_allowed:
                raise RuntimeError("owner-loss control refused unallowed/repeated CREATE")
        if method == "POST" and path.endswith("/start"):
            self.starts += 1
            if self.starts > self.starts_allowed:
                raise RuntimeError("owner-loss control refused unallowed/repeated START")
        if method == "DELETE":
            self.deletions += 1
            if self.deletions > 1:
                raise RuntimeError("owner-loss control refused repeated owner DELETE")
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


def context(root, *, parent=False, case):
    q, binding = fixture.read(root, "request.json"), fixture.read(root, "bindings.json")
    if fixture.build._endpoint(binding["endpoint"]) != q["endpoint"]:
        raise ValueError("owner-loss local endpoint changed")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(q["grant"])
    if grant.inference.forcing.prior_exposure != "exposed" or grant.inference.timeout_seconds != 20:
        raise ValueError("owner-loss exposure or original timeout differs")
    api = GuestDaemonAPI(
        binding["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    if api.profile.to_dict() != q["daemon"]:
        raise ValueError("owner-loss daemon implementation differs")
    journal = APIJournal(
        api,
        root / ("parent-api" if parent else "child-api"),
        starts_allowed=0 if parent else CASES[case][2],
        create_allowed=0 if parent else 1,
    )
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
    return store, grant, api, journal, executor


def child(root, *, case, nonce, controller_sha256):
    root = checked_directory(root)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != controller_sha256:
        raise ValueError("owner-loss child controller changed")
    intent = fixture.read(root, "child-intent.json")
    if intent != {"case": case, "nonce": nonce, "controller_sha256": controller_sha256}:
        raise ValueError("owner-loss child differs from original intent")
    signal.alarm(20)  # A lost parent cannot leave the paused Python owner indefinitely.
    store, grant, api, journal, executor = context(root, case=case)
    original_setup = executor.reconcile_initialization
    original_arm = guest_dispatch.arm
    armed = None

    def arm(*args, **kwargs):
        nonlocal armed
        armed = original_arm(*args, **kwargs)
        return armed

    guest_dispatch.arm = arm

    def setup(value):
        owner = original_setup(value)

        def fault(stage):
            if stage != CASES[case][0]:
                return
            state = owner.replay()
            if state.phase != CASES[case][1]:
                raise ValueError("owner-loss hook reached a different original phase")
            if (
                case == "owner_loss_running"
                and state.observations["started"]["State"]["Running"] is not True
            ):
                raise ValueError("running owner-loss requires an actually running guest")
            marker = {
                "case": case,
                "nonce": nonce,
                "child_pid": os.getpid(),
                "stage": stage,
                "owner_digest": owner.manifest.digest,
                "journal_phase": state.phase,
                "journal_head": state.events[-1].digest,
                "container_id": state.observations["created"]["Id"],
            }
            if case == "watchdog_child_loss_before_start":
                ready = armed.check_live()
                armed.process.kill()
                code = armed.process.wait(timeout=5)
                if code != -signal.SIGKILL:
                    raise ValueError("owned watchdog did not stop by the intended signal")
                marker.update(watchdog_pid=ready.watchdog_pid, watchdog_returncode=code)
                fixture.save(root, "stage-ready.json", marker)
                return
            fixture.save(root, "stage-ready.json", marker)
            signal.pause()  # Parent kills only this exact owned Popen handle.
            raise ValueError("owner-loss pause unexpectedly returned")

        owner.fault = fault
        return owner

    executor.reconcile_initialization = setup
    with store.writer():
        try:
            executor.execute(grant)
        except StoreError as error:
            if (
                case != "watchdog_child_loss_before_start"
                or str(error) != "original guest watchdog is not live within its deadline"
            ):
                raise
            fixture.save(
                root,
                "child-result.json",
                {
                    "case": case,
                    "reason": str(error),
                    "container_creations": journal.creations,
                    "container_starts": journal.starts,
                    "watchdog_killed": True,
                },
            )
        else:
            raise ValueError("owner-loss hook did not interrupt execution")
    signal.alarm(0)


def prepare(frozen_fixture, resources, environment, *, resource_digest, output):
    frozen_fixture = checked_directory(frozen_fixture)
    output = Path(output).absolute()
    fixture.build.guest_image._public_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("owner-loss output must be absent")
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
        "schema": "utility-guest-owner-loss-controls-v1",
        "case_requests": requests,
        "case_policy": {name: list(value) for name, value in CASES.items()},
        "scope_digest": digest(str(output)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "max_container_creations": 4,
        "max_container_starts": 2,
        "max_control_watchdogs": 3,
        "max_owner_children": 4,
        "max_owner_sigkills": 3,
        "max_watchdog_sigkills": 1,
        "fitting_starts_allowed": 0,
        "scoring_starts_allowed": 0,
        "automatic_retries": 0,
        "active_seconds_per_case": 20,
        "cleanup_seconds_per_case": 10,
        "post_cleanup_observation_seconds_per_case": 10,
        "runtime_qualified": False,
    }
    fixture.save(output, "request.json", q)
    durable_write(output / "runner.py.txt", Path(__file__).read_bytes())
    return q


def reserve(root):
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(fixture.read(root, "request.json")["grant"])
    with store.writer():
        args = dict(
            cell_digest=grant.cell_digest,
            attempt_id="confirmation-" + grant.cell_digest[:48],
            child_digest=grant.digest,
            phase="confirmation",
        )
        store.append(
            request_id="owner-loss-reserve", operation="reserve", resources=grant.resources, **args
        )
        store.append(request_id="owner-loss-start", operation="start", **args)
        ref = put_bytes(
            store.root,
            grant.to_json().encode(),
            name="confirmation-grant.json",
            media_type="application/json",
            producer="authored-owner-loss",
        )
        store.append(
            request_id="owner-loss-access",
            operation="confirmation_access",
            result_digest=ref.sha256,
            **args,
        )


def run_case(root, case, controller_sha256):
    reserve(root)
    nonce = uuid4().hex
    fixture.save(
        root,
        "child-intent.json",
        {"case": case, "nonce": nonce, "controller_sha256": controller_sha256},
    )
    with (root / "child.log").open("xb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "examples.utility.guest_owner_loss_controls",
                "child",
                str(root),
                "--case",
                case,
                "--nonce",
                nonce,
                "--controller-sha256",
                controller_sha256,
            ],
            cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        fixture.save(
            root, "child-launched.json", {"case": case, "nonce": nonce, "pid": process.pid}
        )
        try:
            end = time.monotonic() + 15
            while (
                not (root / "stage-ready.json").exists()
                and process.poll() is None
                and time.monotonic() < end
            ):
                time.sleep(0.02)
            marker = fixture.read(root, "stage-ready.json")
            if (marker["case"], marker["nonce"], marker["child_pid"], marker["stage"]) != (
                case,
                nonce,
                process.pid,
                CASES[case][0],
            ):
                raise ValueError("owner-loss stage differs from exact owned child")
            if case != "watchdog_child_loss_before_start":
                if process.poll() is not None:
                    raise ValueError("owned owner exited before intended SIGKILL")
                fixture.save(
                    root,
                    "owner-kill-intent.json",
                    {"pid": process.pid, "nonce": nonce, "signal": "SIGKILL"},
                )
                process.kill()
            code = process.wait(timeout=10)
            expected = 0 if case == "watchdog_child_loss_before_start" else -signal.SIGKILL
            fixture.save(
                root, "child-stopped.json", {"pid": process.pid, "nonce": nonce, "returncode": code}
            )
            if code != expected:
                raise ValueError("owned owner did not have the expected terminal status")
        finally:
            if process.poll() is None:
                fixture.save(
                    root, "fallback-child-kill-intent.json", {"pid": process.pid, "nonce": nonce}
                )
                process.kill()
                process.wait(timeout=5)
    store, grant, api, journal, executor = context(root, parent=True, case=case)
    owner_root = root / "work" / grant.digest
    owner = GuestOwnerJournal(owner_root, suite_root=store.root)
    guard = owner_root / "control/guest-watchdog"
    if case == "owner_loss_before_watchdog_ready":
        with store.writer():
            executor.cleanup_watchdog_startup(grant)
    else:
        end = time.monotonic() + 12
        while not (guard / "outcome.json").exists() and time.monotonic() < end:
            time.sleep(0.02)
    plan = GuestWatchdogPlan.from_dict(fixture.read(guard, "plan.json"))
    outcome = read_outcome(guard, owner, plan)
    starts = CASES[case][2]
    if (
        outcome.result != "absent"
        or outcome.container_id != marker["container_id"]
        or outcome.reason != ("owner_lost" if starts else "startup_refused")
    ):
        raise ValueError("original owner-loss cleanup differs")
    recovered = None
    if case == "owner_loss_after_capture":
        with store.writer():
            result = GuestRoutingExecutor.for_recovery(store, grant, root / "work").recover(grant)
        if result.status != "success" or result.lifecycle_seconds is not None:
            raise ValueError(
                "captured owner-loss result did not recover with unknown lifecycle time"
            )
        recovered = result.to_dict()
    with store.writer():
        before = journal.calls
        try:
            executor.execute(grant)
        except StoreError as error:
            if (
                str(error)
                != "guest attempt already intended; explicit saved-evidence recovery only"
            ):
                raise
        else:
            raise ValueError("original owner-loss attempt permitted redispatch")
        if journal.calls != before:
            raise ValueError("redispatch refusal contacted the daemon")
    cid = outcome.container_id
    absent = api.inspect(cid, deadline=time.monotonic() + 10)
    fixture.save(root, "post-cleanup-observation.json", {"container_id": cid, "inspect": absent})
    if absent is not None:
        raise ValueError("original owner-loss container remains present")
    result = {
        "case": case,
        "passed": True,
        "container_id": cid,
        "owner_digest": owner.manifest.digest,
        "stage": marker["stage"],
        "phase_at_loss": marker["journal_phase"],
        "owner_returncode": code,
        "container_creations": 1,
        "container_starts": starts,
        "charged_inference_starts": starts,
        "inference_elapsed_seconds": None,
        "original_container_absent": True,
        "cleanup": outcome.to_dict(),
        "recovered": recovered,
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
        or set(q["case_requests"]) != set(CASES)
    ):
        raise ValueError("owner-loss source, request or scope changed")
    if tuple(
        q[name]
        for name in (
            "max_container_creations",
            "max_container_starts",
            "max_control_watchdogs",
            "max_owner_children",
            "max_owner_sigkills",
            "max_watchdog_sigkills",
            "fitting_starts_allowed",
            "scoring_starts_allowed",
            "automatic_retries",
            "active_seconds_per_case",
            "cleanup_seconds_per_case",
            "post_cleanup_observation_seconds_per_case",
            "runtime_qualified",
        )
    ) != (4, 2, 3, 4, 3, 1, 0, 0, 0, 20, 10, 10, False):
        raise ValueError("owner-loss original bounds differ")
    for case in CASES:
        if digest(fixture.read(root / case, "request.json")) != q["case_requests"][case]:
            raise ValueError("prepared owner-loss case changed")
    if (root / "execution-intent.json").exists() or (root / "execution-intent.json").is_symlink():
        raise ValueError("owner-loss controls consumed; no retries")
    fixture.save(
        root, "execution-intent.json", {"request_digest": expected_digest, "starts_reserved": 2}
    )
    results = [run_case(root / case, case, q["runner_sha256"]) for case in CASES]
    done = {
        "schema": "utility-guest-owner-loss-completion-v1",
        "request_digest": expected_digest,
        "results": results,
        "all_passed": True,
        "container_creations": 4,
        "container_starts": 2,
        "charged_inference_starts": 2,
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
    worker = sub.add_parser("child")
    worker.add_argument("root", type=Path)
    worker.add_argument("--case", choices=tuple(CASES), required=True)
    worker.add_argument("--nonce", required=True)
    worker.add_argument("--controller-sha256", required=True)
    a = p.parse_args()
    if a.command == "child":
        child(a.root, case=a.case, nonce=a.nonce, controller_sha256=a.controller_sha256)
        return
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
