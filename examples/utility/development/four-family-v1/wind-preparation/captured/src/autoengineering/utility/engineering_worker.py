"""One trusted engineering scenario. No private labels or generated code."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main():
    # These fixed exit codes distinguish preflight/infrastructure failure from
    # supplied-code failure without exposing exception payloads in public scores.
    try:
        from autoengineering.campaign.artifacts import confined_file
        from autoengineering.campaign.serialization import digest, unique_json
        from autoengineering.utility.engineering_process import (
            EngineeringScenarioJob, EngineeringScenarioResult, verify_sources, runtime_binding,
        )
        path = Path(sys.argv[1]).absolute()
        raw = confined_file(path.parent, path.name).read_bytes()
        if len(raw) > 1048576:
            raise ValueError("engineering job exceeds size limit")
        job = EngineeringScenarioJob.from_json(raw.decode())
        if Path(job.scratch_path) != path.parent:
            raise ValueError("engineering scratch path differs from owned scenario directory")
        saved = unique_json(confined_file(path.parent.parent, "execution.json").read_text())
        if digest(saved) != job.binding_digest or digest(runtime_binding(job.execution, Path(job.source_root))) != job.binding_digest:
            raise ValueError("engineering process environment differs from frozen binding")
        verify_sources(job.execution, Path(job.source_root))
    except Exception:
        sys.stderr.write("Engineering preflight failed\n")
        return 2
    try:
        sys.path.insert(0, job.source_root)
        module, name = job.execution.entrypoint.split(":")
        result = getattr(importlib.import_module(module), name)(job)
        if not isinstance(result, EngineeringScenarioResult) or result.job_digest != job.digest:
            raise ValueError("engineering evaluator returned an invalid result")
        sys.stdout.write(result.to_json())
        return 0
    except Exception:
        sys.stderr.write("Supplied engineering execution failed\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
