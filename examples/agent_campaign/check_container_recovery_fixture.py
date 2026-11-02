"""Two bounded authored probes for container recovery after owner exit.

No provider, generated worker, registration or scientific campaign is executed.
An existing caller-pinned qualification is required. No images are downloaded.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from autoengineering.agents.container_recovery import reconcile_container
from autoengineering.agents.containers import DockerBoundary
from autoengineering.agents.qualification import verify_qualification
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write

SUCCESS = b"print('saved-result')\n"
SLEEP = b"import time\ntime.sleep(30)\n"
CHILD = """
import sys
from pathlib import Path
from autoengineering.agents.containers import DockerBoundary
from autoengineering.agents.qualification import verify_qualification
from autoengineering.campaign.serialization import unique_json
job = unique_json(Path(sys.argv[1]).read_text())
qualification = verify_qualification(Path(job['qualification_root']), expected_digest=job['qualification_digest'])
DockerBoundary(qualification.runtime).run_qualified(
    {'probe.py': job['source'].encode()},
    qualification_root=Path(job['qualification_root']),
    qualification_digest=job['qualification_digest'],
    entrypoint='probe.py', payload=b'', root=Path(job['execution']),
    limits=qualification.limits, wall_seconds=5,
)
"""


def exercise(output: Path, qualification_root: Path, qualification_digest: str):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("container recovery fixture requires a fresh output directory")
    qualification = verify_qualification(qualification_root, expected_digest=qualification_digest)
    output.mkdir(mode=0o700)
    durable_write(
        output / "manifest.json",
        canonical_json(
            {
                "schema_version": "1.0",
                "purpose": "authored-container-recovery-fixture",
                "maximum_container_starts": 2,
                "max_elapsed_seconds": 60,
                "provider_calls": 0,
                "scientific_campaigns": 0,
                "qualification_digest": qualification_digest,
                "fixture_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            }
        ).encode(),
    )
    began = time.monotonic()
    boundary = DockerBoundary(qualification.runtime)
    common = dict(
        qualification_root=qualification_root,
        qualification_digest=qualification_digest,
        entrypoint="probe.py",
        payload=b"",
        wall_seconds=5,
    )
    print("Recovering a completed authored probe", flush=True)
    completed = output / "completed"
    result = boundary.run_qualified(
        {"probe.py": SUCCESS},
        root=completed,
        limits=qualification.limits,
        **common,
    )
    if result.status != "success" or not result.stopped:
        raise ValueError("completed recovery fixture did not stop successfully")
    before = (completed / "result.json").read_bytes()
    saved = reconcile_container(completed, sources={"probe.py": SUCCESS}, **common)
    if (
        not saved.stopped
        or not saved.removed
        or saved.stdout != b"saved-result\n"
        or saved.result_status != "success"
        or (completed / "result.json").read_bytes() != before
    ):
        raise ValueError("completed recovery lost or changed the saved result")

    print("Stopping an authored probe after killing its outer owner", flush=True)
    interrupted = output / "interrupted"
    job = {
        "qualification_root": str(qualification_root.absolute()),
        "qualification_digest": qualification_digest,
        "execution": str(interrupted),
        "source": SLEEP.decode(),
    }
    durable_write(output / "child-job.json", canonical_json(job).encode())
    with (output / "child.log").open("xb") as log:
        child = subprocess.Popen(
            [sys.executable, "-c", CHILD, str(output / "child-job.json")],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 15
            running = False
            while child.poll() is None and time.monotonic() < deadline:
                if (interrupted / "watchdog-ready.json").exists():
                    cid = (interrupted / "container-id").read_text()
                    running = boundary._inspect(interrupted, cid)["State"]["Running"]
                    if running:
                        break
                time.sleep(0.02)
            if not running:
                raise ValueError("owned probe never reached its running state")
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
            observed = reconcile_container(interrupted, sources={"probe.py": SLEEP}, **common)
            if observed.stopped or observed.result_digest is not None:
                raise ValueError("outer death did not retain a distinct unresolved container")
            stopped = reconcile_container(
                interrupted,
                sources={"probe.py": SLEEP},
                stop=True,
                **common,
            )
            if (
                not stopped.stopped
                or not stopped.stop_requested
                or stopped.result_digest is not None
            ):
                raise ValueError("inner stop or missing-outcome distinction failed")
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            # Always attempt exact owned cleanup. Failure leaves the execution
            # evidence and watchdog intact and fails this fixture.
            if (interrupted / "effective-policy.json").exists():
                cleanup = reconcile_container(
                    interrupted,
                    sources={"probe.py": SLEEP},
                    stop=True,
                    **common,
                )
                if not cleanup.stopped:
                    raise ValueError("fixture container stop remains unresolved")
                if not cleanup.removed:
                    boundary._metadata(interrupted, "rm", cleanup.container_id)

    removed = reconcile_container(interrupted, sources={"probe.py": SLEEP}, **common)
    if not removed.stopped or not removed.removed:
        raise ValueError("fixture owned container removal was not verified")
    elapsed = time.monotonic() - began
    if elapsed > 60:
        raise ValueError("container recovery fixture exceeded its elapsed allowance")
    records = {}
    for name, receipt in (
        ("saved", saved),
        ("outer_exit", observed),
        ("stopped", stopped),
        ("removed", removed),
    ):
        record = asdict(receipt)
        raw = record.pop("stdout")
        record["stdout_sha256"] = hashlib.sha256(raw).hexdigest() if raw is not None else None
        records[name] = record
    final = {
        "status": "passed",
        "container_starts": 2,
        "elapsed_seconds": elapsed,
        "records": records,
    }
    durable_write(output / "result.json", canonical_json(final).encode())
    print(f"Container recovery fixture passed in {elapsed:.2f} seconds", flush=True)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    args = parser.parse_args()
    exercise(args.output, args.qualification_root, args.qualification_digest)


if __name__ == "__main__":
    main()
