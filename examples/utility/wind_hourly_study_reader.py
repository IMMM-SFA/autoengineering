"""Verify saved hourly-development process receipts without observing live PIDs.

Operational process recovery also checks current process membership. This reader
checks archived stop receipts only and cannot assert current machine state.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from autoengineering.agents.process import ProcessResult
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.execution import ProcessIdentity
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import unique_json


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 1024**2:
        raise ValueError("saved process receipt exceeds cap")
    return unique_json(path.read_text())


def read_stopped_process(directory, source, refs, maximum_output_bytes):
    directory, source = Path(directory), Path(source)
    done = _json(directory, "completion.json")
    launch = _json(directory, "process.json")
    intent = _json(directory, "intent.json")
    job = _json(directory, "job.json")
    watchdog = _json(directory, "watchdog-job.json")
    ready = _json(directory, "watchdog-ready.json")
    stopped = _json(directory, "watchdog-result.json")
    if (
        done.get("schema_version") != "1.0"
        or done.get("status") != "completed"
        or type(done.get("returncode")) is not int
        or done.get("returncode") != 0
        or done.get("stopped") is not True
        or done.get("truncated") is not False
        or done.get("identity") != launch
        or intent != {"nonce": launch.get("nonce")}
        or watchdog.get("target") != launch
        or watchdog.get("owner_lease") != "pipe-eof-v1"
        or job.get("owner_lease") != "pipe-eof-v1"
        or job.get("keep_group_leader") is not True
        or stopped.get("stopped") is not True
        or stopped.get("reason") != "group_stopped"
        or type(launch.get("pid")) is not int
        or launch["pid"] <= 0
        or launch.get("pgid") != launch["pid"]
        or type(ready.get("pid")) is not int
        or ready["pid"] <= 0
    ):
        raise ValueError("saved hourly process or stop receipts disagree")
    watchdog_sha = hashlib.sha256(
        confined_file(directory, "watchdog-job.json").read_bytes()
    ).hexdigest()
    for receipt in (ready, stopped):
        if receipt.get("job_sha256") != watchdog_sha or receipt.get("nonce") != watchdog.get(
            "nonce"
        ):
            raise ValueError("saved watchdog receipt identity differs")
    declared = {r.path: r for r in refs}
    for name in ("watchdog", "worker"):
        ref = declared.get("src/autoengineering/agents/process_" + name + ".py")
        if ref is None or hashlib.sha256(read_bytes(source, ref)).hexdigest() != watchdog.get(
            name + "_sha256"
        ):
            raise ValueError("saved watchdog source closure differs")
    for name, filename in (("job", "job.json"), ("stdin", "stdin.bin")):
        path = confined_file(directory, filename)
        if path.stat().st_size > 1024**2 or hashlib.sha256(
            path.read_bytes()
        ).hexdigest() != done.get(name + "_sha256"):
            raise ValueError("saved process input digest differs")
    captures = {}
    for name in ("stdout", "stderr"):
        ref = ArtifactRef(
            name + ".bin",
            done.get(name + "_sha256"),
            done.get(name + "_bytes"),
            "application/octet-stream",
            "saved-process",
            {},
        )
        captures[name] = read_bytes(directory, ref, max_bytes=maximum_output_bytes)
    elapsed = done.get("elapsed_seconds")
    if (
        type(elapsed) not in (int, float)
        or not math.isfinite(elapsed)
        or elapsed < 0
        or sum(map(len, captures.values())) > maximum_output_bytes
    ):
        raise ValueError("saved process elapsed time or output cap differs")
    return ProcessResult(
        "completed",
        ProcessIdentity(**launch),
        0,
        captures["stdout"],
        captures["stderr"],
        elapsed,
        True,
        False,
    )
