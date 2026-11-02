"""Verify relocated synthetic runtime evidence without contacting Docker.

The caller must supply a separately retained manifest digest. Hashes bind saved
bytes, not the truth of a daemon's assertions or private-scoring qualification.
Archived Python files are hashed as data and are never imported or executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from qualify_utility_local_runtime import IMAGE, MODES, Refused, verify_owned

LIMIT = 1048576


def require(condition, message):
    if not condition:
        raise Refused(message)


def read(root, relative):
    """Open only bounded regular files beneath an explicit archive directory."""
    parts = PurePosixPath(relative).parts
    require(
        bool(parts) and not relative.startswith("/") and all(p not in (".", "..") for p in parts),
        "unsafe archive member",
    )
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(leaf)
            require(
                stat.S_ISREG(info.st_mode) and info.st_size <= LIMIT, "unbounded archive member"
            )
            with os.fdopen(leaf, "rb", closefd=False) as stream:
                raw = stream.read(LIMIT + 1)
            require(len(raw) <= LIMIT, "unbounded archive member")
            return raw
        finally:
            os.close(leaf)
    finally:
        os.close(fd)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result

    def invalid(_):
        raise Refused("nonfinite JSON value")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def verify(root, manifest_sha256):
    require(bool(re.fullmatch(r"[0-9a-f]{64}", manifest_sha256)), "invalid manifest digest")
    manifest_raw = read(root, "execution-files.json")
    require(hashlib.sha256(manifest_raw).hexdigest() == manifest_sha256, "manifest digest differs")
    manifest = decode(manifest_raw)
    require(isinstance(manifest, dict) and 0 < len(manifest) <= 128, "invalid manifest size")
    files = {}
    for name, digest in manifest.items():
        require(isinstance(name, str) and isinstance(digest, str), "invalid manifest entry")
        raw = read(root, "executions/" + name)
        require(hashlib.sha256(raw).hexdigest() == digest, "archive member digest differs")
        files[name] = raw

    def raw(mode, name):
        return files[mode + "/" + name]

    def document(mode, name):
        return decode(raw(mode, name))

    controls = []
    identities = set()
    for mode in MODES:
        base = mode + "/"
        plan = document(mode, base + "plan.json")
        cid, nonce = plan["container_id"], plan["nonce"]
        require(bool(re.fullmatch(r"[0-9a-f]{64}", cid)), "invalid saved container ID")
        require((cid, nonce) not in identities, "reused control identity")
        identities.add((cid, nonce))
        require(plan["mode"] == mode, "control mode differs")
        sources = document(mode, "sources.json")
        require(
            plan["controller_sha256"]
            == sources["controller.py"]
            == hashlib.sha256(raw(mode, "controller.py")).hexdigest(),
            "executed controller binding differs",
        )
        for source in ("probe.py", "private_score_worker.py"):
            require(
                sources[source] == hashlib.sha256(raw(mode, base + "stage/" + source)).hexdigest(),
                "staged source binding differs",
            )
        scope = document(mode, base + "stage/scope.json")
        require(
            scope == {"schema": "utility-container-probe-scope-v1", "nonce": nonce},
            "stage nonce differs",
        )
        image = document(mode, "image.json")
        require(
            image["Id"] == IMAGE and image["Os"] == "linux" and image["Architecture"] == "arm64",
            "saved image differs",
        )
        before = document(mode, base + "before-start.json")
        final = document(mode, base + "final-inspect.json")
        cleanup_before = document(mode, base + "cleanup-before.json")
        for inspected in (before, final, cleanup_before):
            verify_owned(inspected, plan)
            require(inspected["RestartCount"] == 0, "container restarted")
        require(
            before["State"]["Status"] == "created" and before["State"]["Running"] is False,
            "original container already started",
        )
        require(final == cleanup_before, "cleanup snapshot differs from stopped result")
        state = final["State"]
        require(state["Running"] is False and state["Status"] == "exited", "unresolved stop")
        for name in ("start-intent.json", "watchdog-ready.json", "cleanup.json"):
            bound = document(mode, base + name)
            require(
                bound["container_id"] == cid and bound["nonce"] == nonce,
                "lifecycle receipt belongs to another control",
            )
        cleanup = document(mode, base + "cleanup.json")
        require(
            cleanup["removed"] is True and cleanup["reason"] == "owner_pipe_eof",
            "missing normal owner-EOF cleanup receipt",
        )
        result = document(mode, base + "result.json")
        require(
            result["container_id"] == cid
            and result["nonce"] == nonce
            and result["mode"] == mode
            and result["passed"] is True
            and result["exit_code"] == state["ExitCode"]
            and result["oom_killed"] is state["OOMKilled"],
            "result identity or status differs",
        )
        require(raw(mode, base + "stderr.bin") == b"", "unexpected worker stderr")
        if mode == "memory-overrun":
            require(
                state["ExitCode"] == 137
                and state["OOMKilled"] is True
                and result["result"] is None
                and raw(mode, base + "stdout.bin") == b"",
                "missing kernel OOM evidence",
            )
        else:
            observed = decode(raw(mode, base + "stdout.bin"))
            require(
                result["result"] == observed
                and observed["nonce"] == nonce
                and observed["mode"] == mode
                and observed["qualified"] is False
                and observed["status"] == "synthetic_control_observed"
                and state["ExitCode"] == 0
                and state["OOMKilled"] is False,
                "synthetic output differs",
            )
            require(
                observed["observed_context"]
                == {
                    "effective_capabilities": "none",
                    "effective_limits": {
                        "cpu.max": "100000 100000",
                        "memory.max": "67108864",
                        "memory.swap.max": "0",
                        "pids.max": "16",
                    },
                    "gid": 65534,
                    "network_interfaces": ["lo"],
                    "no_new_privileges": True,
                    "platform": "linux",
                    "root_read_only": True,
                    "temporary_filesystem_bytes": 4194304,
                    "uid": 65534,
                },
                "in-container isolation observations differ",
            )
            if mode == "memory-small":
                require(observed["allocation_bytes"] == 8388608, "positive allocation differs")
            if mode == "score":
                require(
                    observed["synthetic_rmse"] == 1.0 and observed["vector_length"] == 64,
                    "synthetic score differs",
                )
        summary = document(mode, "summary.json")
        require(
            summary["results"] == [result] and summary["private_scoring_qualified"] is False,
            "execution summary differs",
        )
        controls.append({"mode": mode, "container_id": cid, "saved_cleanup_receipt": True})
    return {
        "schema": "utility-local-runtime-offline-verification-v1",
        "manifest_sha256": manifest_sha256,
        "verified_files": len(files),
        "controls": controls,
        "private_scoring_qualified": False,
        "live_container_absence_checked": False,
        "scope": "saved local ARM64 synthetic evidence; no execution or live daemon query",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.manifest_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
