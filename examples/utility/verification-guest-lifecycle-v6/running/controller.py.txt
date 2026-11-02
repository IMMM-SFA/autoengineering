"""Cancel one actually running exposed guest before its input transfer.

Keep the charged start, original watchdog proof and saved nonnumeric failure.
This does not establish cancellation during model computation.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_attach import GuestAttachCancelled
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_watchdog import GuestWatchdogPlan, read_outcome
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture
from examples.utility.guest_owner_loss_controls import APIJournal, reserve


def helper_digest():
    from examples.utility import guest_owner_loss_controls

    return hashlib.sha256(Path(guest_owner_loss_controls.__file__).read_bytes()).hexdigest()


def prepare(frozen_fixture, resources, environment, *, resource_digest, output):
    frozen_fixture = checked_directory(frozen_fixture)
    q = fixture.prepare(
        frozen_fixture / "owner",
        frozen_fixture / "suite",
        frozen_fixture / "source",
        frozen_fixture / "drivers",
        resources,
        environment,
        resource_digest=resource_digest,
        output=output,
    )
    output = checked_directory(output)
    control = {
        "schema": "utility-running-guest-cancellation-v1",
        "prepared_request_digest": digest(q),
        "scope_digest": digest(str(output)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "helper_sha256": helper_digest(),
        "max_container_creations": 1,
        "max_container_starts": 1,
        "max_watchdogs": 1,
        "fitting_starts_allowed": 0,
        "scoring_starts_allowed": 0,
        "automatic_retries": 0,
        "active_seconds": 20,
        "cleanup_seconds": 10,
        "post_cleanup_observation_seconds": 10,
        "cancel_at": "started_before_input",
        "runtime_qualified": False,
    }
    fixture.save(output, "control-request.json", control)
    durable_write(output / "controller.py.txt", Path(__file__).read_bytes())
    return control


class RunningCancellation:
    def __init__(self, root, store, grant):
        self.root, self.store, self.grant = root, store, grant
        self.triggered = False

    def __call__(self):
        if self.triggered:
            return True
        directory = self.root / "work" / self.grant.digest
        if not (directory / "owner.json").is_file():
            return False
        owner = GuestOwnerJournal(directory, suite_root=self.store.root)
        state = owner.replay()
        if state.phase != "started":
            return False
        if state.observations["started"]["State"]["Running"] is not True:
            raise ValueError("running cancellation requires an actually running guest")
        fixture.save(
            self.root,
            "cancellation-trigger.json",
            {
                "owner_digest": owner.manifest.digest,
                "grant_digest": self.grant.digest,
                "event_digest": state.events[-1].digest,
                "phase": "started",
                "running": True,
                "boundary": "before_input_transfer",
            },
        )
        self.triggered = True
        return True


def execute(root, *, expected_digest):
    root = checked_directory(root)
    control, q = fixture.read(root, "control-request.json"), fixture.read(root, "request.json")
    if (
        digest(control) != expected_digest
        or control["prepared_request_digest"] != digest(q)
        or control["scope_digest"] != digest(str(root))
        or control["runner_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        or control["helper_sha256"] != helper_digest()
    ):
        raise ValueError("running cancellation source, request or scope changed")
    if tuple(
        control[name]
        for name in (
            "max_container_creations",
            "max_container_starts",
            "max_watchdogs",
            "fitting_starts_allowed",
            "scoring_starts_allowed",
            "automatic_retries",
            "active_seconds",
            "cleanup_seconds",
            "post_cleanup_observation_seconds",
            "cancel_at",
            "runtime_qualified",
        )
    ) != (1, 1, 1, 0, 0, 0, 20, 10, 10, "started_before_input", False):
        raise ValueError("running cancellation original bounds differ")
    if (root / "execution-intent.json").exists() or (root / "execution-intent.json").is_symlink():
        raise ValueError("running cancellation consumed; no retry")
    fixture.save(
        root, "execution-intent.json", {"request_digest": expected_digest, "starts_reserved": 1}
    )
    binding = fixture.read(root, "bindings.json")
    if fixture.build._endpoint(binding["endpoint"]) != q["endpoint"]:
        raise ValueError("running cancellation endpoint changed")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(q["grant"])
    if grant.inference.forcing.prior_exposure != "exposed" or grant.inference.timeout_seconds != 20:
        raise ValueError("running cancellation exposure or timeout differs")
    api = GuestDaemonAPI(
        binding["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    if api.profile.to_dict() != q["daemon"]:
        raise ValueError("running cancellation API implementation changed")
    journal = APIJournal(api, root / "api-observations", starts_allowed=1, create_allowed=1)
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
    cancellation = RunningCancellation(root, store, grant)
    reserve(root)
    with store.writer():
        try:
            executor.execute(grant, cancelled=cancellation)
        except GuestAttachCancelled as error:
            if str(error) != "guest dispatch cancelled":
                raise
        else:
            raise ValueError("running cancellation unexpectedly completed inference")
        if not cancellation.triggered or journal.creations != 1 or journal.starts != 1:
            raise ValueError("running cancellation did not reach its exact original boundary")
        owner_root = root / "work" / grant.digest
        owner = GuestOwnerJournal(owner_root, suite_root=store.root)
        guard = owner_root / "control/guest-watchdog"
        plan = GuestWatchdogPlan.from_dict(fixture.read(guard, "plan.json"))
        outcome = read_outcome(guard, owner, plan)
        if (
            outcome.reason != "cancelled"
            or outcome.result != "absent"
            or not outcome.delete_intended
        ):
            raise ValueError("running cancellation original watchdog cleanup differs")
        if (owner_root / "bootstrap-capture.json").exists():
            raise ValueError("pre-input cancellation unexpectedly has model capture")
        recovered = GuestRoutingExecutor.for_recovery(store, grant, root / "work").recover(grant)
        if (
            recovered.status != "infrastructure_failure"
            or recovered.result is not None
            or recovered.lifecycle_seconds is not None
            or recovered.container_starts != 1
        ):
            raise ValueError(
                "running cancellation did not retain a nonnumeric saved failure and unknown time"
            )
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
            raise ValueError("running cancellation allowed redispatch")
        if journal.calls != before:
            raise ValueError("running cancellation redispatch refusal contacted the daemon")
    cid = outcome.container_id
    absent = api.inspect(cid, deadline=time.monotonic() + 10)
    fixture.save(root, "post-cleanup-observation.json", {"container_id": cid, "inspect": absent})
    if absent is not None:
        raise ValueError("original cancelled running guest remains present")
    done = {
        "schema": "utility-running-guest-cancellation-completion-v1",
        "request_digest": expected_digest,
        "container_id": cid,
        "container_creations": 1,
        "container_starts": 1,
        "charged_inference_starts": 1,
        "cleanup": outcome.to_dict(),
        "recovered": recovered.to_dict(),
        "retry_daemon_requests": 0,
        "parent_composite_reservation_retained": True,
        "inference_elapsed_seconds": None,
        "all_passed": True,
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
