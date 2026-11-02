"""Candidate macOS policy for the fixed Claude bare/API-helper transport.

Rendering is not qualification. Only explicit loopback endpoints are supported.
External API traffic needs a separately qualified broker, not wildcard network
access. No existing native Codex qualification is reused.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import Record
from autoengineering.campaign.store import checked_directory

VERSION = "claude-helper-policy-1.4"
SHELL_FILES = ("/bin/sh", "/bin/bash", "/private/var/select/sh")


def _within(path: Path, root: Path) -> bool:
    # macOS commonly resolves case aliases to the same directory. Lexical prefix
    # checks alone can miss an overlap. All paths have already been checked.
    if path.is_relative_to(root):
        return True
    try:
        metadata = root.stat()
    except FileNotFoundError:
        return False
    key = (metadata.st_dev, metadata.st_ino)
    for parent in (path, *path.parents):
        try:
            metadata = parent.stat()
        except FileNotFoundError:
            continue
        if (metadata.st_dev, metadata.st_ino) == key:
            return True
    return False


@dataclass(frozen=True)
class ClaudeEgress(Record):
    address: str
    port: int

    def _validate(self):
        if self.address != "localhost" or not 0 < self.port < 65536:
            raise ValueError("Claude endpoint requires localhost and a valid port")


@dataclass(frozen=True)
class ClaudePolicy(Record):
    schema: str
    workspace: str
    home: str
    executable: str
    helper: str
    python: str
    python_root: str
    credential_files: tuple[str, ...]
    endpoints: tuple[ClaudeEgress, ...]
    forbidden_roots: tuple[str, ...]

    def _validate(self):
        if self.schema != VERSION:
            raise ValueError("unsupported Claude policy version")
        if not 1 <= len(self.forbidden_roots) <= 32 or not 0 <= len(self.credential_files) <= 4:
            raise ValueError("Claude policy needs bounded explicit private roots/files")
        if len(self.endpoints) > 16 or len(set((e.address, e.port) for e in self.endpoints)) != len(
            self.endpoints
        ):
            raise ValueError("Claude policy endpoints must be unique and bounded")
        directories = (self.workspace, self.home, self.python_root, *self.forbidden_roots)
        files = (self.executable, self.helper, self.python, *self.credential_files)
        for name in (*directories, *files):
            p = Path(name)
            if not p.is_absolute() or ".." in p.parts or str(p) != name:
                raise ValueError("Claude policy paths must be canonical absolute paths")
        for name in directories:
            p = Path(name)
            # Public Python runtime roots need not be owner-private. Other
            # directories are supplied by the trusted caller, never a worker.
            if name in (self.workspace, self.home):
                checked_directory(p)
            if any(x.is_symlink() for x in (p, *p.parents)) or not p.is_dir():
                raise ValueError("Claude policy directory is missing or symlinked")
        for name in files:
            p = Path(name)
            confined_file(p.parent, p.name)
        writable = Path(self.home)
        workspace = Path(self.workspace)
        if writable == workspace or _within(writable, workspace) or _within(workspace, writable):
            raise ValueError("Claude home and worker workspace must be separate")
        if any(_within(Path(n), writable) or _within(Path(n), workspace) for n in files):
            raise ValueError(
                "Claude helper/credentials cannot be in client-writable or worker scope"
            )
        runtime = Path(self.python_root)
        if not _within(Path(self.python), runtime) or any(
            _within(runtime, p) or _within(p, runtime) for p in (workspace, writable)
        ):
            raise ValueError("Claude helper runtime must be separate and contain its interpreter")
        if len(set(self.forbidden_roots)) != len(self.forbidden_roots):
            raise ValueError("Claude private roots must be unique")
        trees = (
            workspace,
            writable,
            Path(self.python_root),
            Path("/usr/lib"),
            Path("/System/Library"),
            Path("/usr/share/icu"),
        )
        for forbidden in map(Path, self.forbidden_roots):
            if any(_within(t, forbidden) or _within(forbidden, t) for t in trees):
                raise ValueError("Claude private root overlaps allowed trees")
            if any(_within(Path(n), forbidden) for n in (*files, *SHELL_FILES)):
                raise ValueError("Claude private root contains an allowed file")
        if len(set(self.credential_files)) != len(self.credential_files):
            raise ValueError("Claude credential paths must be unique")


def render_claude_policy(spec: ClaudePolicy) -> str:
    """Produce deny-default SBPL. This function opens no credential contents."""
    if sys.platform != "darwin":
        raise ValueError("Claude macOS policy is unsupported on this platform")
    # Recheck path state before rendering. A prior valid object is not permission
    # to follow a later symlink or expose a changed path hierarchy.
    spec = ClaudePolicy.from_dict(spec.to_dict())
    trees = (
        spec.workspace,
        spec.home,
        spec.python_root,
        "/usr/lib",
        "/System/Library",
        "/usr/share/icu",
    )
    literals = (
        spec.executable,
        spec.helper,
        spec.python,
        *SHELL_FILES,
        *spec.credential_files,
        "/",
        "/dev/null",
        "/dev/random",
        "/dev/urandom",
        "/etc",
        "/private/etc/ssl/openssl.cnf",
    )
    metadata = sorted({str(p) for name in (*trees, *literals) for p in Path(name).parents})

    def quote(p):
        return json.dumps(str(p), ensure_ascii=True)

    lines = [
        "(version 1)",
        "(deny default)",
        "(deny process-info*)",
        "(allow process-info* (target self))",
        '(allow sysctl-read (sysctl-name-prefix "hw.") (sysctl-name "kern.osrelease") (sysctl-name "kern.osversion") (sysctl-name "kern.ostype") (sysctl-name "kern.osproductversion"))',
        "(allow process-fork)",
        "(allow process-exec "
        + " ".join(
            "(literal " + quote(n) + ")"
            for n in (spec.executable, spec.helper, spec.python, "/bin/sh", "/bin/bash")
        )
        + ")",
        "(allow file-read* "
        + " ".join("(subpath " + quote(n) + ")" for n in trees)
        + " "
        + " ".join("(literal " + quote(n) + ")" for n in literals)
        + ")",
        "(allow file-read-metadata "
        + " ".join("(literal " + quote(n) + ")" for n in metadata)
        + ")",
        "(allow file-write* (subpath " + quote(spec.home) + ') (literal "/dev/null"))',
    ]
    if spec.endpoints:
        lines.append(
            "(allow network-outbound "
            + " ".join(
                "(remote ip " + quote(e.address + ":" + str(e.port)) + ")" for e in spec.endpoints
            )
            + ")"
        )
    return "\n".join(lines) + "\n"
