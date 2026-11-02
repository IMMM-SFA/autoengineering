"""Bounded, digest-pinned evidence archives and offline report reconstruction.

Verification checks retained bytes, not scientific utility or model provenance.
No optional framework or executable configuration is loaded by this reader.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef, relative_path, sha256, unique
from autoengineering.campaign.serialization import Record, unique_json
from autoengineering.campaign.store import durable_write

MAX_FILES = 8192
MAX_TOTAL_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class EvidenceIndex(Record):
    schema_version: Literal[1]
    kind: Literal["bmi", "circuit", "solar_campaign", "optimizer_comparison", "diagnostic"]
    files: tuple[ArtifactRef, ...]
    omissions: tuple[str, ...]
    limitations: tuple[str, ...]

    def _validate(self):
        unique([ref.path for ref in self.files], "evidence path")
        if not self.files or len(self.files) > MAX_FILES:
            raise ValueError("evidence file count outside limits")
        if sum(ref.size_bytes for ref in self.files) > MAX_TOTAL_BYTES:
            raise ValueError("evidence archive exceeds total size limit")
        for ref in self.files:
            relative_path(ref.path)
            if ref.path == "index.json":
                raise ValueError("index cannot reference itself")


def archive(source: Path, destination: Path, paths, *, kind, omissions=(), limitations=()):
    """Copy explicitly selected regular files into a fresh local evidence root."""
    destination = Path(destination)
    selected = tuple(sorted(paths))
    unique(selected, "selected path")
    if not selected or len(selected) > MAX_FILES:
        raise ValueError("invalid evidence selection")
    refs = tuple(reference(source, path, media_type="application/octet-stream",
                           producer="part-4-evidence") for path in selected)
    index = EvidenceIndex(1, kind, refs, tuple(omissions), tuple(limitations))
    # Validate all selected paths/bytes before creating the destination.
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    for ref in refs:
        target = destination / ref.path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        durable_write(target, read_bytes(source, ref))
    durable_write(destination / "index.json", index.to_json().encode())
    return hashlib.sha256(index.to_json().encode()).hexdigest()


def verify(root: Path, expected_digest: str) -> EvidenceIndex:
    sha256(expected_digest)
    path = confined_file(root, "index.json")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("evidence index exceeds size limit")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("evidence index differs from trusted pin")
    index = EvidenceIndex.from_json(raw.decode())
    for ref in index.files:
        read_bytes(root, ref)
    return index


def reconstruct(root: Path, expected_digest: str) -> str:
    index = verify(root, expected_digest)
    allowed = {ref.path for ref in index.files}

    def load(name):
        if name not in allowed:
            raise ValueError("report refers to unindexed evidence")
        return unique_json(confined_file(root, name).read_text())

    lines = [f"# Part 4 {index.kind} evidence", "",
             f"Verified {len(index.files)} retained files against the supplied index pin.", ""]
    if index.kind == "bmi":
        import numpy as np
        from autoengineering.campaign.artifacts import read_arrays

        protocol = load("manifest.json")["protocol"]
        if (protocol["rate_semantics"], protocol["storage_semantics"], protocol["dt_days"]) != (
            "interval_mean_end", "instantaneous_end", 1.0
        ):
            raise ValueError("unsupported BMI rate/state time semantics")
        ref = next((r for r in index.files if r.path == "outputs.npz"), None)
        if ref is None:
            raise ValueError("BMI arrays are missing from indexed evidence")
        arrays = read_arrays(root, ref)
        expected = (len(protocol["forcing"]),)
        if any(value.shape != expected for value in arrays.values()):
            raise ValueError("BMI evidence shape differs from protocol")
        if not np.array_equal(arrays["flow"], arrays["direct_flow"]) or not np.array_equal(
            arrays["reservoir_storage"], arrays["direct_storage"]
        ):
            raise ValueError("retained BMI parity failed")
        dt = protocol["dt_days"]
        residual = np.asarray(protocol["forcing"]) * dt - arrays["flow"] * dt
        residual -= np.diff(np.r_[0., arrays["reservoir_storage"]])
        if not np.isfinite(residual).all() or np.max(np.abs(residual)) > protocol["conservation_atol_mm"]:
            raise ValueError("retained BMI conservation failed")
        lines += ["Direct/wrapped output parity: exact.",
                  f"Maximum conservation residual: {float(np.max(np.abs(residual)))} mm.",
                  "Daily mean rates and instantaneous end-of-interval storage remain distinct."]
    elif index.kind == "circuit":
        manifest, report = load("manifest.json"), load("report.json")
        protocol = manifest["protocol"]
        parity = load("parity.json")
        for row in parity:
            for name, actual in row["wrapped"].items():
                reference_value = row["direct"]["outputs"][name]
                atol = protocol["voltage_atol_V" if "voltage" in name else "current_atol_A"]
                if not math.isclose(actual, reference_value, abs_tol=atol,
                                    rel_tol=protocol["parity_rtol"]):
                    raise ValueError("retained circuit parity differs")
        derivative = load("derivatives.json")
        if not math.isclose(derivative["analytic"]["derivative"], derivative["finite_difference"],
                            abs_tol=protocol["derivative_atol"], rel_tol=protocol["derivative_rtol"]):
            raise ValueError("retained circuit derivative gate failed")
        lines += [f"Direct/wrapped parity cases: {len(parity)}.",
                  f"Optuna physical starts: {report['optuna_physical_starts']}.",
                  f"Native coupled solves: {report['native']['coupled_solves']}.",
                  f"Comparison: {report['native']['budget_match']}."]
    elif index.kind == "solar_campaign":
        state = load("scientific-state.json")
        attempts = state["budget"]["attempts"]
        lines += [f"Outcome: {state['outcome']}.", f"Physical attempts: {len(attempts)}.", "",
                  "| Comparison evaluation | Status | RMSE (kW) |",
                  "| --- | --- | --- |"]
        for row in state["evaluations"]:
            if row["split_id"] == "comparison":
                lines.append(f"| {row['id']} | {row['status']} | {row['metrics'].get('rmse')} |")
        lines += ["", "Previously exposed development data. Confirmation was not attempted."]
    elif index.kind == "optimizer_comparison":
        protocol = load("protocol.json")
        starts = 0
        failed = 0
        for row in load("execution.json"):
            prefix = row["cell"]
            result_paths = [p for p in allowed if p.startswith(prefix + "/result-")]
            starts += len(result_paths)
            failed += row["exit_code"] != 0
        if starts > protocol["total_physical_start_ceiling"]:
            raise ValueError("retained comparison exceeded physical ceiling")
        lines += [f"Committed physical starts: {starts}.", f"Failed cells retained: {failed}."]
    lines += ["", "Limitations:", *(f"- {item}" for item in index.limitations),
              "", "Omissions:", *(f"- {item}" for item in index.omissions), ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = reconstruct(args.root, args.expected_sha256)
    if args.output is None:
        print(report, end="")
    else:
        args.output.write_text(report)


if __name__ == "__main__":
    main()
