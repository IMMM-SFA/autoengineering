"""Kill an owned synthetic-peer supervisor and verify its native watchdog stop.

No provider exists in this probe. Losing the original completion leaves the native
outcome unknown. Recovery must refuse without relaunching or inventing a handoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

from autoengineering.agents.hosts.claude import recover_claude_transport
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import recover_watchdog_stop
from autoengineering.campaign.execution import ProcessIdentity, identity_matches
from autoengineering.campaign.serialization import unique_json


def probe(root):
    root = root.absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    child = root / "owned-supervisor"
    command = (
        sys.executable, str(Path(__file__).with_name("probe_claude_loopback.py")),
        "--output", str(child), "--case", "timeout",
    )
    killed = False
    with (root / "parent.stdout").open("wb") as stdout, (root / "parent.stderr").open("wb") as stderr:
        parent = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        try:
            deadline = time.monotonic() + 6
            observation = child / "request-1-observation.json"
            while time.monotonic() < deadline:
                if parent.poll() is not None:
                    raise ValueError("owned supervisor exited before owner-loss point")
                try:
                    observed = unique_json(observation.read_text())
                    if observed.get("synthetic_auth_matched") is True:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(0.01)
            else:
                raise ValueError("no authenticated synthetic request before owner loss")
            process = unique_json((child / "native/process.json").read_text())
            if not identity_matches(ProcessIdentity(**process)):
                raise ValueError("native process is not active at owner-loss point")
            job_sha256 = hashlib.sha256((child / "native/job.json").read_bytes()).hexdigest()
            before = sorted(str(p.relative_to(root)) for p in root.rglob("job.json"))
            parent.kill()  # The direct child handle, never a recovered numeric PID.
            killed = True
            parent.wait(timeout=3)
            if parent.returncode != -signal.SIGKILL:
                raise ValueError("owned supervisor did not receive the intended fault")
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=3)
    deadline = time.monotonic() + 6
    while not (child / "native/watchdog-result.json").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    stopped = recover_watchdog_stop(child / "native")
    if stopped.get("stopped") is not True or (child / "native/completion.json").exists():
        raise ValueError("owner-loss stop or missing-completion condition failed")
    refused = False
    try:
        recover_claude_transport(
            child / "native", nonce="claude-controlled-peer", job_sha256=job_sha256,
            model="claude-sonnet-4-6", max_output_bytes=65536,
        )
    except ValueError:
        refused = True
    after = sorted(str(p.relative_to(root)) for p in root.rglob("job.json"))
    if not refused or before != after:
        raise ValueError("missing completion was accepted or recovery added a job")
    result = {
        "version": "claude-owner-loss-probe-1.0", "source_identity": host_source_identity(),
        "status": "passed_limited_scope", "parent_killed": killed,
        "parent_returncode": parent.returncode, "native_identity_before_fault": process,
        "authenticated_peer_request_before_fault": observed,
        "watchdog_stop": stopped, "completion_missing": True,
        "native_outcome": "unknown_owner_loss", "handoff": None,
        "original_job_sha256": job_sha256, "recovery_refused": refused,
        "extra_native_jobs": len(after) - len(before),
        "provider_calls": 0, "scientific_calls": 0, "production_admission": False,
        "scope": "owned supervisor death after synthetic request; no provider, model or real key",
    }
    (root / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


def probe_saved_completion(root):
    root = root.absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    child = root / "owned-supervisor"
    command = (
        sys.executable, str(Path(__file__).with_name("probe_claude_loopback.py")),
        "--output", str(child), "--case", "completion_loss",
    )
    with (root / "parent.stdout").open("wb") as stdout, (root / "parent.stderr").open("wb") as stderr:
        parent = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=15, check=False)
    if parent.returncode != 77 or (child / "report.json").exists():
        raise ValueError("saved-completion caller fault was not exercised")
    binding = unique_json((child / "caller-binding.json").read_text())
    if binding.get("nonce") != "claude-controlled-peer" or binding.get("model") != "claude-sonnet-4-6":
        raise ValueError("prelaunch caller binding differs from intended invocation")
    before = sorted(str(p.relative_to(root)) for p in root.rglob("job.json"))
    recovered = recover_claude_transport(
        child / "native", nonce=binding["nonce"], job_sha256=binding["job_sha256"],
        model=binding["model"], max_output_bytes=65536,
    )
    after = sorted(str(p.relative_to(root)) for p in root.rglob("job.json"))
    if (
        before != after or recovered.process.status != "completed" or not recovered.process.stopped
        or recovered.error is not None or recovered.parsed is None
        or unique_json(recovered.parsed.text) != {"handoff_json": "synthetic controlled peer"}
    ):
        raise ValueError("saved original completion could not be recovered without a new job")
    observation = unique_json((child / "request-1-observation.json").read_text())
    if observation.get("synthetic_auth_matched") is not True:
        raise ValueError("synthetic native helper was not exercised")
    result = {
        "version": "claude-saved-completion-loss-probe-1.0",
        "source_identity": host_source_identity(), "status": "passed_limited_scope",
        "parent_returncode": parent.returncode, "prelaunch_binding": binding,
        "caller_result_missing": True, "original_completion_present": True,
        "native_outcome": "completed_saved", "handoff": recovered.parsed.text,
        "stop_verified": True, "extra_native_jobs": len(after) - len(before),
        "original_peer_requests": len(list(child.glob("request-*-observation.json"))),
        "provider_calls": 0, "scientific_calls": 0, "production_admission": False,
        "scope": "caller exit after native durable completion; authored local peer only",
    }
    (root / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--window", choices=("active", "saved_completion"), default="active")
    args = parser.parse_args()
    (probe if args.window == "active" else probe_saved_completion)(args.output)
