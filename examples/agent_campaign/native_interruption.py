"""Interrupt one owned scheduler supervisor before credential preflight.

The fixed upstream gate stays closed. Reconciliation uses the original worker
and batch reservations and never launches a replacement client.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import uuid

if __package__ in (None, ""):
    # The parent supplies its explicit installed package root, never PYTHONPATH.
    sys.path.insert(0, sys.argv[sys.argv.index("--package") + 1])
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import autoengineering
from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.command import _bind_host_configuration
from autoengineering.agents.conformance_owner import OwnerLossHost, PHASE, _configuration
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.hosts.subscription import verify_subscription_attempt
from autoengineering.agents.process import (
    recover_completed_process,
    recover_watchdog_stop,
    supervise_process,
)
from autoengineering.agents.records import TaskAssignment
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.campaign.execution import _process_description, live_members
from autoengineering.campaign.records import identifier
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError, durable_write
from examples.agent_campaign.comparison_status import read_json
from examples.agent_campaign.native_evidence import file_digest

VERSION = "matched-native-interruption-1.0"
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}


def owner_command(job):
    return (
        sys.executable,
        "-I",
        str(Path(__file__).resolve()),
        "--job",
        str(job),
        "--package",
        str(Path(autoengineering.__file__).resolve().parent.parent),
    )


class MatchedOwnerHost(OwnerLossHost):
    def invoke_supervised(self, task, prompt, context):
        from dataclasses import replace

        root = Path(context.directory).parent
        durable_write(root / "invocation.json", canonical_json({"nonce": context.nonce}).encode())

        def launched(receipt):
            durable_write(root / "native-ownership.json", canonical_json(receipt).encode())
            context.on_launch(receipt)

        return super().invoke_supervised(task, prompt, replace(context, on_launch=launched))


def _task(worker, batch):
    single = worker.spec.workflow_route == "single_agent"
    return TaskAssignment(
        "1.1" if single else "1.0",
        "matched-owner-interruption",
        worker.spec.id,
        "single_agent" if single else "orchestrator",
        None,
        0,
        "Return a typed stop. This invocation is a trusted interruption control with no scientific feedback.",
        (),
        "role-handoff-1.2" if single else "role-handoff-1.0",
        ("stop",),
        min(
            worker.replay().started_at + worker.spec.limits.elapsed_seconds,
            batch.created_at + batch.spec.limits.elapsed_seconds,
        ),
        0,
    )


def _metadata(runtime, case, worker):
    root = worker.root / "processes"
    root.mkdir(mode=0o700, exist_ok=True)
    config = _configuration(runtime.configuration)
    path = root / "host.toml"
    if path.exists():
        from autoengineering.campaign.artifacts import confined_file

        if confined_file(root, path.name).read_bytes() != config:
            raise StoreError("matched interruption configuration changed")
    else:
        durable_write(path, config)
    fixed = {
        "version": VERSION,
        "preparation": str(runtime.preparation),
        "preparation_digest": runtime.pin,
        "runtime_digest": runtime.batch.digest,
        "conformance_runtime_digest": runtime.conformance_digest,
        "case": case.id,
        "worker_digest": worker.spec.digest,
        "configuration_digest": runtime.configuration.digest,
        "phase": PHASE,
        "driver_sha256": file_digest(Path(__file__).parent, Path(__file__).name),
        "task": _task(worker, runtime.batch).to_dict(),
    }
    path = root / "supervision.json"
    saved = path.exists() or path.is_symlink()
    if not saved:
        durable_write(path, canonical_json({**fixed, "nonce": uuid.uuid4().hex}).encode())
    job = read_json(root, path.name)
    if set(job) != {*fixed, "nonce"} or {k: v for k, v in job.items() if k != "nonce"} != fixed:
        raise StoreError("matched interruption supervision changed")
    identifier(job["nonce"])
    return root, job, saved


def child(job_path):
    from examples.agent_campaign.native_runtime import NativeRuntime

    job_path = Path(job_path).absolute()
    job = read_json(job_path.parent, job_path.name)
    configuration = HostConfiguration.from_file(job_path.parent / "host.toml")
    runtime = NativeRuntime.open(
        job["preparation"],
        expected_digest=job["preparation_digest"],
        configuration=configuration,
        runtime_digest=job["runtime_digest"],
        conformance_runtime_digest=job["conformance_runtime_digest"],
    )
    case = next(c for c in runtime.plan.cases if c.id == job["case"])
    worker = runtime._worker(case)
    root, verified, _ = _metadata(runtime, case, worker)
    if root != job_path.parent or verified != job or runtime.batch.replay().active_case != case.id:
        raise StoreError("matched interruption child scope changed")
    host = MatchedOwnerHost(configuration, runtime.batch, case.id)
    _bind_host_configuration(worker, host, configuration)
    SerialScheduler(worker, host).dispatch(
        TaskAssignment.from_dict(job["task"]), campaign_revision=0
    )


def _phase(runtime, worker, root, job, *, live=False):
    ready = read_json(root, "phase-ready.json")
    calls = [c for c in worker.replay().invocations.values() if c.task_id == job["task"]["id"]]
    if len(calls) != 1:
        raise StoreError("matched interruption must have one original invocation")
    call = calls[0]
    scope = root / call.id
    native, upstream = scope / "transport/client", scope / "upstream/attempt/process"
    supervisor = read_json(root / "supervisor", "process.json")
    if (
        set(ready)
        != {
            "phase",
            "supervision_sha256",
            "owner_pid",
            "owner_started",
            "owner_pgid",
            "native_nonce",
            "native_identity",
            "upstream_identity",
        }
        or ready["phase"] != PHASE
        or ready["supervision_sha256"] != file_digest(root, "supervision.json")
        or ready["native_nonce"] != call.launch_nonce
        or ready["native_identity"] != read_json(root, "native-ownership.json")
        or ready["native_identity"] != read_json(native, "process.json")
        or ready["upstream_identity"] != read_json(upstream, "process.json")
        or ready["owner_pgid"] != supervisor["pgid"]
        or len(
            {
                ready["owner_pgid"],
                ready["native_identity"]["pgid"],
                ready["upstream_identity"]["pgid"],
            }
        )
        != 3
    ):
        raise StoreError("matched interruption readiness ownership changed")
    for directory in (native, upstream):
        watch = read_json(directory, "watchdog-job.json")
        if (watch["owner_pid"], watch["owner_started"]) != (
            ready["owner_pid"],
            ready["owner_started"],
        ):
            raise StoreError("matched watchdog has another supervisor")
    policy, _ = verify_subscription_attempt(scope / "upstream")
    if (policy["model"], policy["lease_id"], policy["credential_path"]) != (
        worker.spec.host.requested_model,
        runtime.configuration.lease_id,
        str(runtime.configuration.credential_path),
    ):
        raise StoreError("matched interruption fixed-worker scope changed")
    if any(
        (scope / n).exists() or (scope / n).is_symlink()
        for n in (
            "upstream/attempt/process/launch-gate.json",
            "upstream/attempt/provider-intent.json",
            "upstream/attempt/provider-result.json",
        )
    ):
        raise StoreError("matched interruption passed the credential-preflight gate")
    if live:
        owner = _process_description(ready["owner_pid"])
        if (
            owner is None
            or owner[0] != ready["owner_started"]
            or ready["owner_pid"] not in live_members(ready["owner_pgid"])
        ):
            raise StoreError("matched supervisor not live at interruption intent")
    return call, ready


def _intent(root, job):
    return {
        "nonce": job["nonce"],
        "phase": PHASE,
        "readiness_sha256": file_digest(root, "phase-ready.json"),
        "supervision_sha256": file_digest(root, "supervision.json"),
    }


def run_interruption(runtime, case, worker):
    root, job, saved = _metadata(runtime, case, worker)
    if not saved:

        def interrupt():
            if not (root / "phase-ready.json").exists():
                return False
            _phase(runtime, worker, root, job, live=True)
            durable_write(
                root / "interruption-intent.json", canonical_json(_intent(root, job)).encode()
            )
            return True

        remaining = (
            runtime.batch.created_at
            + runtime.plan.batch.limits.elapsed_seconds
            - runtime.batch.clock()
        )
        if remaining <= 0:
            raise StoreError("batch expired before interruption supervisor")
        supervise_process(
            owner_command(root / "supervision.json"),
            directory=root / "supervisor",
            cwd=root,
            environment=ENVIRONMENT,
            nonce=job["nonce"],
            stdin=b"",
            timeout_seconds=min(30, remaining),
            max_output_bytes=8192,
            on_launch=lambda _: None,
            cancelled=interrupt,
            parent_watchdog=True,
        )
    # A saved supervisor intent is never relaunched, even if no ready receipt exists.
    expected_job = {
        "command": list(owner_command(root / "supervision.json")),
        "cwd": str(root),
        "environment": ENVIRONMENT,
        "keep_group_leader": True,
        "owner_lease": "pipe-eof-v1",
    }
    if read_json(root / "supervisor", "job.json") != expected_job or read_json(
        root / "supervisor", "intent.json"
    ) != {"nonce": job["nonce"]}:
        raise StoreError("matched supervisor command/nonce changed")
    pending = {"passed": False, "reconciliation_required": True, "kind": VERSION}
    try:
        if (root / "supervisor/completion.json").exists():
            result = recover_completed_process(
                root / "supervisor", nonce=job["nonce"], max_output_bytes=8192
            )
            supervisor = {
                "status": result.status,
                "stopped": result.stopped,
                "completion": read_json(root / "supervisor", "completion.json"),
            }
        else:
            supervisor = {
                "status": "owner_lost",
                "stopped": True,
                "watchdog": recover_watchdog_stop(root / "supervisor"),
            }
    except (ValueError, OSError):
        return pending
    if not (root / "phase-ready.json").exists():
        # Missing readiness cannot authorize numerical work, even after an early local failure.
        return {**pending, "supervisor": supervisor, "reason": "intended_phase_not_proven"}
    call, ready = _phase(runtime, worker, root, job)
    stops = []
    deadline = time.monotonic() + 3
    while True:
        try:
            stops = [
                recover_watchdog_stop(root / call.id / n)
                for n in ("transport/client", "upstream/attempt/process")
            ]
            break
        except (ValueError, OSError):
            if time.monotonic() >= deadline:
                return pending
            time.sleep(0.02)
    recovered = SerialScheduler(
        worker, BatchCodexHost(runtime.configuration, runtime.batch, case.id)
    ).recover_invocation(call.id, campaign_revision=0)
    intended = read_json(root, "interruption-intent.json") == _intent(root, job)
    valid = (
        intended
        and supervisor["stopped"]
        and supervisor["status"] in ("cancelled", "owner_lost")
        and recovered.state == "host_failure"
        and recovered.elapsed_seconds is None
        and recovered.resolved_model is None
        and not recovered.usage
    )
    bindings = {
        n: file_digest(root, n)
        for n in (
            "supervision.json",
            "phase-ready.json",
            "interruption-intent.json",
            "native-ownership.json",
            "supervisor/job.json",
            "supervisor/intent.json",
            "supervisor/process.json",
        )
    }
    # Bind every stop/launch receipt that justified reconciliation. Reporting
    # checks saved hashes rather than importing process or host implementations.
    for prefix in (f"{call.id}/transport/client", f"{call.id}/upstream/attempt/process"):
        for name in (
            "job.json",
            "intent.json",
            "process.json",
            "watchdog-job.json",
            "watchdog-ready.json",
            "watchdog-result.json",
        ):
            bindings[f"{prefix}/{name}"] = file_digest(root, f"{prefix}/{name}")
    for name in (
        f"{call.id}/adapter.json",
        f"{call.id}/transport/transport.json",
        f"{call.id}/upstream/policy.json",
        f"{call.id}/upstream/attempt/upstream.json",
    ):
        bindings[name] = file_digest(root, name)
    for name in ("completion.json", "watchdog-result.json"):
        if (root / "supervisor" / name).exists():
            bindings[f"supervisor/{name}"] = file_digest(root, f"supervisor/{name}")
    proof = runtime.batch.evidence(
        {
            "kind": VERSION,
            "supervision": job,
            "readiness": ready,
            "supervisor": supervisor,
            "native_stop": stops[0],
            "upstream_stop": stops[1],
            "bindings": bindings,
            "call_digest": recovered.digest,
        }
    )
    receipt = {
        "kind": VERSION,
        "passed": bool(valid),
        "reconciliation_required": False,
        "call_id": call.id,
        "evidence": proof.to_dict(),
        "credential_preflight": "not_started",
        "request_may_have_been_sent": False,
        "usage": {},
        "elapsed_seconds": None,
        "resolved_model": None,
        "remote_computation_stopped": "unknown",
    }
    path = root / "interruption.json"
    if path.exists() or path.is_symlink():
        if read_json(root, path.name) != receipt:
            raise StoreError("saved interruption verdict changed")
    else:
        durable_write(path, canonical_json(receipt).encode())
    return receipt


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    child(parser.parse_args().job)
