"""Read and verify a caller-supplied existing OEDI cache; never fetch data."""
from __future__ import annotations

import json
from pathlib import Path

from examples.open_chains.common import verify_file
from examples.open_chains.solar.run_workflow import load_data

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parents[1] / "open_chains/solar/sources.json"


def load(cache_directory):
    cache = Path(cache_directory)
    sources = json.loads(SOURCES.read_text())["files"]
    for item in sources:
        path = cache / item["name"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("solar cache must contain existing regular files")
        verify_file(path, item)
    protocol = json.loads((HERE / "protocol.json").read_text())
    data, coverage = load_data(*protocol["window"], cache_directory=cache)
    return data, {"sources": sources, "coverage": coverage,
                  "exposure": "previously_exposed_development",
                  "confirmation": "not_attempted", "cache_access": "verified_read_only"}
