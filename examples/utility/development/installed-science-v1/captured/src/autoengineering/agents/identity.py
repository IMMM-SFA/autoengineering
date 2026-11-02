"""Host source and runtime identities, separate from scientific source bundles."""

from __future__ import annotations

import hashlib
from pathlib import Path
import platform
import sys

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import digest


def host_source_identity() -> str:
    root = Path(__file__).resolve().parent
    paths = sorted((*root.rglob("*.py"), *root.joinpath("prompts").glob("*.txt")))
    manifest = {}
    for path in paths:
        name = str(path.relative_to(root))
        manifest[name] = hashlib.sha256(confined_file(root, name).read_bytes()).hexdigest()
    return digest({"schema_version": "1.0", "sources": manifest})


def host_environment_identity() -> str:
    # The host adapter uses Python's standard library. Scientific dependencies
    # and lockfile identity are verified by the campaign controller separately.
    return digest(
        {
            "schema_version": "1.0",
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": sys.platform,
            "machine": platform.machine(),
        }
    )
