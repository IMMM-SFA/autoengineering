"""Resolve a new routing campaign from saved Part 1 arrays, without rerunning the pilot."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from autoengineering.campaign.artifacts import reference, read_arrays
from autoengineering.campaign.records import DataContract, PortContract, TimeContract
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.spec import (
    AcceptanceSpec,
    BaselineSpec,
    CheckSpec,
    InterventionSpec,
    ProvenanceSpec,
)
from examples.campaign_contracts.build_fixture import fixture
from examples.campaign_contracts.routing import PARAMETERS

ROOT = Path(__file__).resolve().parents[2]
HERE = "examples/campaign_contracts/routing-profile"
LEGACY = "background-research/agentic-architecture"


def build_routing():
    base = ROOT / HERE
    base.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / LEGACY / "baseline/manifest.json").read_text())
    ref = reference(
        ROOT, f"{LEGACY}/baseline/baseline.npz", media_type="application/x-npz", producer="Part1"
    )
    if ref.sha256 != manifest["baseline.npz"]:
        raise ValueError("saved Part 1 driver identity changed")
    arrays = read_arrays(ROOT, ref)
    dates = tuple(str(value) for value in arrays["dates"].astype("datetime64[D]"))
    np.savez(base / "forcing.npz", runoff=arrays["runoff"], recharge=arrays["recharge"])
    for role, mask in (
        ("fitting", (np.asarray(dates) >= "2019-04-01") & (np.asarray(dates) < "2020-01-01")),
        ("comparison", np.asarray(dates) >= "2020-01-01"),
    ):
        np.savez(base / f"{role}.npz", prediction=arrays["observed"][mask])
    spec = fixture()

    def port(name, axis=dates):
        warmup = tuple(value < "2019-04-01" for value in axis)
        time = TimeContract(
            axis,
            "interval_mean",
            "P1D",
            "proleptic_gregorian",
            "start",
            warmup,
            tuple(not value for value in warmup),
        )
        return PortContract(
            name,
            ("time",),
            "mm/day",
            "numeric",
            (),
            "leaf-river-02472000",
            digest(["02472000"]),
            time,
        )

    inputs = (port("runoff"), port("recharge"))
    outputs = (port("prediction"),)
    source_paths = (
        "examples/campaign_contracts/qualify.py",
        "examples/leaf_river/models/__init__.py",
        "examples/campaign_contracts/routing.py",
        "examples/campaign_contracts/build_routing.py",
        "examples/leaf_river/models/routing.py",
        "examples/leaf_river/models/routing_calibrated.py",
        f"{LEGACY}/baseline/baseline.npz",
        f"{LEGACY}/baseline/manifest.json",
        f"{LEGACY}/reference-recovery/evaluation.json",
        f"{LEGACY}/reference-recovery/triangular.npz",
        f"{LEGACY}/reference-recovery/gamma.npz",
    )
    refs = tuple(
        reference(ROOT, path, media_type="application/octet-stream", producer="author")
        for path in source_paths
    )
    sources = (*spec.provenance.sources, *refs)
    system = reference(
        ROOT,
        "examples/campaign_contracts/routing-system.yaml",
        media_type="application/yaml",
        producer="author",
    )
    model = replace(
        spec.baseline.model,
        graph_digest=system.sha256,
        implementations={"response": "triangular-v1"},
        inputs=inputs,
        outputs=outputs,
        source_bundle=sources,
    )
    data = [
        DataContract(
            "forcing",
            reference(
                ROOT, f"{HERE}/forcing.npz", media_type="application/x-npz", producer="author"
            ),
            inputs,
            "forcing",
            "exposed",
        )
    ]
    for role, axis in (
        ("fitting", tuple(value for value in dates if "2019-04-01" <= value < "2020-01-01")),
        ("comparison", tuple(value for value in dates if value >= "2020-01-01")),
    ):
        data.append(
            DataContract(
                role,
                reference(
                    ROOT, f"{HERE}/{role}.npz", media_type="application/x-npz", producer="author"
                ),
                (port("prediction", axis),),
                role,
                "exposed",
            )
        )
    bounds = {
        "uh_peak": (1.0, 8.0),
        "gamma_shape": (1.1, 5.0),
        "gamma_scale": (0.5, 3.0),
        "k_base": (0.5, 0.98),
        "recharge_frac": (0.0, 0.12),
        "uh_length": (10.0, 16.0),
    }
    resolved = replace(
        spec,
        name="routing-reference-v1",
        source_bundle="routing-reference-v1",
        scientific_scope="Routing accounting fixture with saved Part 1 drivers; not a catchment water balance",
        baseline=BaselineSpec(system, model, "routing", PARAMETERS["triangular"]),
        data=tuple(data),
        interventions=(InterventionSpec("response", ("triangular-v1", "gamma-v1"), bounds),),
        acceptance=AcceptanceSpec(
            "rmse",
            "minimize",
            0.01,
            {"kge": 0.02, "bias": 0.05},
            (
                CheckSpec("finite", "1", True, "outputs", {}),
                CheckSpec("routing_accounting", "1", True, "routing", {}),
            ),
        ),
        execution=replace(spec.execution, adapter_ids=("routing",)),
        provenance=ProvenanceSpec(sources, spec.provenance.environment_lock, outputs),
    )
    resolved.to_yaml(base / "campaign.yaml")
    return resolved


if __name__ == "__main__":
    build_routing()
