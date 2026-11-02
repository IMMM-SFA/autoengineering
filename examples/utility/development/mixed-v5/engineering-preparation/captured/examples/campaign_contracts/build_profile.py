"""Audit the exposed cache and resolve the Part 2 hydrology development profile.

This prepares input artifacts and contracts without running a scientific model.
Regenerate during implementation, then freeze before the first new comparison.
"""

from __future__ import annotations

from dataclasses import replace

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import DataContract, ModelSnapshot, PortContract, TimeContract
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.spec import (
    AcceptanceSpec,
    BaselineSpec,
    CalibrationSpec,
    CampaignSpec,
    CheckSpec,
    ConfirmationSpec,
    ExecutionSpec,
    InterventionSpec,
    ProvenanceSpec,
    WorkflowSpec,
)
from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)
from examples.campaign_contracts.hydrology import SOURCES

ROOT = Path(__file__).resolve().parents[2]
HERE = "examples/campaign_contracts"
DATA = ROOT / "examples/local_models/data"


def audit_cache() -> pd.DataFrame:
    table = pd.read_csv(DATA / "hydro.csv")
    expected = pd.date_range("2019-01-01", "2020-12-31")
    if not pd.to_datetime(table.date).equals(pd.Series(expected)):
        raise ValueError("cache timestamps differ from the historical daily profile")
    if table.isna().any().any() or not np.isfinite(table.select_dtypes("number")).all().all():
        raise ValueError("cache contains missing or nonfinite values")
    dates = pd.to_datetime(table.date)
    labels = np.select(
        [dates < "2019-04-01", dates < "2019-10-01", dates < "2020-01-01"],
        ["warmup", "train", "validation"],
        default="test",
    )
    if not np.array_equal(labels, table.split.to_numpy()):
        raise ValueError("historical split labels changed")
    if (table.precip_mm < 0).any() or (table.flow_mm_day < 0).any():
        raise ValueError("negative precipitation or observed flow")
    if not ((table.tmin_c <= table.tmean_c) & (table.tmean_c <= table.tmax_c)).all():
        raise ValueError("temperature ordering failed")
    provenance = json.loads((DATA / "sources.json").read_text())["hydro"]
    for path, expected_hash in provenance["source_files"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected_hash:
            raise ValueError("legacy cache source identity changed")
    weather = pd.read_csv(ROOT / "examples/leaf_river/data/weather.csv")
    flow = pd.read_csv(ROOT / "examples/leaf_river/data/streamflow.csv")
    for column in ("precip_mm", "tmin_c", "tmax_c", "tmean_c"):
        np.testing.assert_allclose(table[column], weather[column], rtol=0, atol=1e-10)
    # Existing preparation converts cfs to mm/day using the 1,947.7 km2 basin area.
    np.testing.assert_allclose(
        table.flow_mm_day,
        table.flow_cfs * 0.0283168 * 86400 / (1947.7e6) * 1000,
        rtol=1e-11,
        atol=1e-9,
    )
    np.testing.assert_allclose(table.flow_cfs, flow.flow_cfs, rtol=0, atol=0)
    return table


def build_profile() -> CampaignSpec:
    table = audit_cache()
    development = table[table.date < "2020-01-01"].copy()
    base = ROOT / HERE / "profile"
    base.mkdir(exist_ok=True)
    forcing = {
        name: development[name].to_numpy(copy=True)
        for name in ("precip_mm", "tmean_c", "tmax_c", "tmin_c")
    }
    forcing["day_of_year"] = pd.to_datetime(development.date).dt.dayofyear.to_numpy()
    np.savez(base / "forcing.npz", **forcing)
    for role, label in (("fitting", "train"), ("comparison", "validation")):
        np.savez(
            base / f"{role}.npz",
            prediction=development.loc[development.split == label, "flow_mm_day"].to_numpy(),
        )

    def ref(path, media=None):
        media = media or {
            ".py": "text/x-python",
            ".json": "application/json",
            ".csv": "text/csv",
        }.get(Path(path).suffix, "application/octet-stream")
        return reference(ROOT, path, media_type=media, producer="profile-author")

    # Explicit broad closure for the supplied local adapters and acceptance package.
    source_paths = sorted(
        {
            *SOURCES,
            f"{HERE}/build_profile.py",
            "examples/local_models/kernels.py",
            *(str(path.relative_to(ROOT)) for path in (ROOT / HERE).glob("*.py")),
            "examples/local_models/__init__.py",
            "examples/local_models/data/sources.json",
            "examples/local_models/data/preparation.json",
            "examples/local_models/data/hydro.csv",
            "examples/leaf_river/data/fetch_data.py",
            *(str(path.relative_to(ROOT)) for path in (ROOT / "src/autoengineering").rglob("*.py")),
        }
    )
    sources = tuple(ref(path) for path in source_paths)
    lock = ref("pixi.lock", "text/plain")
    system = ref(f"{HERE}/hydrology-system.yaml", "application/yaml")

    def time_contract(frame, semantics):
        return TimeContract(
            tuple(frame.date),
            semantics,
            "P1D",
            "proleptic_gregorian",
            "start",
            tuple(frame.split == "warmup"),
            tuple(frame.split != "warmup"),
        )

    def port(name, units, semantics="interval_mean", frame=development, scalar=False):
        return PortContract(
            name,
            () if scalar else ("time",),
            units,
            "numeric",
            (),
            "leaf-river-02472000",
            digest(["02472000", 1947.7]),
            None
            if scalar
            else replace(
                time_contract(frame, semantics),
                timestamp="end" if name in ("soil", "reservoir") else "start",
            ),
        )

    inputs = tuple(
        port(name, unit, kind)
        for name, unit, kind in (
            ("precip_mm", "mm", "interval_total"),
            ("tmean_c", "degC", "interval_mean"),
            ("tmax_c", "degC", "instantaneous"),
            ("tmin_c", "degC", "instantaneous"),
            ("day_of_year", "day", "instantaneous"),
        )
    )
    outputs = tuple(
        port(name, unit, semantics)
        for name, unit, semantics in (
            ("prediction", "mm/day", "interval_mean"),
            ("soil", "mm", "instantaneous"),
            ("reservoir", "mm", "instantaneous"),
            ("aet", "mm/day", "interval_mean"),
            ("pet", "mm/day", "interval_mean"),
        )
    ) + tuple(port(name, "mm", scalar=True) for name in ("initial_soil", "initial_reservoir"))
    model = ModelSnapshot(
        system.sha256,
        {"pet": "hamon-v1", "soil": "bucket-v1", "routing": "linear-v1"},
        sources,
        lock.sha256,
        inputs,
        outputs,
    )
    data = [
        DataContract(
            "forcing",
            ref(f"{HERE}/profile/forcing.npz", "application/x-npz"),
            inputs,
            "forcing",
            "exposed",
        )
    ]
    for role, label in (("fitting", "train"), ("comparison", "validation")):
        frame = development[development.split == label]
        data.append(
            DataContract(
                role,
                ref(f"{HERE}/profile/{role}.npz", "application/x-npz"),
                (port("prediction", "mm/day", frame=frame),),
                role,
                "exposed",
            )
        )
    space = SearchSpace(
        (ContinuousParameter("capacity", 20, 200), ContinuousParameter("recession", 0.05, 0.95))
    )
    run = OptimizationRunSpec(
        StudySpec(
            "hydrology-fitting",
            ObjectiveSpec("rmse", "minimize"),
            (),
            BudgetSpec(16, "physical_executions", 16),
            NoiseSpec(),
            "system",
            17,
        ),
        space,
        "sobol",
        {},
        "autoengineering.campaign.studies:campaign_evaluator",
    )
    checks = tuple(
        CheckSpec(name, "1", True, scope, {})
        for name, scope in (
            ("finite", "outputs"),
            ("nonnegative", "whole_model"),
            ("soil_capacity", "whole_model"),
            ("daily_balance", "whole_model"),
        )
    )
    spec = CampaignSpec(
        "1.0",
        "hydrology-development-v1",
        "Exposed Leaf River development case with explicit daily water balance",
        17,
        "hydrology-development-v1",
        BaselineSpec(
            system, model, "hydrology", {"pet": "hamon", "capacity": 100.0, "recession": 0.7}
        ),
        tuple(data),
        (
            InterventionSpec(
                "pet",
                ("hamon-v1", "hargreaves-v1"),
                {"capacity": (20.0, 200.0), "recession": (0.05, 0.95)},
            ),
        ),
        AcceptanceSpec("rmse", "minimize", 0.01, {"kge": 0.02, "bias": 0.05}, checks),
        CalibrationSpec(run, "fitting"),
        WorkflowSpec(),
        ExecutionSpec(("hydrology",), diagnostics="causal_future_forcing_v1"),
        ConfirmationSpec("disabled"),
        ProvenanceSpec(sources, lock, outputs),
    )
    spec.to_yaml(base / "campaign.yaml")
    (base / "audit.json").write_text(
        canonical_json(
            {
                "cache_sha256": hashlib.sha256((DATA / "hydro.csv").read_bytes()).hexdigest(),
                "historical_split_counts": table.split.value_counts().to_dict(),
                "period": [table.date.iloc[0], table.date.iloc[-1]],
                "missing_values": 0,
                "units": {
                    "precip_mm": "mm daily total",
                    "flow_mm_day": "mm/day daily mean",
                    "temperature": "degC",
                },
                "exposure": "All 2019 and 2020 observations have been exposed historically",
                "confirmation": "disabled",
                "real_model_executions": 0,
                "profile_status": "resolved during implementation; freeze before qualification",
                "planned_executions": {
                    "defaults": 2,
                    "fitting": 32,
                    "selected_comparison": 2,
                    "causality": 2,
                    "total": 38,
                },
                "metadata_limit": "Original HTTP responses and quality flags are absent from the legacy cache",
            }
        )
        + "\n"
    )
    return spec


if __name__ == "__main__":
    build_profile()
