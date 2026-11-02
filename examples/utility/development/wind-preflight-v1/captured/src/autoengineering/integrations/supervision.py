"""Local resource supervision for trusted scientific example commands.

RSS is sampled, not an instantaneous kernel memory quota. Descendant identities
include process creation time. Detached work that escapes discovery between
samples is outside this boundary; the admitted examples do not detach work.
No failed or interrupted run is converted into a scientific result.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write


def process_rss(process):
    """Observe a live identity, including protected macOS helper executables."""
    import psutil

    try:
        return process.memory_info().rss
    except psutil.AccessDenied:
        # Some signed utilities deny task-info access. Never treat a live but
        # unreadable process as zero RSS. The POSIX ps path is identity-checked
        # on both sides so PID reuse cannot substitute an unrelated process.
        if not process.is_running():
            return 0
        result = subprocess.run(["ps", "-p", str(process.pid), "-o", "rss="],
                                capture_output=True, text=True, timeout=.5)
        if not process.is_running():
            return 0
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip()) * 1024
        if process.status() == psutil.STATUS_ZOMBIE:
            return 0
        raise


def supervise(command, root, cwd, *, timeout_seconds, max_rss_bytes, poll_seconds=.02,
              environment=None):
    import psutil

    if not command or any(type(item) is not str or not item for item in command):
        raise ValueError("trusted command requires a nonempty argument vector")
    if type(max_rss_bytes) is not int or max_rss_bytes < 1:
        raise ValueError("memory ceiling must be a positive integer")
    if any(type(value) not in (float, int) or not math.isfinite(value) or value <= 0
           for value in (timeout_seconds, poll_seconds)):
        raise ValueError("time limits must be positive finite numbers")
    root = checked_directory(root)
    durable_write(root / "launch-intent.json", canonical_json({
        "command_sha256": hashlib.sha256(canonical_json(list(command)).encode()).hexdigest(),
        "timeout_seconds": timeout_seconds, "max_rss_bytes": max_rss_bytes,
        "poll_seconds": poll_seconds, "psutil_version": psutil.__version__,
        "supervisor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": sys.version, "platform": platform.platform(),
    }).encode())
    known = {}
    peak, samples = 0, 0
    reason = None
    monitor_error = None
    phase = "launch"
    started = time.monotonic()
    process = None

    def alive(p):
        try:
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    def discover():
        for parent in tuple(known.values()):
            if alive(parent):
                try:
                    for child in parent.children(recursive=True):
                        known.setdefault((child.pid, child.create_time()), child)
                except psutil.NoSuchProcess:
                    pass

    def stop_known():
        # Freeze known roots first so they cannot keep spawning during stop.
        for _ in range(3):
            discover()
            for p in tuple(known.values()):
                if alive(p):
                    try:
                        p.suspend()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        for p in reversed(tuple(known.values())):
            if alive(p):
                try:
                    p.kill()  # Process checks creation identity before signalling.
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        psutil.wait_procs([p for p in known.values() if process is None or p.pid != process.pid],
                          timeout=2)
        return not any(alive(p) for p in known.values())

    try:
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            process = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr,
                                       start_new_session=True, env=environment)
        try:
            parent = psutil.Process(process.pid)
            known[(parent.pid, parent.create_time())] = parent
        except psutil.NoSuchProcess:
            pass
        while process.poll() is None:
            phase = "discover"
            discover()
            phase = "sample_rss"
            rss = 0
            for p in tuple(known.values()):
                try:
                    if alive(p):
                        rss += process_rss(p)
                except psutil.NoSuchProcess:
                    pass
            peak = max(peak, rss)
            samples += 1
            if rss > max_rss_bytes:
                reason = "memory_ceiling"
                break
            if time.monotonic() - started >= timeout_seconds:
                reason = "deadline"
                break
            time.sleep(poll_seconds)
        discover()
        if reason is None and any(alive(p) for p in known.values() if p.pid != process.pid):
            reason = "orphaned_work_after_exit"
    except Exception as error:
        reason = "monitor_failure"
        monitor_error = {"type": type(error).__name__, "phase": phase}
    finally:
        try:
            stopped = stop_known() if known else True
        except psutil.Error:
            stopped = False
            reason = reason or "monitor_failure"
        if process is not None:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                stopped = False
        try:
            # Recheck after reaping the owned root. A kill request by itself
            # is not proof that the process has disappeared.
            stopped = not any(alive(p) for p in known.values())
        except psutil.Error:
            stopped = False
        result = {"schema_version": 1, "status": reason or (
            "success" if process is not None and process.returncode == 0 else "process_failure"),
            "exit_code": None if process is None else process.returncode,
            "stopped": stopped, "elapsed_seconds": time.monotonic() - started,
            "peak_sampled_tree_rss_bytes": peak, "samples": samples,
            "observed_processes": len(known), "psutil_version": psutil.__version__,
            "observed_identities": [
                {"pid": pid, "create_time": created} for pid, created in sorted(known)
            ],
            "monitor_error": monitor_error,
            "memory_enforcement": "sampled_RSS_not_instantaneous_quota",
            "recovery": "reconcile_scientific_ledger_before_any_restart"}
        durable_write(root / "supervision.json", canonical_json(result).encode())
    return result


def run_example(name, root, cache=None):
    module = f"examples.interoperability.{name}.run"
    if name == "solar":
        module = "examples.interoperability.solar.supervised_run"
    location = importlib.util.find_spec(module)
    if location is None or location.origin is None:
        raise ValueError("example module is not installed")
    protocol = json.loads(Path(location.origin).with_name("protocol.json").read_text())
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    durable_write(root / "example.json", canonical_json({
        "example": name, "module": module,
        "source_sha256": hashlib.sha256(Path(location.origin).read_bytes()).hexdigest(),
        "protocol": protocol,
    }).encode())
    work = root / "working-directory"
    work.mkdir(mode=0o700)
    command = [sys.executable, "-m", module, "--output", str(root / "result")]
    if name == "solar":
        if cache is None:
            raise ValueError("solar supervision requires an existing cache")
        command += ["--cache", str(Path(cache).absolute())]
    environment_path = str(Path(__file__).resolve().parents[2])
    if Path(environment_path).name == "src":
        environment_path += os.pathsep + str(Path(environment_path).parent)
    # Workers must import the same installed/source package and bundled examples.
    environment = dict(os.environ, PYTHONPATH=environment_path)
    return supervise(tuple(command), root, work, environment=environment,
                     timeout_seconds=protocol["wall_seconds"], max_rss_bytes=protocol["memory_bytes"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", choices=("bmi", "circuit", "solar"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    result = run_example(args.example, args.output.absolute(), args.cache)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "success" or not result["stopped"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
