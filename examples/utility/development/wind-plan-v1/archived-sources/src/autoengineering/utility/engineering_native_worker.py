"""Fixed worker for a trusted registered native engineering driver."""

from __future__ import annotations

import contextlib
import importlib
from pathlib import Path
import sys


def main():
    try:
        from autoengineering.campaign.artifacts import confined_file
        from autoengineering.campaign.serialization import digest, unique_json
        from autoengineering.utility.engineering_process import verify_sources
        from autoengineering.utility.engineering_native import (
            NativeDriverJob,
            NativeDriverResult,
            native_binding,
            validate_native_result,
        )

        path = Path(sys.argv[1]).absolute()
        raw = confined_file(path.parent, path.name).read_bytes()
        if len(raw) > 1048576:
            raise ValueError("native job exceeds size limit")
        job = NativeDriverJob.from_json(raw.decode())
        if Path(job.scratch_path) != path.parent:
            raise ValueError("native scratch path differs")
        saved = unique_json(confined_file(path.parent, "binding.json").read_text())
        if (
            digest(saved) != job.binding_digest
            or digest(native_binding(job.specification, Path(job.source_root)))
            != job.binding_digest
        ):
            raise ValueError("native worker binding differs")
        verify_sources(
            job.specification.execution,
            Path(job.source_root),
            additional_entrypoints=(job.specification.entrypoint,),
        )
    except Exception:
        sys.stderr.write("Native engineering preflight failed\n")
        return 2
    try:
        sys.path.insert(0, job.source_root)
        module, name = job.specification.entrypoint.split(":")
        with contextlib.redirect_stdout(sys.stderr):
            result = getattr(importlib.import_module(module), name)(job)
        if not isinstance(result, NativeDriverResult):
            raise ValueError("native result type differs")
        validate_native_result(job.specification, job, result)
        sys.stdout.write(result.to_json())
        return 0
    except Exception:
        sys.stderr.write("Supplied native engineering execution failed\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
