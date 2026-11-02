"""Archive and inspect synthetic Claude boundary evidence without executing it.

The caller must supply the independently retained index digest. Original absolute
paths remain provenance only. A successful inspection grants no host admission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import unique_json

VERSION = "claude-policy-archive-1.0"
MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 256
FIELDS = (
    "allowed_read", "private_read_denied", "credential_read", "outside_write_denied",
    "home_write", "workspace_write_denied", "symlink_read_denied", "symlink_write_denied",
    "hardlink_read_denied", "endpoint_allowed", "other_tcp_denied", "unix_denied",
    "exec_denied", "checkout_read_denied",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive(source: Path, destination: Path) -> str:
    """Copy regular bytes only. Record links/special nodes without following them."""
    source = source.absolute()
    if source.is_symlink() or not source.is_dir():
        raise ValueError("archive source must be a directory")
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError("archive destination cannot be within source")
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    files, excluded = {}, {}
    total = 0
    for directory, dirs, names in os.walk(source, followlinks=False):
        parent = Path(directory)
        for name in sorted([*dirs, *names]):
            path = parent / name
            relative = path.relative_to(source).as_posix()
            metadata = path.lstat()
            target = destination / relative
            if stat.S_ISLNK(metadata.st_mode):
                excluded[relative] = {"type": "symlink", "target": os.readlink(path)}
                if name in dirs:
                    dirs.remove(name)
            elif stat.S_ISDIR(metadata.st_mode):
                target.mkdir(mode=0o700)
            elif stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
                if total > MAX_BYTES or len(files) >= MAX_FILES:
                    raise ValueError("archive exceeds bounds")
                data = confined_file(source, relative).read_bytes()
                if len(data) != metadata.st_size:
                    raise ValueError("archive source changed while copying")
                target.write_bytes(data)
                target.chmod(0o600)
                files[relative] = reference(
                    destination, relative, media_type="application/octet-stream",
                    producer="synthetic-claude-policy-probe",
                ).to_dict()
            else:
                excluded[relative] = {"type": "special", "mode": stat.S_IFMT(metadata.st_mode)}
    index = {
        "version": VERSION, "original_root": str(source), "files": files,
        "excluded_nodes": excluded, "total_bytes": total,
        "production_admission": False,
    }
    data = (json.dumps(index, indent=2, sort_keys=True) + "\n").encode()
    (destination / "archive.json").write_bytes(data)
    return digest(data)


def inspect(root: Path, index_sha256: str) -> dict:
    """Check pinned saved evidence. Never query original paths or live processes."""
    path = confined_file(root, "archive.json")
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("archive index exceeds bound")
    raw = path.read_bytes()
    if digest(raw) != index_sha256:
        raise ValueError("archive index digest mismatch")
    index = unique_json(raw.decode())
    if index.get("version") != VERSION or index.get("production_admission") is not False:
        raise ValueError("unsupported archive or admission claim")
    entries = index.get("files")
    if not isinstance(entries, dict) or not 1 <= len(entries) <= MAX_FILES:
        raise ValueError("archive file count exceeds bound")
    refs = {name: ArtifactRef.from_dict(value) for name, value in entries.items()}
    total = sum(ref.size_bytes for ref in refs.values())
    if total > MAX_BYTES or total != index.get("total_bytes"):
        raise ValueError("archive size mismatch")
    if any(ref.path != name for name, ref in refs.items()):
        raise ValueError("archive reference name mismatch")
    data = {name: read_bytes(root, ref, max_bytes=MAX_BYTES) for name, ref in refs.items()}

    def obj(name):
        if name not in data:
            raise ValueError("missing archive evidence: " + name)
        value = unique_json(data[name].decode())
        if not isinstance(value, dict):
            raise ValueError("evidence must be an object")
        return value

    report = obj("report.json")
    if (
        report.get("version") != "claude-policy-probe-1.3"
        or report.get("status") != "passed_limited_scope"
        or report.get("production_admission") is not False
        or type(report.get("provider_calls")) is not int or report["provider_calls"] != 0
        or type(report.get("scientific_calls")) is not int or report["scientific_calls"] != 0
        or report.get("runtime", {}).get("platform") != "darwin"
        or not report.get("unqualified")
    ):
        raise ValueError("report is not the supported limited probe")
    if digest(data["code/probe.c"]) != report.get("raw_source_sha256"):
        raise ValueError("probe source mismatch")
    observed = {}
    control_command = obj("control/job.json").get("command")
    original = index["original_root"]
    if (
        not isinstance(control_command, list) or len(control_command) != 14
        or control_command[0] != original + "/code/probe"
        or obj("sandbox/job.json").get("command")
        != ["/usr/bin/sandbox-exec", "-f", original + "/canary.sb", *control_command]
    ):
        raise ValueError("syscall jobs do not bind the original sandbox policy")
    nonces = {
        "control": "claude-policy-control", "sandbox": "claude-policy-sandbox",
        "client-help": "claude-policy-help", "helper-proof": "claude-policy-helper",
    }
    for name, nonce in nonces.items():
        completion = obj(name + "/completion.json")
        identity = obj(name + "/process.json")
        job = obj(name + "/job.json")
        watchdog_job = obj(name + "/watchdog-job.json")
        watchdog_result = obj(name + "/watchdog-result.json")
        if (
            completion.get("schema_version") != "1.0"
            or completion.get("status") != "completed"
            or type(completion.get("returncode")) is not int or completion["returncode"] != 0
            or completion.get("stopped") is not True or completion.get("truncated") is not False
            or completion.get("identity") != identity or identity.get("nonce") != nonce
            or obj(name + "/intent.json") != {"nonce": nonce}
            or job.get("keep_group_leader") is not True or job.get("owner_lease") != "pipe-eof-v1"
            or watchdog_job.get("target") != identity
            or watchdog_result.get("nonce") != watchdog_job.get("nonce")
            or watchdog_result.get("job_sha256") != digest(data[name + "/watchdog-job.json"])
            or watchdog_result.get("stopped") is not True
            or watchdog_result.get("reason") != "group_stopped"
        ):
            raise ValueError("inconsistent stopped-process evidence: " + name)
        for field, suffix in (("job", ".json"), ("stdin", ".bin"), ("stdout", ".bin"), ("stderr", ".bin")):
            value = data[name + "/" + field + suffix]
            if completion.get(field + "_sha256") != digest(value):
                raise ValueError("process digest mismatch: " + name)
            if field in ("stdout", "stderr") and completion.get(field + "_bytes") != len(value):
                raise ValueError("process size mismatch: " + name)
        if data[name + "/stdin.bin"]:
            raise ValueError("probe unexpectedly supplied input")
        if name in ("control", "sandbox"):
            result = obj(name + "/stdout.bin")
            expected = {f: (0 if name == "control" and f.endswith("_denied") else 1) for f in FIELDS}
            if result != expected or any(type(v) is not int for v in result.values()):
                raise ValueError("syscall observations contradict the fixed control contract")
            observed[name] = result
        elif name == "client-help":
            command = job.get("command")
            if command != [
                "/usr/bin/sandbox-exec", "-f", original + "/client.sb",
                report["inventory"]["executable"], "--bare", "--tools=",
                "--setting-sources=", "--help",
            ] or b"Usage: claude" not in data[name + "/stdout.bin"]:
                raise ValueError("actual CLI help evidence differs from its contract")
            observed["actual_cli_help"] = {
                "status": "completed", "returncode": 0, "stopped": True, "help_returned": True,
            }
        else:
            if data[name + "/stdout.bin"] != b"synthetic authentication fixture\n":
                raise ValueError("helper synthetic output mismatch")
            observed["synthetic_helper_bootstrap"] = {
                "status": "completed", "returncode": 0, "stopped": True,
                "expected_synthetic_output": True, "native_CLI_helper_hook_exercised": False,
            }
    if observed != report.get("observed"):
        raise ValueError("report observations disagree with raw evidence")
    return {
        "status": "verified_saved_limited_scope", "index_sha256": index_sha256,
        "source_identity": report["source_identity"], "observed": observed,
        "production_admission": False, "live_process_state_checked": False,
        "provider_calls": 0, "scientific_calls": 0, "unqualified": report["unqualified"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    pack = sub.add_parser("archive")
    pack.add_argument("source", type=Path)
    pack.add_argument("destination", type=Path)
    check = sub.add_parser("inspect")
    check.add_argument("root", type=Path)
    check.add_argument("--index-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(
        {"index_sha256": archive(args.source, args.destination)} if args.action == "archive"
        else inspect(args.root, args.index_sha256), sort_keys=True,
    ))
