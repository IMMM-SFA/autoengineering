"""Resolve a fresh synthetic campaign with a separate scientific source closure."""

from __future__ import annotations

from dataclasses import replace

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.identity import scientific_source_paths
from examples.campaign_contracts.build_fixture import ROOT, fixture


def agent_fixture():
    original = fixture()
    paths = ("examples/campaign_contracts/fixture_model.py", *scientific_source_paths())
    sources = tuple(
        reference(ROOT, path, media_type="application/octet-stream", producer="author")
        for path in paths
    )
    model = replace(original.baseline.model, source_bundle=sources)
    return replace(
        original,
        name="agent-contract-fixture",
        source_bundle="scientific-core-v1",
        baseline=replace(original.baseline, model=model),
        provenance=replace(original.provenance, sources=sources),
    )
