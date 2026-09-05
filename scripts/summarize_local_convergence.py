"""Audit and report the fixed extension and prospective BMI target comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import median, mean

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "examples/local_models/results"
METHODS = ["random", "sobol", "bo"]
DOMAINS = ["hydro", "solar", "copper"]


def read(path: Path):
    return json.loads(path.read_text())


def entries(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def checked_runs(directory: Path) -> list[dict]:
    manifest = read(directory / "manifest.json")
    for name, digest in manifest["inputs"].items():
        path = REPO / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            archived = directory / "source" / name
            assert archived.is_file(), f"Unarchived changed source: {name}"
            assert hashlib.sha256(archived.read_bytes()).hexdigest() == digest, name
    rows = read(directory / "results.json")["runs"]
    expected = {
        (d, m, s)
        for d in manifest["domains"]
        for m in manifest["methods"]
        for s in manifest["seeds"]
    }
    assert len(rows) == len(expected)
    assert {(r["domain"], r["method"], r["seed"]) for r in rows} == expected
    for row in rows:
        study = directory / f"{row['domain']}-{row['method']}-{row['seed']}"
        assert read(study / "application-result.json") == row
        assert read(study / "frozen-recommendation.json") == row["recommendation"]
        ledger = entries(study / "observations.jsonl")
        assert len(ledger) == row["evaluations"]
        if manifest["mode"] == "fixed":
            assert len(ledger) == 24
            original = entries(ROOT / "bmi-development" / study.name / "observations.jsonl")
            assert ledger[:12] == original, f"Changed prefix: {study.name}"
        else:
            target = manifest["targets"]["targets"][row["domain"]]
            assert target == row["target"]
            first = next(
                (
                    i + 1
                    for i, entry in enumerate(ledger)
                    if entry["result"]["status"] == "success"
                    and entry["result"]["outcomes"]["rmse"] <= target
                ),
                None,
            )
            assert row["target_reached"] == (first is not None)
            assert first is None or first == len(ledger)
            assert len(ledger) <= row["cap"] == 60
            if first is not None:
                assert row["stop_reason"] == "target_reached"
            elif row["stop_reason"] == "evaluation_cap":
                assert len(ledger) == row["cap"]
            else:
                assert row["stop_reason"] not in {"target_reached", "", None}
                assert len(ledger) < row["cap"]
            assert read(study / "trajectory.json") == row["trajectory"]
            best = None
            prior_seconds = prior_model = 0.0
            for i, (entry, step) in enumerate(zip(ledger, row["trajectory"], strict=True)):
                value = entry["result"]["outcomes"].get("rmse")
                if entry["result"]["status"] == "success":
                    best = value if best is None else min(best, value)
                assert step["evaluations"] == i + 1
                assert step["best_validation_rmse"] == best
                assert step["target_reached"] == (best is not None and best <= target)
                assert step["study_seconds"] >= prior_seconds
                assert step["model_seconds"] >= prior_model
                assert step["study_seconds"] >= step["model_seconds"]
                prior_seconds, prior_model = step["study_seconds"], step["model_seconds"]
    return rows


def number(value) -> str:
    return "NA" if value is None else f"{value:.6f}"


def test_median(rows: list[dict]) -> str:
    values = [r["test"]["rmse"] for r in rows if r["test"] is not None]
    return number(median(values)) if len(values) == len(rows) else "NA (missing test results)"


def main() -> None:
    fixed = checked_runs(ROOT / "extended-fixed")
    target = checked_runs(ROOT / "convergence-target")
    original = read(ROOT / "bmi-development/results.json")["runs"]
    targets = read(REPO / "examples/local_models/convergence-targets.json")
    observed = {}
    for name, digest in targets["source_ledger_sha256"].items():
        path = REPO / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        domain = path.parent.name.split("-")[0]
        for entry in entries(path):
            if entry["result"]["status"] == "success":
                value = entry["result"]["outcomes"]["rmse"]
                observed[domain] = min(observed.get(domain, float("inf")), value)
    assert observed == targets["historical_best_validation_rmse"]
    assert targets["targets"] == {d: 1.05 * v for d, v in observed.items()}
    assert all(
        r["evaluations"] <= 4 for r in target if r["domain"] == "solar" and r["method"] == "bo"
    )
    assert all(
        r["target_reached"] == (r["method"] == "bo") for r in target if r["domain"] == "hydro"
    )
    lines = [
        "# Extended BMI search results",
        "",
        f"Fixed comparison: {len(fixed)} studies, {sum(r['evaluations'] for r in fixed)} calls. "
        f"Target comparison: {len(target)} studies, {sum(r['evaluations'] for r in target)} calls.",
        "",
        "## 12 versus 24 complete-model evaluations",
        "",
        "Median RMSE across the same three seeds. Lower is better. All 27 extended runs "
        "reproduce their original first 12 ledger entries exactly. Test results are computed "
        "only after validation selects the recommendation.",
        "",
        "| Domain | Method | Validation at 12 | Validation at 24 | Test at 12 | Test at 24 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for domain in DOMAINS:
        for method in METHODS:
            old = [r for r in original if (r["domain"], r["method"]) == (domain, method)]
            new = [r for r in fixed if (r["domain"], r["method"]) == (domain, method)]
            values = [
                median(r["recommendation"]["outcomes"]["rmse"] for r in old),
                median(r["recommendation"]["outcomes"]["rmse"] for r in new),
                median(r["test"]["rmse"] for r in old),
                median(r["test"]["rmse"] for r in new),
            ]
            lines.append(
                f"| {domain} | {method} | " + " | ".join(f"{v:.6f}" for v in values) + " |"
            )
    lines += [
        "",
        "## Evaluations to a frozen validation target",
        "",
        "Targets are 1.05 times the lowest original validation RMSE, pooled across all methods. "
        "Five new seeds (3-7) are used. The limit is 60 calls, including initialization. "
        "This measures time to a quality target, not convergence to a global optimum.",
        "",
        "| Domain | Target RMSE | Method | Reached | Calls, seeds 3-7 | Median calls among successes | Mean calls consumed | Median study seconds, all runs | Median test RMSE, all runs |",
        "| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for domain in DOMAINS:
        for method in METHODS:
            group = sorted(
                [r for r in target if (r["domain"], r["method"]) == (domain, method)],
                key=lambda r: r["seed"],
            )
            hits = [r for r in group if r["target_reached"]]
            calls = ", ".join(
                str(r["evaluations"])
                if r["target_reached"]
                else (
                    ">60"
                    if r["stop_reason"] == "evaluation_cap"
                    else f"stopped@{r['evaluations']}:{r['stop_reason']}"
                )
                for r in group
            )
            success_median = f"{median(r['evaluations'] for r in hits):g}" if hits else "NA"
            lines.append(
                f"| {domain} | {targets['targets'][domain]:.6f} | {method} | {len(hits)}/5 | "
                f"{calls} | {success_median} | {mean(r['evaluations'] for r in group):.1f} | "
                f"{median(r['study_seconds'] for r in group):.3f} | "
                f"{test_median(group)} |"
            )
    lines += [
        "",
        "A >60 entry is censored: the target was not reached within the budget. "
        "Median successful calls exclude those runs and must be read alongside the success "
        "fraction. Mean calls consumed includes caps and is a restricted computational cost, "
        "not an estimated mean time to eventual success. Unequal success rates prevent a "
        "standalone ranking by that mean. Backend termination is labeled separately with its actual "
        "horizon. Missing test results are shown as NA, not silently dropped.",
        "",
        "## Interpretation",
        "",
        "Hydrology shows a clear validation-search benefit for BO at this frozen target: "
        "every BO run succeeds, while random and Sobol exhaust the cap. However, the BO "
        "recommendations have worse median held-out RMSE than either baseline. Efficient "
        "validation optimization is distinct from better generalization.",
        "",
        "Every solar BO run stops within its four initial Sobol points. This target does "
        "not exercise adaptive BO on solar. Copper targets are also usually reached quickly, "
        "with only a small difference in consumed calls. Future more demanding targets would "
        "need a separate protocol; these targets were not changed after seeing the outcomes.",
        "",
        "## Timing and expensive-model implications",
        "",
        "Study seconds include optimizer and durable controller work. Model seconds measure "
        "BMI evaluations. Imports, input loading, backend construction and held-out scoring "
        "are excluded. Runs are sequential with rotated method order and one Torch CPU thread. "
        "Target mode also checks a recommendation after each call, so compare timing within "
        "each experiment. The fixed extension first solar study includes a lazy pvlib import; "
        "target runs preimport pvlib. These are single-machine measurements, not repeated timing trials.",
        "",
        "| Domain | Method | Median model seconds | Median optimizer/controller seconds |",
        "| --- | --- | ---: | ---: |",
    ]
    for domain in DOMAINS:
        for method in METHODS:
            group = [r for r in target if (r["domain"], r["method"]) == (domain, method)]
            lines.append(
                f"| {domain} | {method} | {median(r['model_seconds'] for r in group):.4f} | "
                f"{median(r['controller_and_optimizer_seconds'] for r in group):.4f} |"
            )
    lines += [
        "",
        "For a hypothetical constant model cost C, study time is approximately N*C + H, "
        "where N is calls and H is optimizer/controller overhead. When BO reaches the same "
        "target in fewer calls, its break-even cost against another method is "
        "(H_BO - H_other)/(N_other - N_BO), floored at zero. This projection assumes unchanged "
        "search trajectories and overhead. It is not a measurement on a more complex model. "
        "Fewer evaluations cannot be claimed when BO uses more calls or fails to hit the target.",
        "",
        "## Individual target runs",
        "",
        "| Domain | Method | Seed | Status | Calls | Validation RMSE | Test RMSE | Model seconds | Study seconds |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in target:
        lines.append(
            f"| {r['domain']} | {r['method']} | {r['seed']} | {r['stop_reason']} | "
            f"{r['evaluations']} | {number(r['recommendation']['outcomes'].get('rmse'))} | "
            f"{number((r['test'] or {}).get('rmse'))} | {r['model_seconds']:.4f} | {r['study_seconds']:.4f} |"
        )
    lines += [
        "",
        "## Evidence and limits",
        "",
        "Raw evidence is in extended-fixed/ and convergence-target/. Both include manifests, "
        "ledgers and frozen recommendations. Target trajectories retain cumulative costs. "
        "Targets and source ledger hashes are in ../convergence-targets.json. "
        "The report generator checks source hashes, full study matrices, exact paired prefixes, "
        "earliest crossings and trajectory accounting. Separate audit JSON files recalculate "
        "every model objective and held-out recommendation.",
        "",
        "These remain three small BMI applications with short or limited validation data. "
        "The targets are informed by earlier development runs, and five seeds provide limited "
        "precision. More optimization can improve validation while worsening held-out error. "
        "Hydrology cache quality flags, solar allocation assumptions, and copper's unresolved "
        "unit multiplier remain as documented in ../README.md. Application partial BO is "
        "still untested. No algorithm settings or target thresholds were tuned after results.",
        "",
    ]
    (ROOT / "CONVERGENCE_RESULTS.md").write_text("\n".join(lines))
    print(f"Verified {len(fixed) + len(target)} studies and generated CONVERGENCE_RESULTS.md")


if __name__ == "__main__":
    main()
