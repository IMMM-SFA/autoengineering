"""Input integrity and evidence records shared by the three open model examples."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import platform
import time
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np

from autoengineering.execute.swap import swap_component
from autoengineering.system.graph import System


def passthrough(value: np.ndarray) -> np.ndarray:
    """Expose an additional port through a graph whose edges hold one port pair."""
    return value


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fetch_sources(directory: Path) -> None:
    """Download only declared public files; verify both new and cached content."""
    manifest = json.loads((directory / "sources.json").read_text())
    cache = directory / "data"
    cache.mkdir(exist_ok=True)
    for item in manifest["files"]:
        destination = cache / item["name"]
        if not destination.exists():
            print(f"Downloading {item['name']} ({item['bytes'] / 1e6:.1f} MB)", flush=True)
            partial = destination.with_suffix(destination.suffix + ".part")
            try:
                with urllib.request.urlopen(item["url"], timeout=120) as src:
                    with partial.open("wb") as dst:
                        while block := src.read(1024 * 1024):
                            dst.write(block)
                verify_file(partial, item)
                partial.replace(destination)
            finally:
                partial.unlink(missing_ok=True)
        verify_file(destination, item)
        print(f"Verified {item['name']}", flush=True)


def verify_file(path: Path, item: dict) -> None:
    if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
        raise ValueError(f"Input integrity mismatch: {path.name}; refusing changed data")


def verify_sources(directory: Path) -> list[dict]:
    manifest = json.loads((directory / "sources.json").read_text())
    for item in manifest["files"]:
        path = directory / "data" / item["name"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path.name}. Run this example's fetch command first.")
        verify_file(path, item)
    return manifest["files"]


def parser(description: str) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=description)
    result.add_argument(
        "--fetch", action="store_true", help="Fetch and verify pinned public inputs"
    )
    result.add_argument("--output", type=Path, required=False)
    result.add_argument(
        "--smoke", action="store_true", help="Use a short execution check, not a benchmark"
    )
    return result


def output_directory(here: Path, supplied: Path | None) -> Path:
    output = supplied or here / "outputs" / time.strftime("%Y%m%d-%H%M%S")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    return output


def compare(
    here: Path,
    output: Path,
    evaluate: Callable,
    *,
    objective: str,
    evidence: str,
    packages: list[str],
    context: dict,
    test: Callable | None = None,
) -> dict:
    """Bounded independent swaps against one immutable baseline, minimizing objective.

    This is an explicit candidate comparison using the package's graph and swap API.
    It is not Bayesian optimization. Test data are evaluated only after selection.
    """
    system = System.from_yaml(here / "system.yaml")
    candidates = json.loads((here / "candidates.json").read_text())
    records = []
    systems = {"baseline": system}
    (output / "graph.mmd").write_text(system.to_mermaid() + "\n")
    system.to_yaml(output / "baseline-system.yaml")
    source_files = sorted(here.glob("*.py")) + sorted(here.glob("*.yaml"))
    source_files += [here / "candidates.json", Path(__file__), here.parent / "__init__.py"]
    if (here / "sources.json").exists():
        source_files.append(here / "sources.json")
    write_json(
        output / "manifest.json",
        {
            "evidence_kind": evidence,
            "objective": objective,
            "direction": "minimize",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {p: importlib.metadata.version(p) for p in packages},
            "source_sha256": {str(p.relative_to(here.parent)): digest(p) for p in source_files},
            "context": context,
            "pixi_lock_sha256": digest(here.parents[2] / "pixi.lock"),
            "core_source_sha256": {
                str(p.relative_to(here.parents[2])): digest(p)
                for p in sorted((here.parents[2] / "src/autoengineering").rglob("*.py"))
            },
            "pixi_manifest_sha256": digest(here.parents[2] / "pixi.toml"),
        },
    )
    for index, spec in enumerate([None, *candidates]):
        name = "baseline" if spec is None else spec["id"]
        print(f"[{index + 1}/{len(candidates) + 1}] {name}", flush=True)
        trial = system
        if spec is not None:
            replacement = copy.deepcopy(system.get_component(spec["component"]))
            replacement.metadata["runnable"]["params"].update(spec["params"])
            trial = swap_component(system, spec["component"], replacement)
        start = time.perf_counter()
        try:
            value, metrics, arrays = evaluate(trial)
            if not np.isfinite(value):
                raise ValueError("Nonfinite objective")
            for key, array in arrays.items():
                if not np.isfinite(np.asarray(array)).all():
                    raise ValueError(f"Nonfinite output: {key}")
            np.savez_compressed(output / f"{name}.npz", **arrays)
            record = {
                "id": name,
                "status": "evaluated" if metrics.get("feasible", True) else "infeasible",
                "objective": float(value),
                "metrics": metrics,
                "seconds": time.perf_counter() - start,
                "candidate": spec,
            }
            systems[name] = trial
        except Exception as error:
            record = {
                "id": name,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
                "seconds": time.perf_counter() - start,
                "candidate": spec,
            }
        records.append(record)
        write_json(output / "trials.json", records)
        if record["status"] == "failed" and name == "baseline":
            raise RuntimeError(f"Baseline failed: {record['error']}")
    valid = [r for r in records if r["status"] == "evaluated"]
    if not valid:
        raise RuntimeError("No feasible completed candidate; see trials.json")
    winner = min(valid, key=lambda r: r["objective"])
    selected = systems[winner["id"]]
    selected.to_yaml(output / "selected-system.yaml")
    write_json(output / "selection.json", {"id": winner["id"], "objective": winner["objective"]})
    assessment = None
    if test is not None:
        print("Evaluating frozen selection on held-out data", flush=True)
        assessment = test(system, selected, output)
    summary = {
        "evidence_kind": evidence,
        "objective": objective,
        "selected": winner["id"],
        "baseline": records[0]["objective"],
        "selected_value": winner["objective"],
        "gain": records[0]["objective"] - winner["objective"],
        "test": assessment,
        "failed_trials": sum(r["status"] == "failed" for r in records),
        "infeasible_trials": sum(r["status"] == "infeasible" for r in records),
    }
    write_json(output / "summary.json", summary)
    lines = [
        "# Open model chain comparison",
        "",
        evidence,
        "",
        f"Objective: {objective} (minimize).",
        f"Selected: {winner['id']}.",
        "",
        "| Trial | Objective | Seconds | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for record in records:
        value = record.get("objective")
        shown = "unavailable" if value is None else f"{value:.6g}"
        lines.append(f"| {record['id']} | {shown} | {record['seconds']:.3f} | {record['status']} |")
        if "error" in record:
            lines.extend(["", f"Failure ({record['id']}): {record['error']}", ""])
    lines.extend(
        [
            "",
            "Candidate selection uses the declared selection objective only.",
            "A zero gain or failed candidate remains part of the result.",
            "",
            "See manifest.json, trials.json, summary.json and the NPZ arrays for evidence.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n")
    write_json(
        output / "artifact-sha256.json",
        {p.name: digest(p) for p in output.iterdir() if p.is_file()},
    )
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Report: {output / 'report.md'}", flush=True)
    if summary["failed_trials"]:
        raise RuntimeError("Some candidates failed; see trials.json. This run is incomplete.")
    return summary
