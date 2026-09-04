"""Run or verify the preregistered Release A benchmark gate."""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

from .runner import execute_suite, read_raw_records, write_raw_records
from .summary import evaluate_gate, gate_json, render_report, summarize_records, summary_csv


def _repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "decisions" / "0001-release-a-benchmark.md").is_file():
            return parent
    raise RuntimeError("Release A benchmark must run from an autoengineering checkout")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hash(root: Path) -> str:
    digest = hashlib.sha256()
    sources = sorted(
        [
            *(root / "src/autoengineering/benchmarks/release_a").rglob("*.py"),
            *(root / "src/autoengineering/optimization").rglob("*.py"),
            root / "pyproject.toml",
            root / "pixi.toml",
            root / "pixi.lock",
        ],
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for source in sources:
        digest.update(source.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
    return digest.hexdigest()


def _provenance(root: Path, output: Path) -> dict[str, object]:
    decision = root / "docs/decisions/0001-release-a-benchmark.md"
    correction = root / "docs/decisions/0002-release-a-evidence-corrections.md"
    status = _git_output(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise ValueError("benchmark execution requires a clean Git checkout")
    revision = _git_output(root, "rev-parse", "HEAD")
    versions = {}
    for package in (
        "autoengineering",
        "numpy",
        "scipy",
        "torch",
        "botorch",
        "gpytorch",
        "smac",
        "ConfigSpace",
    ):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not_installed"
    return {
        "decision_sha256": _sha256(decision),
        "correction_sha256": _sha256(correction),
        "source_sha256": _source_hash(root),
        "git_head_at_execution": revision,
        "git_tree_clean": True,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": versions,
        "command": f"pixi run -e bayes benchmark-release-a --output {output}",
    }


def _git_output(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _artifact_texts(records, provenance):
    rows = summarize_records(records)
    gate = evaluate_gate(records, provenance=provenance)
    return {
        "run-summary.csv": summary_csv(rows),
        "gate.json": gate_json(gate),
        "report.md": render_report(rows, gate),
    }, gate


def run_new(output: Path) -> bool:
    """Run the full suite and atomically publish all evidence to an absent directory."""
    if output.exists() or output.is_symlink():
        raise ValueError("benchmark output already exists; verify it instead of replacing it")
    root = _repository_root()
    provenance = _provenance(root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / f".{output.name}.lock"
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("another benchmark publication holds the output lock") from error
    temporary: Path | None = None
    try:
        if output.exists() or output.is_symlink():
            raise ValueError("benchmark output appeared while acquiring the publication lock")
        temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        records = execute_suite()
        write_raw_records(temporary / "raw-records.jsonl", records)
        texts, gate = _artifact_texts(records, provenance)
        for name, contents in texts.items():
            (temporary / name).write_text(contents, encoding="utf-8", newline="\n")
        if output.exists() or output.is_symlink():
            raise ValueError("benchmark output appeared before atomic publication")
        os.replace(temporary, output)
        temporary = None
    except BaseException:
        if temporary is not None:
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    finally:
        os.close(lock_descriptor)
        lock_path.unlink(missing_ok=True)
    return bool(gate["passed"])


def verify_existing(output: Path) -> bool:
    """Rebuild every derived artifact from checked raw evidence without mutation."""
    raw_path = output / "raw-records.jsonl"
    gate_path = output / "gate.json"
    if not raw_path.is_file() or not gate_path.is_file():
        raise ValueError("existing benchmark output is incomplete")
    existing_gate = json.loads(gate_path.read_text(encoding="utf-8"))
    provenance = existing_gate["provenance"]
    root = _repository_root()
    if provenance["decision_sha256"] != _sha256(
        root / "docs/decisions/0001-release-a-benchmark.md"
    ):
        raise ValueError("checked benchmark decision hash differs from the current decision")
    if provenance["correction_sha256"] != _sha256(
        root / "docs/decisions/0002-release-a-evidence-corrections.md"
    ):
        raise ValueError("checked benchmark correction hash differs from the current decision")
    if provenance["source_sha256"] != _source_hash(root):
        raise ValueError("checked benchmark source hash differs from the current implementation")
    records = read_raw_records(raw_path)
    expected, gate = _artifact_texts(records, provenance)
    mismatches = [
        name
        for name, contents in expected.items()
        if not (output / name).is_file() or (output / name).read_text(encoding="utf-8") != contents
    ]
    if mismatches:
        raise ValueError(f"derived benchmark artifacts differ from raw records: {mismatches}")
    return bool(gate["passed"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/release_a/results"),
        help="Absent output directory to create, or existing evidence to verify.",
    )
    arguments = parser.parse_args(argv)
    try:
        passed = (
            verify_existing(arguments.output)
            if arguments.output.exists()
            else run_new(arguments.output)
        )
    except Exception as error:
        parser.exit(2, f"benchmark error: {error}\n")
    print(f"Release A benchmark gate: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
