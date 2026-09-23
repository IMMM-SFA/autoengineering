"""Verify the three open-chain records and generate their results section."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from examples.open_chains.common import digest

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "examples/open_chains"


def verify_release_metadata(name: str, expected: str) -> None:
    """Allow only a version-field change against an exact archived release input."""
    current = REPO / name
    if digest(current) == expected:
        return
    patterns = {
        "pixi.toml": r'(?m)^version = "[^"\n]+"$',
        "src/autoengineering/__init__.py": r'(?m)^__version__ = "[^"\n]+"$',
    }
    assert name in patterns, f"Changed core source: {name}"
    archived = REPO / "examples/open_chains/history/source-sha256" / f"{expected}.txt"
    assert archived.is_file() and digest(archived) == expected, f"Invalid release snapshot: {name}"
    pattern = patterns[name]
    old, new = archived.read_text(), current.read_text()
    assert len(re.findall(pattern, old)) == len(re.findall(pattern, new)) == 1
    assert re.sub(pattern, "VERSION_FIELD", old) == re.sub(pattern, "VERSION_FIELD", new), (
        f"Changed non-version content: {name}"
    )


def verify(domain: str) -> tuple[dict, list, dict]:
    directory = ROOT / "results" / domain
    hashes = json.loads((directory / "artifact-sha256.json").read_text())
    assert "report.md" in hashes
    for name, expected in hashes.items():
        assert digest(directory / name) == expected, f"Changed {domain} artifact: {name}"
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["source_sha256"].items():
        assert digest(ROOT / name) == expected, f"Changed adapter: {name}"
    for name, expected in manifest["core_source_sha256"].items():
        verify_release_metadata(name, expected)
    assert digest(REPO / "pixi.lock") == manifest["pixi_lock_sha256"]
    verify_release_metadata("pixi.toml", manifest["pixi_manifest_sha256"])
    assert not manifest["context"]["smoke"]
    trials = json.loads((directory / "trials.json").read_text())
    candidates = json.loads((ROOT / domain / "candidates.json").read_text())
    assert [row["id"] for row in trials] == ["baseline", *[c["id"] for c in candidates]]
    assert all(row["status"] in {"evaluated", "infeasible"} for row in trials)
    summary = json.loads((directory / "summary.json").read_text())
    valid = [row for row in trials if row["status"] == "evaluated"]
    winner = min(valid, key=lambda r: r["objective"])
    assert winner["id"] == summary["selected"]
    assert winner["objective"] == summary["selected_value"]
    assert trials[0]["objective"] == summary["baseline"]
    assert summary["gain"] == summary["baseline"] - summary["selected_value"]
    assert summary["failed_trials"] == 0
    assert summary["infeasible_trials"] == sum(r["status"] == "infeasible" for r in trials)
    assert json.loads((directory / "selection.json").read_text()) == {
        "id": winner["id"],
        "objective": winner["objective"],
    }
    for row in trials:
        with np.load(directory / f"{row['id']}.npz") as arrays:
            assert all(np.isfinite(value).all() for value in arrays.values())
            if domain == "solar":
                import pandas as pd

                observed = pd.read_csv(directory / "selection-observed.csv")
                error = arrays["ac_kw"] - observed.iloc[:, 1].to_numpy()
                np.testing.assert_allclose(np.sqrt(np.mean(error**2)), row["objective"])
            elif domain == "wind":
                np.testing.assert_allclose(-arrays["aep_gwh"].sum(), row["objective"])
            else:
                from examples.open_chains.hybrid.models import check_physics

                feasible = True
                try:
                    check_physics(dict(arrays))
                except ValueError:
                    feasible = False
                assert feasible == row["metrics"]["feasible"]
                assert row["status"] == ("evaluated" if feasible else "infeasible")
                np.testing.assert_allclose(
                    -(arrays["grid_kw"] * arrays["price"]).sum(), row["objective"]
                )
    if domain == "solar":
        import pandas as pd

        observed = pd.read_csv(directory / "test-observed.csv").iloc[:, 1].to_numpy()
        for name in ["baseline", "selected"]:
            with np.load(directory / f"test-{name}.npz") as arrays:
                error = arrays["ac_kw"] - observed
                np.testing.assert_allclose(
                    np.sqrt(np.mean(error**2)), summary["test"][name + "_rmse_kw"]
                )
    return summary, trials, manifest


def report_lines() -> list[str]:
    records = {domain: verify(domain) for domain in ["solar", "wind", "hybrid"]}
    lines = [
        "",
        "## Independently maintained model chains",
        "",
        "These are finite component-swap comparisons, not extra RMSE domains in the frozen "
        "Bayesian benchmark. All three execute their real upstream software locally. "
        "These fixed candidate lists are independent of the separate 2000-call target experiment.",
        "",
        "| Chain | Selection objective (minimize) | Baseline | Selected | Selection gain | Evaluations | Seconds |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for domain, (summary, trials, _) in records.items():
        lines.append(
            f"| {domain} | {summary['objective']} | {summary['baseline']:.6g} | "
            f"{summary['selected_value']:.6g} | {summary['gain']:.6g} | {len(trials)} | "
            f"{sum(r['seconds'] for r in trials):.3f} |"
        )
    solar = records["solar"][0]
    wind = records["wind"][0]
    hybrid = records["hybrid"][0]
    lines += [
        "",
        f"Solar selected `{solar['selected']}` using 2018. On 2019, AC RMSE changed from "
        f"{solar['test']['baseline_rmse_kw']:.4f} to {solar['test']['selected_rmse_kw']:.4f} kW. "
        "This is conditional on measured POA and the declared jointly observed subset. "
        "Implausible 2019 module-temperature readings invalidate that intermediate diagnostic, "
        "without changing the power score. The test period was inspected during example "
        "development and is a temporal holdout, not blinded external validation.",
        "",
        f"Wind selected `{wind['selected']}`. On the finer five-degree grid, modeled energy "
        f"changed from {wind['test']['baseline_aep_gwh']:.4f} to "
        f"{wind['test']['selected_aep_gwh']:.4f} GWh. The finer-grid gain "
        f"is {wind['test']['gain_gwh']:.4f} GWh. This is a numerical sensitivity check, "
        "not observed plant improvement. Bounded feasible iterates do not establish convergence.",
        "",
        f"Hybrid selected `{hybrid['selected']}`. {hybrid['infeasible_trials']} policy was "
        "excluded by the unchanged numerical/physical screens. Gross revenue omits capital "
        "and degradation costs and terminal SOC value. Perfect 24-hour foresight and a "
        "separate price-year scenario are assumptions, not forecast skill or realized income.",
        "",
        "| Chain | Candidate | Status | Inner optimizer / physical diagnostics |",
        "| --- | --- | --- | --- |",
    ]
    for domain, (_, trials, _) in records.items():
        for row in trials:
            metrics = row["metrics"]
            detail = (
                "See sensor QA and selection/test coverage"
                if domain == "solar"
                else (
                    f"{metrics['inner_termination']}; {metrics['inner_wake_function_calls']} wake function "
                    f"and {metrics['inner_wake_gradient_calls']} gradient evaluations"
                    if domain == "wind"
                    else f"SOC {metrics['minimum_soc_percent']:.3f}-{metrics['maximum_soc_percent']:.3f}%; "
                    f"final {metrics['final_soc_percent']:.3f}%; {metrics['infeasibility'] or 'screen passed'}"
                )
            )
            lines.append(f"| {domain} | {row['id']} | {row['status']} | {detail} |")
    lines += [
        "",
        "Sources, commands, limits and raw evidence are linked from "
        "[the open-chain README](../../open_chains/README.md). Each result includes source, "
        "environment and artifact hashes. Summarization recomputes objectives from saved arrays. "
        "The [older 200-call report](../../complex_models/history/a262556/RESULTS-200.md) is preserved.",
        "",
    ]
    return lines


if __name__ == "__main__":
    (ROOT / "results/RESULTS.md").write_text(
        "# Open model chain results\n" + "\n".join(report_lines())
    )
    print("Verified all three open-chain results")
