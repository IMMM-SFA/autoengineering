"""Fixed owner-loss case. Interrupt only its owned supervisor before lease preflight.

The worker launch gate remains closed. No credential is opened, provider contacted
or native result invented. Recovery never starts a replacement supervisor/client.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import time
import uuid

# Isolated child entry must use the package beside this source, including in a wheel.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.hosts.subscription import ScopedSubscriptionUpstream
from autoengineering.agents.hosts.subscription import verify_subscription_attempt
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import (
    recover_completed_process,
    recover_watchdog_stop,
    supervise_process,
)
from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.execution import _process_description, live_members
from autoengineering.campaign.records import ArtifactRef, identifier
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import StoreError, durable_write

VERSION = "conformance-owner-loss-1.0"
PHASE = "fixed_worker_launch_gate_closed_before_credential_preflight"
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise StoreError("owner-loss receipt exceeds 64 KiB")
    return unique_json(path.read_text())


def _sha(path):
    return hashlib.sha256(confined_file(path.parent, path.name).read_bytes()).hexdigest()


def owner_command(job):
    return (sys.executable, "-I", str(Path(__file__).resolve()), "--job", str(job))


def _configuration(configuration):
    values = {
        "schema_version": "1.0",
        "qualification_root": str(configuration.qualification_root),
        "qualification_digest": configuration.qualification_digest,
        "credential_path": str(configuration.credential_path),
        "lease_id": configuration.lease_id,
    }
    return "".join(f"{key} = {canonical_json(value)}\n" for key, value in values.items()).encode()


def _metadata(runtime, root):
    config = root / "host.toml"
    raw = _configuration(runtime.configuration)
    if config.exists() or config.is_symlink():
        if confined_file(root, config.name).read_bytes() != raw:
            raise StoreError("owner-loss host metadata changed")
    else:
        durable_write(config, raw)
    fixed = {
        "version": VERSION,
        "source_identity": host_source_identity(),
        "preparation": str(runtime.preparation),
        "preparation_digest": runtime.preparation_digest,
        "runtime_digest": runtime.batch.digest,
        "configuration": str(config),
        "configuration_digest": runtime.configuration.digest,
        "phase": PHASE,
        "supervisor_seconds": 30,
    }
    path = root / "supervision.json"
    saved = path.exists() or path.is_symlink()
    if not saved:
        durable_write(path, canonical_json({**fixed, "nonce": uuid.uuid4().hex}).encode())
    job = _json(root, path.name)
    if set(job) != {*fixed, "nonce"} or {k: v for k, v in job.items() if k != "nonce"} != fixed:
        raise StoreError("owner-loss supervisor binding changed")
    identifier(job["nonce"])
    return job, saved


class OwnerLossHost(BatchCodexHost):
    """Fixed preflight hold inside this case's supervisor, never a worker option."""

    def _upstream(self, root, workspace, home, deadline, cancelled):
        def hold(receipt):
            metadata = _json(root.parent, "invocation.json")
            description = _process_description(os.getpid())
            if description is None:
                raise StoreError("owner-loss supervisor identity unavailable")
            durable_write(
                root.parent / "phase-ready.json",
                canonical_json(
                    {
                        "phase": PHASE,
                        "supervision_sha256": _sha(root.parent / "supervision.json"),
                        "owner_pid": os.getpid(),
                        "owner_started": description[0],
                        "owner_pgid": os.getpgrp(),
                        "native_nonce": metadata["nonce"],
                        "native_identity": _json(root.parent, "native-ownership.json"),
                        "upstream_identity": receipt,
                    }
                ).encode(),
            )
            # The trusted parent must interrupt us. Expiry raises before the
            # launch callback returns, so preflight cannot run even on failure.
            while time.monotonic() < deadline:
                time.sleep(0.01)
            raise TimeoutError("owner-loss gate expired before intended interruption")

        return ScopedSubscriptionUpstream(
            root / "upstream",
            credential_path=self.credential_path,
            lease_id=self.lease_id,
            model=self.model,
            client_roots=(workspace, home),
            deadline_monotonic=deadline,
            cancelled=cancelled,
            on_launch=hold,
        )


def child(job_path):
    from autoengineering.agents.conformance_runtime import ConformanceRuntime, TEXT_PROMPT

    job_path = Path(job_path).absolute()
    root = job_path.parent
    job = _json(root, job_path.name)
    if job_path.name != "supervision.json" or job.get("source_identity") != host_source_identity():
        raise StoreError("owner-loss child source or job binding changed")
    configuration = HostConfiguration.from_file(Path(job["configuration"]))
    runtime = ConformanceRuntime.open(
        Path(job["preparation"]),
        expected_digest=job["preparation_digest"],
        configuration=configuration,
        runtime_digest=job["runtime_digest"],
    )
    expected_root = runtime.batch.root / "cases/owner_loss"
    if root != expected_root or _metadata(runtime, root)[0] != job:
        raise StoreError("owner-loss child scope changed")
    if runtime.batch.replay().active_case != "owner_loss":
        raise StoreError("owner-loss case is not active")
    runtime._direct(
        "owner_loss", TEXT_PROMPT, host=OwnerLossHost(configuration, runtime.batch, "owner_loss")
    )


def _phase(runtime, root, *, live=False):
    ready = _json(root, "phase-ready.json")
    scope = root / "owner_loss-call"
    native, upstream = scope / "transport/client", scope / "upstream/attempt/process"
    metadata = _json(root, "invocation.json")
    supervisor = _json(root / "supervisor", "process.json")
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
        or ready["supervision_sha256"] != _sha(root / "supervision.json")
        or ready["native_nonce"] != metadata["nonce"]
        or ready["native_identity"] != _json(root, "native-ownership.json")
        or ready["native_identity"] != _json(native, "process.json")
        or ready["upstream_identity"] != _json(upstream, "process.json")
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
        raise StoreError("owner-loss readiness ownership mismatch")
    for directory in (native, upstream):
        watchdog = _json(directory, "watchdog-job.json")
        if (watchdog["owner_pid"], watchdog["owner_started"]) != (
            ready["owner_pid"],
            ready["owner_started"],
        ):
            raise StoreError("owner-loss watchdog belongs to another supervisor")
    policy, _ = verify_subscription_attempt(scope / "upstream")
    if (policy["credential_path"], policy["lease_id"], policy["model"]) != (
        str(runtime.configuration.credential_path),
        runtime.configuration.lease_id,
        runtime.plan.worker.host.requested_model,
    ):
        raise StoreError("owner-loss fixed worker scope mismatch")
    for path in (
        upstream / "launch-gate.json",
        scope / "upstream/attempt/provider-intent.json",
        scope / "upstream/attempt/provider-result.json",
    ):
        if path.exists() or path.is_symlink():
            raise StoreError("owner-loss case passed its intended preflight gate")
    if live:
        description = _process_description(ready["owner_pid"])
        if (
            description is None
            or description[0] != ready["owner_started"]
            or ready["owner_pid"] not in live_members(ready["owner_pgid"])
        ):
            raise StoreError("owner-loss supervisor is not live at interruption intent")
    return ready


def _intent(root, job):
    return {
        "nonce": job["nonce"],
        "phase": PHASE,
        "readiness_sha256": _sha(root / "phase-ready.json"),
        "supervisor": _json(root / "supervisor", "process.json"),
    }


def _launch(runtime, root, job):
    def interrupt():
        if not (root / "phase-ready.json").exists():
            return False
        _phase(runtime, root, live=True)
        durable_write(
            root / "interruption-intent.json", canonical_json(_intent(root, job)).encode()
        )
        return True

    remaining = (
        runtime.batch.created_at + runtime.plan.batch.limits.elapsed_seconds - runtime.batch.clock()
    )
    if remaining <= 0:
        raise StoreError("batch deadline exhausted before owner-loss supervisor launch")
    return supervise_process(
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


def _supervisor_stop(root, job):
    expected = {
        "command": list(owner_command(root / "supervision.json")),
        "cwd": str(root),
        "environment": ENVIRONMENT,
        "keep_group_leader": True,
        "owner_lease": "pipe-eof-v1",
    }
    if _json(root / "supervisor", "job.json") != expected:
        raise StoreError("owner-loss supervisor command changed")
    if _json(root / "supervisor", "intent.json") != {"nonce": job["nonce"]}:
        raise StoreError("owner-loss supervisor nonce changed")
    if (root / "supervisor/completion.json").exists():
        result = recover_completed_process(
            root / "supervisor", nonce=job["nonce"], max_output_bytes=8192
        )
        return {
            "status": result.status,
            "stop_verified": result.stopped,
            "completion": _json(root / "supervisor", "completion.json"),
        }
    return {
        "status": "owner_lost",
        "stop_verified": True,
        "watchdog": recover_watchdog_stop(root / "supervisor"),
    }


def _supervisor_captures(runtime, root, supervisor):
    if "completion" not in supervisor:
        return []
    return [
        put_bytes(
            runtime.batch.root,
            confined_file(root / "supervisor", name + ".bin").read_bytes(),
            name="supervisor-" + name + ".bin",
            media_type="application/octet-stream",
            producer="owner-loss-supervisor-capture",
        ).to_dict()
        for name in ("stdout", "stderr")
    ]


def run_owner_loss(runtime):
    from autoengineering.agents.conformance_runtime import TEXT_PROMPT

    root = runtime.batch.root / "cases/owner_loss"
    root.mkdir(mode=0o700, exist_ok=True)
    job, saved = _metadata(runtime, root)
    if not saved:
        _launch(runtime, root, job)
    pending = {"kind": "owner_loss", "passed": False, "reconciliation_required": True}
    try:
        supervisor = _supervisor_stop(root, job)
    except (ValueError, OSError):
        return pending
    supervisor_captures = _supervisor_captures(runtime, root, supervisor)
    if not (root / "invocation.json").exists():
        return {
            "kind": "owner_loss",
            "passed": False,
            "intended_phase_exercised": False,
            "reason": "supervisor_stopped_before_native_invocation",
            "captures": supervisor_captures,
            "ownership": {
                "verified": False,
                "evidence": runtime.batch.evidence(supervisor).to_dict(),
            },
        }
    # A conclusively completed native failure before readiness is unexercised,
    # not an abandoned two-worker launch. Let its normal decoder verify the stop.
    if not (root / "phase-ready.json").exists() and supervisor["status"] not in (
        "cancelled",
        "owner_lost",
    ):
        try:
            early, _ = runtime._direct("owner_loss", TEXT_PROMPT)
        except (ValueError, OSError):
            return pending
        if not early.stop_verified or early.status == "reconciliation_required":
            return pending
        return {
            "kind": "owner_loss",
            "passed": False,
            "intended_phase_exercised": False,
            "reason": "native_stopped_before_interruption_gate",
            "host_status": early.status,
            "stop_verified": True,
            "resolved_model": early.resolved_model,
            "elapsed_seconds": early.elapsed_seconds,
            "usage": dict(early.usage),
            "captures": supervisor_captures,
            "transcripts": runtime._capture_transcripts(early),
            "ownership": {
                "verified": False,
                "evidence": runtime.batch.evidence(supervisor).to_dict(),
            },
        }
    # Wait only for the already launched independent watchdogs. No signals or retry.
    scope = root / "owner_loss-call"
    deadline = time.monotonic() + 3
    while True:
        try:
            stops = [
                recover_watchdog_stop(directory)
                for directory in (scope / "transport/client", scope / "upstream/attempt/process")
            ]
            break
        except (ValueError, OSError):
            if time.monotonic() >= deadline:
                return pending
            time.sleep(0.02)
    result, scope = runtime._direct("owner_loss", TEXT_PROMPT)
    try:
        ready = _phase(runtime, root)
        intent = _json(root, "interruption-intent.json")
        intended = intent == _intent(root, job)
    except (ValueError, OSError):
        return {
            "kind": "owner_loss",
            "passed": False,
            "intended_phase_exercised": False,
            "host_status": result.status,
            "stop_verified": result.stop_verified,
            "captures": supervisor_captures,
            "ownership": {
                "verified": False,
                "evidence": runtime.batch.evidence(supervisor).to_dict(),
            },
        }
    proof = runtime.batch.evidence(
        {
            "kind": "owned_supervisor_interruption_before_credential_preflight",
            "supervision": job,
            "supervisor_stop": supervisor,
            "readiness": ready,
            "interruption_intent": intent,
            "native_stop": stops[0],
            "upstream_stop": stops[1],
            "bindings": {
                name: _json(scope, name)
                for name in (
                    "adapter.json",
                    "transport/transport.json",
                    "transport/client/job.json",
                    "transport/client/watchdog-job.json",
                    "transport/client/process.json",
                    "upstream/policy.json",
                    "upstream/attempt/upstream.json",
                    "upstream/attempt/process/job.json",
                    "upstream/attempt/process/watchdog-job.json",
                    "upstream/attempt/process/process.json",
                )
            },
        }
    )
    captured = [
        (Path(name).name, confined_file(scope, name).read_bytes())
        for name in ("transport/client/stdin.bin", "upstream/attempt/request.bin")
    ]
    transport = _json(scope / "transport", "transport.json")
    for reference in (transport["schema"], transport["boundary_policy"]["artifact"]):
        ref = ArtifactRef.from_dict(reference)
        captured.append(
            (Path(ref.path).name, read_bytes(scope / "transport", ref, max_bytes=65536))
        )
    captures = [
        put_bytes(
            runtime.batch.root,
            raw,
            name=name,
            media_type="application/octet-stream",
            producer="owner-loss-bound-input-capture",
        ).to_dict()
        for name, raw in captured
    ]

    return {
        "kind": "owner_loss",
        "passed": intended
        and supervisor["status"] in ("cancelled", "owner_lost")
        and result.status == "host_failure"
        and result.stop_verified
        and result.elapsed_seconds is None
        and result.resolved_model is None
        and not result.usage,
        "intended_phase_exercised": intended,
        "phase": PHASE,
        "host_status": result.status,
        "stop_verified": result.stop_verified,
        "elapsed_seconds": result.elapsed_seconds,
        "resolved_model": result.resolved_model,
        "usage": dict(result.usage),
        "request_may_have_been_sent": False,
        "credential_preflight": "not_started",
        "remote_computation_stopped": "unknown",
        "ownership": {"verified": True, "evidence": proof.to_dict()},
        "captures": captures + supervisor_captures,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    child(parser.parse_args().job)
