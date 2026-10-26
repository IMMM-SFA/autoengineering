"""Verify saved numerical claims and seal investigation artifacts without replacement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .science import digest, identity, metrics


def verify(directory: Path) -> dict:
    runs = sorted((directory / "comparison").glob("*-*/evaluation.json"))
    expected = None
    for path in runs:
        record = json.loads(path.read_text())
        if record["hashes"] != identity():
            raise ValueError(f"source identity changed: {path}")
        result = record["response"]
        if expected is None:
            expected = result
        if result != expected:
            raise ValueError("transport parity failed")
        for family, summary in result["families"].items():
            with np.load(path.parent / f"{family}.npz", allow_pickle=False) as arrays:
                mask = arrays["comparison_mask"]
                scores = metrics(arrays["predicted"][mask], arrays["observed"][mask])
                for metric, value in scores.items():
                    if not np.isclose(value, summary["comparison"][metric], atol=1e-12, rtol=0):
                        raise ValueError(f"metric reconstruction failed: {path}: {metric}")
        for family in ("triangular", "gamma"):
            records = (path.parent / family / "observations.jsonl").read_text().splitlines()
            if len(records) != 16:
                raise ValueError(f"family evaluation count differs: {path}")
    if len(runs) != 6:
        raise ValueError("expected six deterministic transport runs")
    return dict(runs=len(runs), parity=True, independently_reconstructed_metrics=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.directory)))
    manifest = args.directory / "artifact-manifest.json"
    if args.seal:
        paths = {
            str(p.relative_to(args.directory)): digest(p)
            for p in sorted(args.directory.rglob("*"))
            if p.is_file() and p != manifest and not p.name.endswith(".lock")
        }
        with manifest.open("x") as stream:
            json.dump(paths, stream, indent=2, sort_keys=True)
    else:
        for name, expected in json.loads(manifest.read_text()).items():
            path = args.directory / name
            if not path.is_relative_to(args.directory) or digest(path) != expected:
                raise ValueError(f"artifact changed: {name}")
        print("Artifact hashes match.")


if __name__ == "__main__":
    main()
