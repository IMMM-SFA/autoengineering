"""Bounded local Docker qualification. Never downloads an image automatically.

Only trusted, fixed probes execute. This command does not admit candidate code,
call a provider, or run a scientific development campaign.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

from autoengineering.agents.containers import (
    DockerBoundary,
    discover_runtime,
    boundary_source_identity,
)
from autoengineering.agents.sandbox import BoundaryLimits
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write


CASES = {
    "startup": 'import json,sys,os; print(json.dumps({"python":list(sys.version_info[:2]),"uid":os.getuid(),"pid":os.getpid()}))',
    "network": """import socket,errno,json
try:
 s=socket.socket();s.settimeout(1);s.connect(('198.51.100.1',9));blocked=False
except OSError as error:
 blocked=error.errno in (errno.ENETUNREACH,errno.EACCES,errno.EPERM)
print(json.dumps({'blocked':blocked}))
""",
    "memory": 'x=bytearray(512*1024*1024); print("allocation_allowed")',
    "cpu": "while True: pass",
    "output": 'import os\nwhile True: os.write(1,b"x"*65536)',
    "sleep": "import time; time.sleep(60)",
    "pids": """import os,time,signal,json
children=[];blocked=False
try:
 for _ in range(20):
  try: pid=os.fork()
  except OSError: blocked=True;break
  if pid==0:
   time.sleep(20);os._exit(0)
  children.append(pid)
finally:
 for pid in children:
  try: os.kill(pid,signal.SIGKILL)
  except ProcessLookupError: pass
  os.waitpid(pid,0)
print(json.dumps({'blocked':blocked,'children':len(children)}))
""",
}


def qualify(output: Path, image: str = "python:3.12-slim"):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("qualification requires a fresh output directory")
    checked_directory(output.parent)
    output.mkdir(mode=0o700)
    limits = BoundaryLimits(cpu_seconds=1, memory_bytes=128 * 1024 * 1024, output_bytes=4096)
    manifest = {
        "schema_version": "1.0",
        "purpose": "generated-boundary-qualification",
        "requested_image": image,
        "max_probe_executions": 9,
        "max_elapsed_seconds": 90,
        "limits": asdict(limits),
        "boundary_source_identity": boundary_source_identity(),
        "qualification_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "platform": platform.platform(),
        "provider_calls": 0,
        "scientific_campaigns": 0,
    }
    durable_write(output / "manifest.json", canonical_json(manifest).encode())
    try:
        runtime = discover_runtime(image)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        receipt = {
            **manifest,
            "status": "unavailable",
            "reason": str(error),
            "checks": [],
            "image_download_attempted": False,
        }
        durable_write(output / "qualification.json", canonical_json(receipt).encode())
        return receipt
    boundary = DockerBoundary(runtime)
    durable_write(output / "runtime.json", canonical_json(asdict(runtime)).encode())
    canary = output / "private-labels"
    canary.write_bytes(b"evaluator-owned-canary")
    privacy = f"""import json,os
results={{}}
for name,path,mode in [('label_read',{str(canary)!r},'rb'),('evaluator_write',{str(output / "checkpoint")!r},'wb'),
 ('workspace_write','/work/changed','wb'),('root_write','/tmp/changed','wb'),('shared_memory_write','/dev/shm/changed','wb')]:
 try:
  with open(path,mode) as stream:
   stream.read() if 'r' in mode else stream.write(b'changed')
  results[name]=False
 except OSError: results[name]=True
results['credentials_absent']=not any(key in os.environ for key in ('OPENAI_API_KEY','CODEX_API_KEY','CODEX_HOME'))
print(json.dumps(results))
"""
    cases = {
        "startup": CASES["startup"],
        "privacy": privacy,
        **{k: v for k, v in CASES.items() if k != "startup"},
    }
    began = time.monotonic()
    checks = []
    for name, source in cases.items():
        if time.monotonic() - began > manifest["max_elapsed_seconds"]:
            raise ValueError("qualification wall allowance exhausted")
        print(f"Qualifying {name}", flush=True)
        try:
            result = boundary.run_probe(
                {"probe.py": source.encode()},
                entrypoint="probe.py",
                payload=b"",
                root=output / name,
                limits=limits,
                wall_seconds=2 if name == "sleep" else 5,
            )
        except Exception as error:
            checks.append(
                {
                    "name": name,
                    "status": "fail",
                    "reason": str(error),
                    "probe_sha256": hashlib.sha256(source.encode()).hexdigest(),
                }
            )
            break
        parsed = None
        if name in ("startup", "privacy", "network", "pids") and result.status == "success":
            parsed = json.loads(result.stdout)
        if name == "startup":
            passed = result.stopped and parsed == {"python": [3, 12], "uid": 65534, "pid": 1}
        elif name == "privacy":
            passed = (
                result.stopped
                and isinstance(parsed, dict)
                and all(parsed.values())
                and canary.read_bytes() == b"evaluator-owned-canary"
                and not (output / "checkpoint").exists()
            )
        elif name == "network":
            passed = result.stopped and parsed == {"blocked": True}
        elif name == "memory":
            passed = result.stopped and result.oom_killed and result.status == "model_failure"
        elif name == "cpu":
            passed = result.stopped and result.status == "model_failure" and not result.oom_killed
        elif name == "output":
            passed = (
                result.stopped
                and result.status == "output_limit"
                and len(result.stdout) + len(result.stderr) <= limits.output_bytes
            )
        elif name == "sleep":
            passed = result.stopped and result.status == "timeout"
        else:
            passed = (
                result.stopped
                and isinstance(parsed, dict)
                and parsed["blocked"]
                and parsed["children"] <= 7
            )
        checks.append(
            {
                "name": name,
                "status": "pass" if passed else "fail",
                "probe_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "execution_receipt": result.receipt_digest,
                "observed_status": result.status,
                "stopped": result.stopped,
                "oom_killed": result.oom_killed,
            }
        )
        if not passed:
            break
    if len(checks) == 8 and all(c["status"] == "pass" for c in checks):
        checks.append(parent_death_probe(boundary, output))
    elapsed = time.monotonic() - began
    passed = all(c["status"] == "pass" for c in checks) and len(checks) == 9 and elapsed <= 90
    receipt = {
        **manifest,
        "runtime": asdict(runtime),
        "status": "qualified" if passed else "failed",
        "checks": checks,
        "remaining_gate": None if passed else "failed_or_missing_probe",
        "elapsed_seconds": elapsed,
        "image_download_attempted": False,
    }
    durable_write(output / "qualification.json", canonical_json(receipt).encode())
    return receipt


def parent_death_probe(boundary, output):
    source = """
from pathlib import Path
import json,sys
from autoengineering.agents.containers import ContainerRuntime,DockerBoundary
from autoengineering.agents.sandbox import BoundaryLimits
root=Path(sys.argv[1])
runtime=ContainerRuntime(**json.loads((root/'runtime.json').read_text()))
DockerBoundary(runtime).run_probe({'probe.py':b'import time; time.sleep(60)'},
 entrypoint='probe.py',payload=b'',root=root/'parent-death',
 limits=BoundaryLimits(cpu_seconds=1,memory_bytes=128*1024*1024,output_bytes=4096),wall_seconds=3)
"""
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
    import autoengineering

    environment["PYTHONPATH"] = str(Path(autoengineering.__file__).parent.parent)
    process = subprocess.Popen(
        [sys.executable, "-c", source, str(output)],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    root = output / "parent-death"
    cid = None
    running = False
    try:
        deadline = time.monotonic() + 8
        while process.poll() is None and time.monotonic() < deadline:
            if (root / "container-id").exists() and (root / "watchdog-ready.json").exists():
                cid = (root / "container-id").read_text()
                running = boundary._inspect(root, cid)["State"]["Running"]
                if running:
                    break
            time.sleep(0.02)
        if not running:
            return {
                "name": "parent_death",
                "status": "fail",
                "reason": "container_not_running_before_interrupt",
                "probe_sha256": hashlib.sha256(source.encode()).hexdigest(),
            }
        process.kill()
        process.wait(timeout=2)
        receipt = root / "watchdog-result.json"
        deadline = time.monotonic() + 8
        while not receipt.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        value = json.loads(receipt.read_text()) if receipt.exists() else {}
        current = boundary._inspect(root, cid)
        passed = (
            value.get("container_id") == cid
            and value.get("stopped") is True
            and value.get("reason") == "timeout"
            and not current["State"]["Running"]
        )
        if not current["State"]["Running"]:
            boundary._metadata(root, "rm", cid)
        return {
            "name": "parent_death",
            "status": "pass" if passed else "fail",
            "stopped": not current["State"]["Running"],
            "probe_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "execution_receipt": hashlib.sha256(receipt.read_bytes()).hexdigest()
            if receipt.exists()
            else None,
        }
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="python:3.12-slim")
    args = parser.parse_args()
    receipt = qualify(args.output, args.image)
    print(canonical_json(receipt))
    if receipt["status"] != "qualified":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
