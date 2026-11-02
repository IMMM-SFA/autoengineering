"""Fixed Linux coupled-load stdin entrypoint for a separately pinned image.

The owner must supply the expected packet hash in the immutable container command
and enforce lifecycle ownership. This entrypoint authorizes no sealed-source read
and supplies no host owner-loss recovery or execution/cost registration.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys

SOURCE = Path("/opt/coupled-source")
SITE = "/opt/inference/lib/python3.12/site-packages"
FILES = (
    "examples/utility/__init__.py",
    "examples/utility/engineering.py",
    "examples/utility/engineering_load.py",
    "examples/utility/engineering_load_scoring.py",
    "examples/utility/engineering_load_worker.py",
    "examples/utility/guest_resource_probe.py",
    "examples/interoperability/circuit/model.py",
    "examples/interoperability/circuit/fixture.py",
    "pixi.lock",
)
ACTIVE_SECONDS = 45
PACKET_BYTES = 32768


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate entrypoint field")
        result[key] = value
    return result


def read_regular(path, limit):
    """Bound metadata reads and refuse symlink components or special files."""
    path = Path(path)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("entrypoint path differs")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise ValueError("entrypoint file type or size differs")
        raw = os.read(descriptor, limit + 1)
        if len(raw) != info.st_size:
            raise ValueError("entrypoint file bytes differ")
        return raw
    finally:
        os.close(descriptor)


def verify_sources(root, manifest_raw, entrypoint_raw):
    """Verify a fixed source catalogue without importing any model code."""
    if type(manifest_raw) is not bytes or len(manifest_raw) > 16384:
        raise ValueError("entrypoint manifest size differs")
    manifest = json.loads(manifest_raw, object_pairs_hook=_unique)
    if (
        type(manifest) is not dict
        or set(manifest) != {"schema", "entrypoint_sha256", "files"}
        or manifest["schema"] != "utility-coupled-entrypoint-source-v1"
        or manifest["entrypoint_sha256"] != hashlib.sha256(entrypoint_raw).hexdigest()
        or type(manifest["files"]) is not dict
        or set(manifest["files"]) != set(FILES)
    ):
        raise ValueError("entrypoint manifest differs")
    sources = {}
    for name in FILES:
        expected = manifest["files"][name]
        if type(expected) is not str or re.fullmatch("[0-9a-f]{64}", expected) is None:
            raise ValueError("entrypoint source identity differs")
        raw = read_regular(Path(root) / name, 1048576 if name == "pixi.lock" else 131072)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("entrypoint source bytes differ")
        sources[name] = raw
    return sources


def execute(expected_packet_sha256):
    """Fixed paths, fixed context check, one stdin packet, one scoring attempt."""
    if (
        type(expected_packet_sha256) is not str
        or re.fullmatch("[0-9a-f]{64}", expected_packet_sha256) is None
    ):
        raise ValueError("entrypoint packet identity differs")
    sources = verify_sources(
        SOURCE,
        read_regular("/opt/coupled-worker/manifest.json", 16384),
        read_regular("/opt/coupled-worker/entrypoint.py", 131072),
    )
    context = {"__name__": "fixed_coupled_context"}
    exec(
        compile(
            sources["examples/utility/guest_resource_probe.py"], "fixed-coupled-context", "exec"
        ),
        context,
    )
    observed = context["context"]()
    # Observe the isolated no-site interpreter before enabling only this image's
    # fixed source/dependency locations. No caller path or .pth file is used.
    sys.path[:0] = [str(SOURCE), SITE]
    packet = sys.stdin.buffer.read(PACKET_BYTES + 1)
    if not 0 < len(packet) <= PACKET_BYTES:
        raise ValueError("entrypoint packet size differs")
    worker = {
        "__name__": "fixed_coupled_worker",
        "__file__": str(SOURCE / "examples/utility/engineering_load_worker.py"),
    }
    exec(
        compile(
            sources["examples/utility/engineering_load_worker.py"], "fixed-coupled-worker", "exec"
        ),
        worker,
    )
    # Validate before creating the private scoring scope.
    worker["parse_packet"](packet, expected_sha256=expected_packet_sha256)
    private_work = Path("/work/private-results")
    private_work.mkdir(mode=0o700)
    result = worker["capture"](
        packet,
        expected_sha256=expected_packet_sha256,
        source_root=SOURCE,
        private_work=private_work,
    )
    return {
        "schema": "utility-coupled-container-result-v1",
        "observed": observed,
        "worker": result,
        "private_boundary_qualified": False,
        "owner_loss_qualified": False,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
    signal.alarm(ACTIVE_SECONDS)
    try:
        if len(argv) != 1:
            raise ValueError("entrypoint arguments differ")
        result = execute(argv[0])
        print(
            json.dumps(result, sort_keys=True, allow_nan=False, separators=(",", ":")), flush=True
        )
        return 0 if result["worker"]["result"] is not None else 70
    except Exception:
        print('{"status":"refused","private_boundary_qualified":false}', flush=True)
        return 70
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
