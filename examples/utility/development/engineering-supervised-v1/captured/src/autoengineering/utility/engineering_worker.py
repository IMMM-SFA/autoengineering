"""One trusted engineering scenario. No private labels or generated code."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from autoengineering.campaign.artifacts import confined_file
from autoengineering.utility.engineering_process import (
    EngineeringScenarioJob, EngineeringScenarioResult, verify_sources,
)


def main():
    path = Path(sys.argv[1]).absolute()
    raw = confined_file(path.parent, path.name).read_bytes()
    if len(raw) > 1048576:
        raise ValueError("engineering job exceeds size limit")
    job = EngineeringScenarioJob.from_json(raw.decode())
    if Path(job.scratch_path) != path.parent:
        raise ValueError("engineering scratch path differs from owned scenario directory")
    verify_sources(job.execution, Path(job.source_root))
    sys.path.insert(0, job.source_root)
    module, name = job.execution.entrypoint.split(":")
    result = getattr(importlib.import_module(module), name)(job)
    if not isinstance(result, EngineeringScenarioResult) or result.job_digest != job.digest:
        raise ValueError("engineering evaluator returned an invalid result")
    sys.stdout.write(result.to_json())


if __name__ == "__main__":
    main()
