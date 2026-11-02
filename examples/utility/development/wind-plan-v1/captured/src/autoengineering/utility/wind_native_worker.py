"""Fixed bootstrap verifies a wind source closure before importing supplied code."""

from __future__ import annotations

import contextlib
import importlib
from pathlib import Path
import sys


def main():
    try:
        from autoengineering.campaign.artifacts import confined_file
        from autoengineering.campaign.serialization import digest, unique_json
        from autoengineering.utility.engineering_process import (
            EngineeringExecutionSpec,
            verify_sources,
        )

        path = Path(sys.argv[1]).absolute()
        raw = confined_file(path.parent, path.name).read_bytes()
        if len(raw) > 1048576:
            raise ValueError("wind job exceeds size limit")
        document = unique_json(raw.decode())
        source_root = Path(document["source_root"])
        execution = EngineeringExecutionSpec.from_dict(document["specification"]["execution"])
        verify_sources(
            execution,
            source_root,
            additional_entrypoints=(
                document["specification"]["entrypoint"],
                "examples.utility.wind_process:run_driver",
            ),
        )
        sys.path.insert(0, str(source_root))
        from examples.utility.wind_process import (
            WindDriverJob,
            WindDriverResult,
            validate_result,
            verify_wind_sources,
            wind_binding,
        )

        job = WindDriverJob.from_json(raw.decode())
        if Path(job.scratch_path) != path.parent:
            raise ValueError("wind scratch path differs")
        saved = unique_json(confined_file(path.parent, "binding.json").read_text())
        if (
            digest(saved) != job.binding_digest
            or digest(wind_binding(job.specification, source_root)) != job.binding_digest
        ):
            raise ValueError("wind worker binding differs")
        verify_wind_sources(job.specification, source_root)
    except Exception:
        sys.stderr.write("Wind native preflight failed\n")
        return 2
    try:
        module, name = job.specification.entrypoint.split(":")
        with contextlib.redirect_stdout(sys.stderr):
            result = getattr(importlib.import_module(module), name)(job)
        if not isinstance(result, WindDriverResult):
            raise ValueError("wind driver result type differs")
        validate_result(job, result)
        sys.stdout.write(result.to_json())
        return 0
    except Exception:
        sys.stderr.write("Supplied wind native execution failed\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
