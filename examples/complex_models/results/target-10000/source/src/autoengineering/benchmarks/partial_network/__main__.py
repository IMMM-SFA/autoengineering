"""Run or verify the preregistered partial-network benchmark."""

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
from .summary import (
    component_csv,
    component_summary,
    evaluate_gate,
    gate_json,
    render_report,
    summarize_records,
    summary_csv,
    value_cost_json,
    value_cost_payload,
)


def repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "docs" / "decisions").is_dir():
            return parent
    raise RuntimeError("benchmark must run from an autoengineering checkout")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(root: Path) -> tuple[Path, ...]:
    names = (
        "src/autoengineering/optimization/backend.py",
        "src/autoengineering/optimization/controller.py",
        "src/autoengineering/optimization/full_network_backend.py",
        "src/autoengineering/optimization/function_network.py",
        "src/autoengineering/optimization/function_network_evaluator.py",
        "src/autoengineering/optimization/ledger.py",
        "src/autoengineering/optimization/partial_network_backend.py",
        "src/autoengineering/optimization/partial_network_baselines.py",
        "src/autoengineering/optimization/records.py",
        "src/autoengineering/optimization/space.py",
        "src/autoengineering/optimization/spec.py",
        "src/autoengineering/research/runner.py",
        "pyproject.toml",
        "pixi.toml",
        "pixi.lock",
    )
    benchmark = tuple((root / "src/autoengineering/benchmarks/partial_network").glob("*.py"))
    return tuple(
        sorted(
            (*benchmark, *(root / name for name in names)),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )


def source_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in source_files(root):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def source_file_hashes(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256(path) for path in source_files(root)}


def _git_output(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _provenance(root: Path, output: Path) -> dict[str, object]:
    if _git_output(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("benchmark execution requires a clean Git checkout")
    decision = root / "docs/decisions/0007-partial-network-benchmark.md"
    if not decision.is_file():
        raise ValueError("decision 0007 must exist before benchmark execution")
    subprocess.run(
        ["git", "verify-commit", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    versions = {}
    for package in ("autoengineering", "numpy", "scipy", "torch", "botorch", "gpytorch"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not_installed"
    return {
        "decision_sha256": sha256(decision),
        "source_sha256": source_hash(root),
        "source_file_sha256": source_file_hashes(root),
        "git_head_at_execution": _git_output(root, "rev-parse", "HEAD"),
        "git_tree_clean": True,
        "git_commit_signed": True,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": versions,
        "lock_file_sha256": {
            "pixi.lock": sha256(root / "pixi.lock"),
            "pixi.toml": sha256(root / "pixi.toml"),
            "pyproject.toml": sha256(root / "pyproject.toml"),
        },
        "command": f"pixi run -e bayes benchmark-partial-network --output {output}",
    }


def _artifact_texts(records, provenance):
    rows = summarize_records(records)
    components = component_summary(records)
    gate = evaluate_gate(records, provenance=provenance)
    return {
        "run-summary.csv": summary_csv(rows),
        "component-selection.csv": component_csv(components),
        "value-cost-diagnostics.json": value_cost_json(value_cost_payload(records)),
        "gate.json": gate_json(gate),
        "report.md": render_report(rows, gate, components),
    }, gate


def run_new(output: Path) -> bool:
    """Run once and atomically publish evidence to an absent directory."""
    if output.exists() or output.is_symlink():
        raise ValueError("benchmark output already exists; verify it instead of replacing it")
    root = repository_root()
    provenance = _provenance(root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / f".{output.name}.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("another benchmark publication holds the output lock") from error
    temporary = None
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
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)
    return bool(gate["passed"])


def verify_existing(output: Path) -> bool:
    """Rebuild every derived artifact from raw evidence without mutation."""
    required = {
        "raw-records.jsonl",
        "run-summary.csv",
        "component-selection.csv",
        "value-cost-diagnostics.json",
        "gate.json",
        "report.md",
    }
    missing = sorted(name for name in required if not (output / name).is_file())
    if missing:
        raise ValueError(f"existing benchmark output is incomplete: {missing}")
    root = repository_root()
    gate_path = output / "gate.json"
    existing_gate = json.loads(gate_path.read_text(encoding="utf-8"))
    provenance = existing_gate["provenance"]
    decision = root / "docs/decisions/0007-partial-network-benchmark.md"
    if provenance["decision_sha256"] != sha256(decision):
        raise ValueError("checked benchmark decision hash differs from the current decision")
    if provenance["source_sha256"] != source_hash(root):
        raise ValueError("checked benchmark source hash differs from the current implementation")
    if provenance["source_file_sha256"] != source_file_hashes(root):
        raise ValueError("checked benchmark source-file hashes differ")
    records = read_raw_records(output / "raw-records.jsonl")
    expected, gate = _artifact_texts(records, provenance)
    mismatches = [
        name
        for name, contents in expected.items()
        if (output / name).read_text(encoding="utf-8") != contents
    ]
    if mismatches:
        raise ValueError(f"derived benchmark artifacts differ from raw records: {mismatches}")
    return bool(gate["passed"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/partial_network/results"),
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
    print(f"Partial-network benchmark gate: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
