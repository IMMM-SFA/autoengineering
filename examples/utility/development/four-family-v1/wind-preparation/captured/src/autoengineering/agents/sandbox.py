"""Explicit macOS deny-by-default boundary for generated Python execution.

The workspace is read-only during execution. The only output channel is the
inherited bounded pipe. This policy grants no network or child-process access.
It does not qualify a networked host worker boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys
import sysconfig

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import checked_directory


@dataclass(frozen=True)
class BoundaryLimits:
    cpu_seconds: int = 2
    memory_bytes: int = 256 * 1024 * 1024
    output_bytes: int = 65536

    def __post_init__(self):
        if any(
            type(value) is not int or value <= 0
            for value in (
                self.cpu_seconds,
                self.memory_bytes,
                self.output_bytes,
            )
        ):
            raise ValueError("boundary limits require positive integers")
        if (
            self.cpu_seconds > 60
            or self.memory_bytes > 1024 * 1024 * 1024
            or self.output_bytes > 65536
        ):
            raise ValueError("boundary limits exceed the initial execution policy")


class MacOSBoundary:
    """Construct a fixed generated-code policy. Qualification is recorded separately."""

    version = "macos-generated-1.0"

    def __init__(self):
        if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
            raise ValueError("macOS generated boundary is unavailable")
        self.python = Path(sys.executable).resolve()
        self.library = Path(sysconfig.get_config_var("LIBDIR")).resolve()
        self.site_packages = Path(sysconfig.get_path("purelib")).resolve()
        self.wrapper = Path(__file__).with_name("resource_worker.py").absolute()
        confined_file(self.wrapper.parent, self.wrapper.name)

    def profile(self, workspace: Path) -> str:
        workspace = checked_directory(workspace)
        reads = [Path("/usr/lib"), Path("/System/Library"), self.library, workspace]
        literals = [
            Path("/"),
            self.python,
            self.wrapper,
            Path("/dev/null"),
            Path("/dev/random"),
            Path("/dev/urandom"),
        ]
        metadata = {str(parent) for path in (*reads, *literals) for parent in path.parents}

        def quote(value):
            return json.dumps(str(value), ensure_ascii=True)

        rules = [
            "(version 1)",
            "(deny default)",
            "(allow sysctl-read)",
            f"(allow process-exec (literal {quote(self.python)}))",
            "(deny process-fork)",
            "(allow file-read* "
            + " ".join(f"(subpath {quote(path)})" for path in reads)
            + " "
            + " ".join(f"(literal {quote(path)})" for path in literals)
            + ")",
            "(allow file-read-metadata "
            + " ".join(f"(literal {quote(path)})" for path in sorted(metadata))
            + ")",
            f"(deny file-read* (subpath {quote(self.site_packages)}))",
        ]
        return "\n".join(rules)

    def command(self, workspace: Path, entrypoint: str, limits: BoundaryLimits) -> tuple[str, ...]:
        workspace = checked_directory(workspace)
        source = confined_file(workspace, entrypoint)
        return (
            "/usr/bin/sandbox-exec",
            "-p",
            self.profile(workspace),
            str(self.python),
            "-I",
            "-S",
            "-B",
            str(self.wrapper),
            "--cpu",
            str(limits.cpu_seconds),
            "--memory",
            str(limits.memory_bytes),
            "--file-bytes",
            str(limits.output_bytes),
            str(source),
        )

    def identity(self, workspace: Path, limits: BoundaryLimits) -> str:
        return digest(
            {
                "version": self.version,
                "platform": platform.platform(),
                "python": hashlib.sha256(self.python.read_bytes()).hexdigest(),
                "wrapper": hashlib.sha256(self.wrapper.read_bytes()).hexdigest(),
                "profile": self.profile(workspace),
                "limits": {
                    "cpu_seconds": limits.cpu_seconds,
                    "memory_bytes": limits.memory_bytes,
                    "output_bytes": limits.output_bytes,
                },
            }
        )
