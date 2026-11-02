"""Standalone standard-library RMSE worker for the private macOS boundary."""
from __future__ import annotations

import json
import math
from pathlib import Path


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate private JSON key")
        result[key] = value
    return result


def main():
    root = Path(__file__).parent
    job = json.loads((root / "job.json").read_text())
    result = {"status": "infrastructure_failure", "outcome": job["outcome"],
              "units": job["units"], "value": None, "feasible": None}
    try:
        private = json.loads((root / "labels.json").read_text(), object_pairs_hook=unique_pairs)
        if not isinstance(private, dict) or set(private) != {"labels", "mask"}:
            raise ValueError("invalid private data schema")
        predicted = job["prediction"]
        labels, mask = private["labels"], private["mask"]
        if not predicted or len(predicted) != len(labels) or len(labels) != len(mask):
            raise ValueError("unaligned scoring vectors")
        if any(type(v) is not bool for v in mask):
            raise ValueError("mask is not Boolean")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (*predicted, *labels)):
            raise ValueError("invalid scoring vectors")
        errors = [p-y for p, y, keep in zip(predicted, labels, mask) if keep]
        if not errors:
            result["status"] = "insufficient_data"
        else:
            value = math.sqrt(math.fsum(e*e for e in errors)/len(errors))
            if not math.isfinite(value):
                raise ValueError("nonfinite RMSE")
            result.update(status="success", value=value, feasible=True)
    except Exception:
        pass  # Never serialize private values, exceptions or file names.
    print(json.dumps(result, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
