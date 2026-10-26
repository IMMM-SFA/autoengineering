"""Fixed Leaf River evaluator. Never imports worker-supplied code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import pandas as pd
import yaml

from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    EvaluationAction,
    EvaluationResult,
    IntegerParameter,
    NoiseSpec,
    ObjectiveSpec,
    ObservationLedger,
    OptimizationStudy,
    SearchSpace,
    SobolBackend,
    StudySpec,
)
from examples.leaf_river.models.pet_hamon import hamon_pet
from examples.leaf_river.models.routing import route_streamflow, triangular_uh
from examples.leaf_river.models.routing_calibrated import route_streamflow_calibrated, gamma_uh
from examples.leaf_river.models.scs_runoff import scs_runoff
from examples.leaf_river.models.soil_moisture import soil_bucket

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "background-research/agentic-architecture"
LEAF = ROOT / "examples/leaf_river"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity() -> dict:
    paths = [
        ROOT / "pixi.lock",
        LEAF / "system.yaml",
        LEAF / "candidates.yaml",
        LEAF / "run_auto_research.py",
        LEAF / "run_workflow.py",
        LEAF / "data/fetch_data.py",
        *sorted((LEAF / "data").glob("*.csv")),
        *sorted((LEAF / "models").glob("*.py")),
        *sorted((ROOT / "src/autoengineering").rglob("*.py")),
        *sorted(Path(__file__).parent.glob("*.py")),
    ]
    task = EVIDENCE / "task.yaml"
    if task.exists():
        paths.append(task)
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def write_json(path: Path, value: object) -> None:
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def load_data() -> pd.DataFrame:
    flow = pd.read_csv(LEAF / "data/streamflow.csv", parse_dates=["date"])
    weather = pd.read_csv(LEAF / "data/weather.csv", parse_dates=["date"])
    expected = pd.date_range("2019-01-01", "2020-12-31")
    for table in (flow, weather):
        if not table.date.equals(pd.Series(expected)) or table.isna().any().any():
            raise ValueError("daily alignment or missing-value contract failed")
    return flow.merge(weather, on="date", validate="one_to_one")


def drivers(data: pd.DataFrame) -> dict[str, np.ndarray]:
    p = data.precip_mm.to_numpy(copy=True)
    pet = hamon_pet(data.tmean_c.to_numpy(copy=True), data.date.dt.dayofyear.to_numpy())
    aet, excess, storage = soil_bucket(p.copy(), pet.copy())
    return dict(
        precip=p,
        pet=pet,
        aet=aet,
        excess=excess,
        storage=storage,
        runoff=scs_runoff(excess.copy()),
        recharge=np.maximum(p - aet, 0),
    )


def metrics(predicted: np.ndarray, observed: np.ndarray) -> dict[str, float]:
    """Independent metric reconstruction, without package validation functions."""
    residual = predicted - observed
    r = float(np.corrcoef(predicted, observed)[0, 1])
    return dict(
        rmse=float(np.sqrt(np.mean(residual**2))),
        bias=float(np.mean(residual)),
        nse=float(1 - np.sum(residual**2) / np.sum((observed - observed.mean()) ** 2)),
        kge=float(
            1
            - np.sqrt(
                (r - 1) ** 2
                + (predicted.std() / observed.std() - 1) ** 2
                + (predicted.mean() / observed.mean() - 1) ** 2
            )
        ),
    )


def route(family: str, parameters: dict, arrays: dict) -> np.ndarray:
    functions = dict(triangular=route_streamflow, gamma=route_streamflow_calibrated)
    return functions[family](
        arrays["runoff"].copy(), precip=arrays["recharge"].copy(), **parameters
    )


def checks(predicted: np.ndarray, family: str, parameters: dict, arrays: dict) -> dict:
    """Executable routing invariants, not a whole-catchment water balance."""
    n = len(arrays["runoff"])
    aligned = isinstance(predicted, np.ndarray) and predicted.shape == (n,)
    finite = aligned and bool(np.isfinite(predicted).all())
    results = dict(
        aligned=aligned, finite=finite, nonnegative=finite and bool((predicted >= -1e-12).all())
    )
    if not finite:
        return results
    if family == "triangular":
        uh = triangular_uh(parameters.get("uh_peak", 3), parameters.get("uh_length", 10))
        k, frac = parameters.get("k_base", 0.85), parameters.get("recharge_frac", 0.10)
    else:
        uh = gamma_uh(
            parameters.get("gamma_shape", 2.5),
            parameters.get("gamma_scale", 1.5),
            parameters.get("uh_length", 15),
        )
        k, frac = parameters.get("k_base", 0.92), parameters.get("recharge_frac", 0.03)
    q_base = np.zeros(n)
    q_base[0] = 0.5
    for i in range(1, n):
        q_base[i] = k * q_base[i - 1] + frac * arrays["recharge"][i]
    full = np.convolve(arrays["runoff"], uh)
    results["normalized_kernel"] = bool(abs(uh.sum() - 1) <= 1e-12)
    results["routing_accounting"] = bool(
        np.allclose(predicted, full[:n] + q_base, atol=1e-10, rtol=1e-10)
    )
    results["tail_accounting"] = bool(abs(full.sum() - arrays["runoff"].sum()) <= 1e-8)
    perturbed = {key: value.copy() for key, value in arrays.items()}
    midpoint = n // 2
    perturbed["runoff"][midpoint:] += 1
    perturbed["recharge"][midpoint:] += 1
    causal = route(family, parameters, perturbed)
    results["causal"] = bool(np.allclose(predicted[:midpoint], causal[:midpoint], atol=1e-12))
    return results


def audit(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    data = load_data()
    arrays = drivers(data)
    before = {k: v.copy() for k, v in arrays.items()}
    baseline = route("triangular", {}, arrays)
    repeated = route("triangular", {}, arrays)
    observed = data.flow_mm_day.to_numpy(copy=True)
    np.savez(
        output / "baseline.npz",
        **arrays,
        predicted=baseline,
        observed=observed,
        dates=data.date.to_numpy(dtype="datetime64[D]"),
    )
    previous = np.r_[50.0, arrays["storage"][:-1]]
    result = dict(
        days=len(data),
        start=str(data.date.iloc[0].date()),
        end=str(data.date.iloc[-1].date()),
        metrics=metrics(baseline, observed),
        deterministic=bool(np.array_equal(baseline, repeated)),
        input_isolation=all(np.array_equal(before[k], v) for k, v in arrays.items()),
        bucket_residual_max=float(
            np.max(
                np.abs(
                    arrays["precip"]
                    - arrays["aet"]
                    - arrays["excess"]
                    - arrays["storage"]
                    + previous
                )
            )
        ),
        checks=checks(baseline, "triangular", {}, arrays),
        conversion_residual_max=float(
            np.max(
                np.abs(
                    data.flow_mm_day.to_numpy()
                    - data.flow_cfs.to_numpy() * 0.0283168 * 86400 / 1947.7 / 1000
                )
            )
        ),
        seconds=time.monotonic() - started,
        environment=dict(
            python=platform.python_version(),
            platform=platform.platform(),
            numpy=np.__version__,
            pandas=pd.__version__,
        ),
        source_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        source_hashes=identity(),
    )
    write_json(output / "audit.json", result)
    write_json(output / "manifest.json", {p.name: digest(p) for p in output.iterdir()})
    return result


def task() -> dict:
    return yaml.safe_load((EVIDENCE / "task.yaml").read_text())


class DefaultThenSobol(SobolBackend):
    """Count the supplied default as the first observation in each family budget."""

    def suggest(self, ledger, n=1):
        if not ledger.entries():
            family = self.spec.name.split("-")[-1]
            config = dict(task()["families"][family]["default"])
            return (
                EvaluationAction.system(
                    "eval-000001", config, seed=self.spec.seed, suggested_by="default_then_sobol"
                ),
            )
        return super().suggest(ledger, n=n)


def calibrate(directory: Path, family: str, hashes: dict) -> dict:
    frozen = task()
    config = frozen["families"][family]
    parameters = []
    for name, bounds in config["bounds"].items():
        cls = IntegerParameter if name == "uh_peak" else ContinuousParameter
        parameters.append(cls(name, *bounds))
    space = SearchSpace(tuple(parameters))
    spec = StudySpec(
        name=f"leaf-routing-{family}",
        objective=ObjectiveSpec("rmse", "minimize"),
        constraints=(),
        budget=BudgetSpec(max_cost=16, cost_unit="attempt", max_evaluations=16),
        noise=NoiseSpec(),
        backend="system",
        seed=frozen["seed"],
    )
    data = load_data()
    # Fitting never loads comparison observations into the objective.
    fitting = data.date.between("2019-04-01", "2019-12-31").to_numpy()
    arrays = drivers(data[data.date < "2020-01-01"])
    observed = data.loc[fitting, "flow_mm_day"].to_numpy(copy=True)
    mask = fitting[: len(arrays["runoff"])]

    def evaluate(action):
        predicted = route(family, dict(action.config), arrays)
        score = metrics(predicted[mask], observed)
        return EvaluationResult.success(action.id, score, {}, 1.0, "attempt")

    directory.mkdir(parents=True, exist_ok=True)
    ledger = ObservationLedger(directory / "observations.jsonl")
    study = OptimizationStudy(
        spec,
        space,
        DefaultThenSobol(spec, space),
        ledger,
        evaluate,
        directory,
        input_artifact_hashes=hashes,
    )
    study.run()
    successful = [(a, r) for a, r in ledger.entries() if r.status.value == "success"]
    best_action, best_result = min(
        successful, key=lambda pair: (pair[1].outcomes["rmse"], pair[0].id)
    )
    return dict(
        parameters=dict(best_action.config),
        fit=dict(best_result.outcomes),
        evaluations=len(ledger.entries()),
        action_id=best_action.id,
    )


def evaluate_choices(directory: Path, hashes: dict) -> dict:
    """One calibration per family, then two comparison and two default evaluations."""
    data = load_data()
    arrays = drivers(data)
    comparison = (data.date >= "2020-01-01").to_numpy()
    observed = data.flow_mm_day.to_numpy(copy=True)[comparison]
    results = {}
    for family in ("triangular", "gamma"):
        selected = calibrate(directory / family, family, hashes)
        predicted = route(family, selected["parameters"], arrays)
        invariants = checks(predicted, family, selected["parameters"], arrays)
        default = route(family, dict(task()["families"][family]["default"]), arrays)
        results[family] = dict(
            **selected,
            comparison=metrics(predicted[comparison], observed),
            default_comparison=metrics(default[comparison], observed),
            checks=invariants,
        )
        np.savez(
            directory / f"{family}.npz",
            predicted=predicted,
            observed=data.flow_mm_day.to_numpy(),
            comparison_mask=comparison,
            dates=data.date.to_numpy(dtype="datetime64[D]"),
        )
    base, candidate = results["triangular"], results["gamma"]
    rules = task()["acceptance"]
    gain = base["comparison"]["rmse"] - candidate["comparison"]["rmse"]
    accept = (
        all(candidate["checks"].values())
        and all(base["checks"].values())
        and gain >= rules["min_rmse_gain"]
        and candidate["comparison"]["kge"] >= base["comparison"]["kge"] - rules["max_kge_loss"]
        and abs(candidate["comparison"]["bias"])
        <= abs(base["comparison"]["bias"]) + rules["max_absolute_bias_increase"]
    )
    return dict(
        families=results,
        decision="retain_gamma" if accept else "retain_triangular",
        rmse_gain=gain,
        scientific_executions=36,
        diagnostic_executions=2,
        total_executions=38,
        scope="engineering_fixture_not_catchment_validation",
    )
