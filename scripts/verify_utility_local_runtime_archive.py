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

from qualify_utility_local_runtime import BASE_MODES, IMAGE, Refused, verify_owned

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


def load(root, manifest_sha256):
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
    return files


def verify(root, manifest_sha256, *, modes=BASE_MODES):
    files = load(root, manifest_sha256)

    def raw(mode, name):
        return files[mode + "/" + name]

    def document(mode, name):
        return decode(raw(mode, name))

    controls = []
    identities = set()
    for mode in modes:
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
            if mode == "isolation":
                public = raw(mode, "host-canary.json")
                expected = json.dumps({"public_synthetic_canary": nonce}, sort_keys=True).encode()
                digest = hashlib.sha256(public).hexdigest()
                require(
                    public == expected + b"\n"
                    and raw(mode, base + "stage/public-canary.json") == public,
                    "public canary content differs",
                )
                metadata = document(mode, base + "stage/isolation.json")
                require(
                    metadata["host_canary_sha256"] == digest
                    and metadata["host_canary_path"]
                    == str(Path(plan["stage"]).parent.parent / "host-canary.json"),
                    "host canary metadata differs",
                )
                positive = document(mode, base + "host-positive-control.json")
                require(
                    positive == {"nonce": nonce, "canary_sha256": digest, "read_succeeded": True},
                    "host positive control differs",
                )
                checks = {
                    "public_canary_sha256": digest,
                    "mounted_public_canary_read": True,
                    "unmounted_host_canary_read": False,
                    "parent_traversal_canary_read": False,
                    "root_and_stage_write": False,
                    "temporary_canary_read_write": True,
                    "loopback_positive_control": True,
                    "documentation_address_errno": 101,
                }
                require(
                    all(observed[k] == value for k, value in checks.items()),
                    "isolation positive/negative control differs",
                )
            if mode in ("output-small", "output-overrun", "bounded-score"):
                require(
                    sources["private_container_worker.py"]
                    == hashlib.sha256(
                        raw(mode, base + "stage/private_container_worker.py")
                    ).hexdigest(),
                    "bounded worker source differs",
                )
                captured = observed["output_capture"]
                require(
                    captured["schema"] == "private-container-output-v1"
                    and captured["output_limit_bytes"] == 16384
                    and captured["private_scoring_qualified"] is False,
                    "output boundary metadata differs",
                )
                if mode == "bounded-score":
                    require(
                        captured["mode"] == "score"
                        and captured["child_exit_code"] == 0
                        and captured["child_signal"] is None
                        and captured["output_limited"] is False
                        and 0 < captured["captured_bytes"] < 16384
                        and captured["score"]
                        == {
                            "status": "success",
                            "outcome": "rmse",
                            "units": "1",
                            "value": 1.0,
                            "feasible": True,
                        },
                        "bounded synthetic score differs",
                    )
                else:
                    expected = (
                        (4096, None, 0, False)
                        if mode == "output-small"
                        else (16384, 25, None, True)
                    )
                    require(
                        captured["mode"] == mode
                        and tuple(
                            captured[k]
                            for k in (
                                "captured_bytes",
                                "child_signal",
                                "child_exit_code",
                                "output_limited",
                            )
                        )
                        == expected,
                        "output enforcement control differs",
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


def verify_lifecycle(root, manifest_sha256):
    files = load(root, manifest_sha256)
    controls = []
    ids, nonces = set(), set()
    for fault, owner_exit in (
        ("deadline", 2),
        ("cancellation", -15),
        ("owner-loss", -9),
        ("lost-start-ack", 2),
    ):

        def raw(name):
            return files[fault + "/" + name]

        def document(name):
            return decode(raw(name))

        plan = document("hold/plan.json")
        cid, nonce = plan["container_id"], plan["nonce"]
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", cid))
            and cid not in ids
            and nonce not in nonces
            and plan["mode"] == "hold",
            "invalid lifecycle identity",
        )
        ids.add(cid)
        nonces.add(nonce)
        sources = document("sources.json")
        require(
            plan["controller_sha256"]
            == sources["controller.py"]
            == hashlib.sha256(raw("controller.py")).hexdigest(),
            "controller binding differs",
        )
        for source in ("probe.py", "private_score_worker.py"):
            require(
                sources[source] == hashlib.sha256(raw("hold/stage/" + source)).hexdigest(),
                "staged source binding differs",
            )
        require(
            document("hold/stage/scope.json")
            == {"schema": "utility-container-probe-scope-v1", "nonce": nonce},
            "stage nonce differs",
        )
        before = document("hold/before-start.json")
        running = document("hold/fault-running-inspect.json")
        cleanup_before = document("hold/cleanup-before.json")
        for value in (before, running, cleanup_before):
            verify_owned(value, plan)
            require(value["RestartCount"] == 0, "container restarted")
        require(
            before["State"]["Status"] == "created" and before["State"]["Running"] is False,
            "original container already started",
        )
        require(
            running["State"]["Running"] is True and cleanup_before["State"]["Running"] is True,
            "fault did not remove the running original container",
        )
        intent = document("hold/fault-intent.json")
        ready = document("hold/watchdog-ready.json")
        receipt = document("hold/cleanup.json")
        reconciled = document("hold/fault-reconciled.json")
        for bound in (document("hold/start-intent.json"), intent, ready, receipt, reconciled):
            require(
                bound["container_id"] == cid and bound["nonce"] == nonce,
                "lifecycle receipt belongs to another control",
            )
        require(
            intent["fault"] == fault
            and intent["start_response_delivered_to_controller"] is (fault != "lost-start-ack"),
            "fault intent differs",
        )
        exited = document("owner-exit.json")
        require(
            exited["fault"] == fault
            and exited["owner_pid"] == intent["owner_pid"]
            and exited["returncode"] == owner_exit,
            "owner exit differs",
        )
        expected_reason = "deadline" if fault == "deadline" else "owner_pipe_eof"
        require(
            receipt["reason"] == expected_reason and receipt["removed"] is True,
            "independent cleanup reason differs",
        )
        require(
            reconciled["removed"] is True
            and reconciled["live_absence_confirmed"] is True
            and reconciled["private_scoring_qualified"] is False
            and reconciled["fault"] == fault
            and reconciled["start_retries"] == 0,
            "saved live reconciliation differs",
        )
        witness = document("hold/fault-witness.json")
        require(
            witness["nonce"] == nonce
            and witness["mode"] == "hold"
            and witness["status"] == "synthetic_hold_ready"
            and witness["qualified"] is False,
            "running witness differs",
        )
        controls.append({"fault": fault, "container_id": cid, "saved_cleanup_receipt": True})
    return {
        "schema": "utility-local-runtime-lifecycle-offline-verification-v1",
        "manifest_sha256": manifest_sha256,
        "verified_files": len(files),
        "controls": controls,
        "private_scoring_qualified": False,
        "live_container_absence_checked": False,
        "scope": "saved local ARM64 synthetic lifecycle evidence; no execution or live daemon query",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument(
        "--kind", choices=("basic", "lifecycle", "isolation", "output"), default="basic"
    )
    args = parser.parse_args()
    if args.kind == "output":
        result = verify(
            args.archive,
            args.manifest_sha256,
            modes=("output-small", "output-overrun", "bounded-score"),
        )
    elif args.kind == "isolation":
        result = verify(args.archive, args.manifest_sha256, modes=("isolation",))
    else:
        verifier = verify if args.kind == "basic" else verify_lifecycle
        result = verifier(args.archive, args.manifest_sha256)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
