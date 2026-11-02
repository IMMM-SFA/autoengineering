"""Probe one external macOS boundary without native CLI sandbox nesting.

Only synthetic files and local listeners are used. No model request, real
credential or production host qualification is involved.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import shutil
import socket
import sys
import threading
import time
import uuid

from autoengineering.agents.hosts.codex import inspect_codex
from autoengineering.agents.process import supervise_process
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.probe_command_profile import command_passed


def external_policy(workspace: Path, scratch: Path, executable: Path) -> str:
    """Restrict this prototype to staged files, fixed binaries and no networking.

    There is deliberately no grant for host home, checkout, general temporary
    directories, Mach services, Unix sockets or arbitrary executable paths.
    """
    programs = (
        executable,
        Path("/bin/cat"),
        Path("/bin/bash"),
        Path("/usr/bin/touch"),
        Path("/usr/bin/curl"),
    )
    trees = (Path("/usr/lib"), Path("/System/Library"), workspace, scratch)
    # macOS runtime startup requires an exact root-directory read. This grants
    # no descendant read authority; canary probes verify that distinction.
    literals = (
        *programs,
        Path("/"),
        Path("/dev/null"),
        Path("/dev/random"),
        Path("/dev/urandom"),
        Path("/private/etc/ssl/openssl.cnf"),
    )
    metadata = sorted({str(parent) for p in (*trees, *literals) for parent in p.parents})

    def quote(p):
        return json.dumps(str(p), ensure_ascii=True)

    return (
        "\n".join(
            (
                "(version 1)",
                "(deny default)",
                "(allow sysctl-read)",
                "(allow process-fork)",
                "(allow process-exec " + " ".join(f"(literal {quote(p)})" for p in programs) + ")",
                "(allow file-read* "
                + " ".join(f"(subpath {quote(p)})" for p in trees)
                + " "
                + " ".join(f"(literal {quote(p)})" for p in literals)
                + ")",
                "(allow file-read-metadata "
                + " ".join(f"(literal {quote(p)})" for p in metadata)
                + ")",
                f'(allow file-write* (subpath {quote(scratch)}) (literal "/dev/null"))',
            )
        )
        + "\n"
    )


class LocalListener:
    """A bounded synthetic HTTP listener, including a Unix socket positive control."""

    def __init__(self, path: Path | None = None):
        self.socket = socket.socket(socket.AF_UNIX if path else socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(str(path) if path else ("127.0.0.1", 0))
        self.socket.listen(4)
        self.socket.settimeout(0.1)
        self.port = None if path else self.socket.getsockname()[1]
        self.requests = 0
        self.errors = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with connection:
                self.requests += 1
                connection.settimeout(1)
                try:
                    connection.recv(8192)
                    connection.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n"
                    )
                except OSError as exc:
                    self.errors.append(type(exc).__name__)

    def close(self):
        self.stop.set()
        self.socket.close()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError("local listener did not stop")


def exercise(output: Path):
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise ValueError("external host probe requires macOS")
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("external host probe requires a fresh output directory")
    installed = shutil.which("codex")
    if installed is None:
        raise ValueError("installed Codex is unavailable")
    inventory = inspect_codex(Path(installed))
    output.mkdir(mode=0o700)
    for name in ("workspace", "private", "scratch", "receipts"):
        (output / name).mkdir(mode=0o700)
    workspace, private, scratch = (output / name for name in ("workspace", "private", "scratch"))
    public = f"public-{uuid.uuid4().hex}\n".encode()
    secret = f"synthetic-private-{uuid.uuid4().hex}\n".encode()
    durable_write(workspace / "brief.txt", public)
    for name in ("labels", "credential", "evaluator"):
        durable_write(private / f"{name}.txt", secret)
    (workspace / "linked-private.txt").symlink_to(private / "labels.txt")
    # Put the Unix socket inside an allowed tree so its denial tests network
    # authority rather than the inability to resolve a private file path.
    unix_path = scratch / "local.sock"
    if len(str(unix_path).encode()) >= 104:
        raise ValueError("output path is too long for the Unix socket probe")
    policy = external_policy(workspace, scratch, Path(inventory.executable))
    durable_write(output / "external.sb", policy.encode())
    # These fixed-command positive controls differ only in network authority.
    # This is never used to launch the CLI or any generated command.
    durable_write(output / "network-control.sb", (policy + "(allow network*)\n").encode())
    durable_write(output / "probe-source.py", Path(__file__).read_bytes())
    environment = {
        "HOME": str(scratch),
        "CODEX_HOME": str(scratch),
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "TMPDIR": str(scratch),
    }
    records = []
    began = time.monotonic()

    def run(name, command, *, control=False):
        print(f"Checking {name}", flush=True)
        profile = "network-control.sb" if control else "external.sb"
        args = ("/usr/bin/sandbox-exec", "-f", str(output / profile), *command)
        result = supervise_process(
            args,
            directory=output / "receipts" / name,
            cwd=workspace,
            environment=environment,
            nonce=uuid.uuid4().hex,
            stdin=b"",
            timeout_seconds=5,
            max_output_bytes=65536,
            on_launch=lambda owner: durable_write(
                output / "receipts" / f"{name}-owner.json", canonical_json(owner).encode()
            ),
        )
        if not result.stopped:
            raise RuntimeError(f"unresolved process ownership in {name}; no further launch")
        return result

    def record(name, result, passed):
        bounded = result.stopped and not result.truncated
        records.append(
            {
                "name": name,
                "passed": bool(passed and bounded),
                "returncode": result.returncode,
                "stopped": result.stopped,
                "truncated": result.truncated,
                "process_status": result.status,
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            }
        )

    tcp = LocalListener()
    unix = None
    try:
        unix = LocalListener(unix_path)
        for name, command, expected in (
            ("approved_brief", ("/bin/cat", str(workspace / "brief.txt")), public),
            (
                "installed_cli",
                (inventory.executable, "--version"),
                (inventory.version + "\n").encode(),
            ),
            (
                "child_approved_read",
                (
                    "/bin/bash",
                    "--noprofile",
                    "--norc",
                    "-c",
                    '/bin/cat "$1"; exit "$?"',
                    "probe",
                    str(workspace / "brief.txt"),
                ),
                public,
            ),
        ):
            result = run(name, command)
            record(name, result, result.returncode == 0 and result.stdout == expected)
            if not records[-1]["passed"]:
                break
        if len(records) == 3 and all(r["passed"] for r in records):
            for name, path in (
                ("private_labels", private / "labels.txt"),
                ("credential_canary", private / "credential.txt"),
                ("private_evaluator", private / "evaluator.txt"),
                ("checkout_source", Path(__file__).resolve()),
                ("symlink_escape", workspace / "linked-private.txt"),
            ):
                command = ("/bin/cat", str(path))
                result = run(name, command)
                record(
                    name,
                    result,
                    command_passed(result, command, readable=False, public=public, secret=secret),
                )
            command = (
                "/bin/bash",
                "--noprofile",
                "--norc",
                "-c",
                '/bin/cat "$1"; exit "$?"',
                "probe",
                str(private / "labels.txt"),
            )
            result = run("child_private_labels", command)
            # The child cat emits the same exact-path diagnostic as a direct
            # read, while bash propagates its exit status.
            record(
                "child_private_labels",
                result,
                command_passed(
                    result,
                    ("/bin/cat", str(private / "labels.txt")),
                    readable=False,
                    public=public,
                    secret=secret,
                ),
            )
            command = ("/usr/bin/touch", str(workspace / "forbidden-write"))
            result = run("workspace_write", command)
            record(
                "workspace_write",
                result,
                command_passed(result, command, readable=False, public=public, secret=secret)
                and not (workspace / "forbidden-write").exists(),
            )
            # An approved scratch write establishes that the policy is usable.
            result = run("scratch_write", ("/usr/bin/touch", str(scratch / "allowed-write")))
            record(
                "scratch_write",
                result,
                result.returncode == 0 and (scratch / "allowed-write").is_file(),
            )
            for name, listener, extra, url in (
                ("tcp", tcp, (), f"http://127.0.0.1:{tcp.port}/"),
                ("unix", unix, ("--unix-socket", str(unix_path)), "http://localhost/"),
            ):
                command = (
                    "/usr/bin/curl",
                    "--silent",
                    "--show-error",
                    "--noproxy",
                    "*",
                    "--connect-timeout",
                    "1",
                    "--max-time",
                    "2",
                    *extra,
                    url,
                )
                baseline = run(f"{name}_control", command, control=True)
                record(
                    f"{name}_control",
                    baseline,
                    baseline.returncode == 0
                    and baseline.stdout == b"ok\n"
                    and listener.requests == 1,
                )
                if not records[-1]["passed"]:
                    break
                result = run(f"{name}_denied", command)
                record(
                    f"{name}_denied",
                    result,
                    result.returncode == 7
                    and not result.stdout
                    and b"curl: (7)" in result.stderr
                    and listener.requests == 1,
                )
    finally:
        tcp.close()
        if unix is not None:
            unix.close()
    elapsed = time.monotonic() - began
    passed = (
        len(records) == 15
        and all(r["passed"] for r in records)
        and elapsed <= 80
        and not tcp.errors
        and unix is not None
        and not unix.errors
    )
    receipt = {
        "schema_version": "1.0",
        "purpose": "external-offline-boundary-probe",
        "status": "external_probe_passed" if passed else "failed",
        "host_qualified": False,
        "networked_host_qualified": False,
        "provider_calls": 0,
        "real_credentials_used": False,
        "platform": platform.platform(),
        "inventory": asdict(inventory),
        "policy_sha256": hashlib.sha256(policy.encode()).hexdigest(),
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "elapsed_seconds": elapsed,
        "checks": records,
        "expected_checks": 15,
        "tcp_requests": tcp.requests,
        "unix_requests": None if unix is None else unix.requests,
        "listener_errors": tcp.errors + ([] if unix is None else unix.errors),
        "remaining_gates": [
            "actual_exec_fake_service",
            "brokered_egress",
            "tool_surfaces",
            "credential_separation",
            "host_lifecycle",
            "live_conformance",
        ],
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"External boundary probe: {receipt['status']} in {elapsed:.2f} seconds", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if exercise(args.output)["status"] == "external_probe_passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
