"""Scoped code-production workspaces and immutable patch/source capture.

Capturing and inspecting source never executes it. Static checks implement the
initial interface/dependency policy and are not an execution security boundary.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
import difflib
import hashlib
import os
from pathlib import Path
import stat
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef, identifier, sha256
from autoengineering.campaign.serialization import Record, canonical_json
from autoengineering.campaign.store import checked_directory, durable_write


@dataclass(frozen=True)
class WorkspacePolicy(Record):
    schema_version: Literal["1.0"]
    allowed_files: tuple[Literal["adapter.py"], ...] = ("adapter.py",)
    dependencies: tuple[Literal["python-stdlib", "math"], ...] = ("python-stdlib", "math")
    max_bytes: int = 65536

    def _validate(self):
        if self.allowed_files != ("adapter.py",) or self.dependencies != ("python-stdlib", "math"):
            raise ValueError("initial workspace policy permits one adapter and fixed dependencies")
        if not 0 < self.max_bytes <= 65536:
            raise ValueError("workspace source ceiling must be in 1..65536")


@dataclass(frozen=True)
class WorkspaceManifest(Record):
    schema_version: Literal["1.0"]
    run_id: str
    task_id: str
    policy: WorkspacePolicy
    base_sources: Mapping[str, ArtifactRef]

    def _validate(self):
        identifier(self.run_id)
        identifier(self.task_id)
        if set(self.base_sources) != set(self.policy.allowed_files):
            raise ValueError("workspace baseline differs from the source allowlist")


@dataclass(frozen=True)
class SourceCapture(Record):
    schema_version: Literal["1.0"]
    base_snapshot: str
    source_digest: str
    policy_digest: str
    sources: Mapping[str, ArtifactRef]
    patch: ArtifactRef
    issues: tuple[str, ...]

    def _validate(self):
        for value in (self.base_snapshot, self.source_digest, self.policy_digest):
            sha256(value)


def inspect_source(raw: bytes) -> tuple[str, ...]:
    try:
        text = raw.decode("utf-8")
        if "\x00" in text:
            return ("binary_source",)
        tree = ast.parse(text)
    except (UnicodeError, SyntaxError, RecursionError):
        return ("invalid_python_source",)
    issues = set()
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "predict":
        issues.add("requires_one_predict_function")
    elif (
        len(functions[0].args.args) != 1
        or functions[0].args.args[0].arg != "inputs"
        or functions[0].args.posonlyargs
        or functions[0].args.kwonlyargs
        or functions[0].args.vararg
        or functions[0].args.kwarg
        or functions[0].args.defaults
        or functions[0].decorator_list
    ):
        issues.add("predict_interface_changed")
    permitted_calls = {"abs", "min", "max", "sum", "float", "int", "len", "range"}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom)) and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            issues.add("undeclared_module_initialization")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(n.name != "math" or n.asname for n in node.names):
            issues.add("undeclared_import")
        elif isinstance(node, ast.ImportFrom):
            # Keep this first policy simple. math functions use math.name.
            issues.add("undeclared_import")
        elif isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Global, ast.Nonlocal)):
            issues.add("undeclared_runtime_structure")
        elif isinstance(node, ast.Name) and node.id.startswith("__"):
            issues.add("undeclared_runtime_access")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            issues.add("undeclared_runtime_access")
        elif isinstance(node, ast.Call):
            valid = isinstance(node.func, ast.Name) and node.func.id in permitted_calls
            valid = valid or (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "math"
                and not node.func.attr.startswith("_")
            )
            if not valid:
                issues.add("undeclared_call")
    return tuple(sorted(issues))


class CandidateWorkspace:
    def __init__(self, root: Path, manifest: WorkspaceManifest):
        self.root = checked_directory(root)
        self.candidate = checked_directory(self.root / "candidate")
        self.manifest = manifest
        path = confined_file(self.root, "manifest.json")
        if path.stat().st_size > 65536 or WorkspaceManifest.from_json(path.read_text()) != manifest:
            raise ValueError("workspace manifest identity mismatch")

    @classmethod
    def create(
        cls,
        root: Path,
        *,
        run_id: str,
        task_id: str,
        baseline: Mapping[str, bytes],
        policy: WorkspacePolicy = WorkspacePolicy("1.0"),
    ):
        if set(baseline) != set(policy.allowed_files) or any(
            type(value) is not bytes for value in baseline.values()
        ):
            raise ValueError("baseline must match the exact source allowlist")
        if sum(len(value) for value in baseline.values()) > policy.max_bytes:
            raise ValueError("baseline exceeds workspace byte ceiling")
        root = Path(root).absolute()
        if root.exists() or root.is_symlink():
            raise ValueError("candidate workspace requires a fresh directory")
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        for name in ("candidate", "artifacts"):
            (root / name).mkdir(mode=0o700)
        sources = {}
        for name, raw in baseline.items():
            sources[name] = put_bytes(
                root, raw, name=name, media_type="text/x-python", producer="trusted-base"
            )
            durable_write(root / "candidate" / name, raw)
        manifest = WorkspaceManifest("1.0", run_id, task_id, policy, sources)
        durable_write(root / "manifest.json", manifest.to_json().encode())
        return cls(root, manifest)

    def capture(self) -> SourceCapture:
        """Capture bounded regular bytes before checks, including invalid candidates."""
        if (
            WorkspaceManifest.from_json(confined_file(self.root, "manifest.json").read_text())
            != self.manifest
        ):
            raise ValueError("workspace manifest changed")
        checked_directory(self.candidate)
        sources, issues = {}, []
        total = 0
        entries = []
        for index, path in enumerate(self.candidate.iterdir()):
            if index == 64:
                issues.append("entry_limit_exceeded")
                break
            entries.append(path)
        entries.sort()
        for path in entries:
            name = path.name
            if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                issues.append(f"nonregular_entry:{name}")
                continue
            # Initial allowlist is flat. O_NOFOLLOW and descriptor checks avoid
            # following an edited file into evaluator or author directories.
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_size > self.manifest.policy.max_bytes - total
                ):
                    issues.append(f"source_limit:{name}")
                    continue
                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                    raw = stream.read(self.manifest.policy.max_bytes - total + 1)
            finally:
                os.close(descriptor)
            if len(raw) > self.manifest.policy.max_bytes - total:
                issues.append(f"source_limit:{name}")
                continue
            total += len(raw)
            sources[name] = put_bytes(
                self.root,
                raw,
                name="source.bin",
                media_type="application/octet-stream",
                producer="candidate-capture",
            )
            if name not in self.manifest.policy.allowed_files:
                issues.append(f"undeclared_file:{name}")
        if set(sources) != set(self.manifest.policy.allowed_files):
            issues.append("source_allowlist_changed")
        patch = []
        for name in sorted(set(self.manifest.policy.allowed_files) | set(sources)):
            original = (
                read_bytes(
                    self.root,
                    self.manifest.base_sources[name],
                    max_bytes=self.manifest.policy.max_bytes,
                )
                if name in self.manifest.base_sources
                else b""
            )
            current = (
                read_bytes(self.root, sources[name], max_bytes=self.manifest.policy.max_bytes)
                if name in sources
                else b""
            )
            patch.extend(
                difflib.unified_diff(
                    original.decode("utf-8", errors="replace").splitlines(keepends=True),
                    current.decode("utf-8", errors="replace").splitlines(keepends=True),
                    fromfile=f"base/{name}",
                    tofile=f"candidate/{name}",
                )
            )
            if name in self.manifest.policy.allowed_files:
                issues.extend(f"{issue}:{name}" for issue in inspect_source(current))
        patch_ref = put_bytes(
            self.root,
            "".join(patch).encode(),
            name="candidate.patch",
            media_type="text/x-diff",
            producer="candidate-capture",
        )
        identity = hashlib.sha256(
            canonical_json({name: ref.sha256 for name, ref in sources.items()}).encode()
        ).hexdigest()
        capture = SourceCapture(
            "1.0",
            self.manifest.digest,
            identity,
            self.manifest.policy.digest,
            sources,
            patch_ref,
            tuple(sorted(set(issues))),
        )
        put_bytes(
            self.root,
            capture.to_json().encode(),
            name="capture.json",
            media_type="application/json",
            producer="candidate-capture",
        )
        return capture

    def verify_capture(self, capture: SourceCapture):
        """Verify immutable capture integrity. This is not executable admission."""
        if (
            capture.base_snapshot != self.manifest.digest
            or capture.policy_digest != self.manifest.policy.digest
        ):
            raise ValueError("capture belongs to a different workspace or source policy")
        if sum(ref.size_bytes for ref in capture.sources.values()) > self.manifest.policy.max_bytes:
            raise ValueError("captured source exceeds workspace byte ceiling")
        for ref in capture.sources.values():
            read_bytes(self.root, ref, max_bytes=self.manifest.policy.max_bytes)
        read_bytes(self.root, capture.patch)
        actual = hashlib.sha256(
            canonical_json({name: ref.sha256 for name, ref in capture.sources.items()}).encode()
        ).hexdigest()
        if actual != capture.source_digest:
            raise ValueError("captured source identity mismatch")
