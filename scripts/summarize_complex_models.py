"""Verify matrices, historical prefixes and stopping, then report larger BMI searches."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import median, mean

from examples.complex_models.models import DOMAINS, ROOT
from examples.complex_models.run import CHECKPOINTS, METHODS

RESULTS = ROOT / "results"
REPO = ROOT.parents[1]


def read(path: Path):
    return json.loads(path.read_text())


def entries(path: Path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def comparable(row: dict) -> dict:
    return {
        "action": row["action"],
        "status": row["result"]["status"],
        "outcomes": row["result"]["outcomes"],
    }


def verify(directory: Path) -> tuple[list, int]:
    manifest = read(directory / "manifest.json")
    for name, digest in manifest["inputs"].items():
        path = REPO / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            # Only diagnostic code and its QA documentation changed after primary runs.
            assert name in {
                "examples/complex_models/workflow.py",
                "examples/complex_models/README.md",
            }, name
            path = directory / "source" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    rows = read(directory / "results.json")["runs"]
    expected = {(d, m, s) for d in DOMAINS for m in METHODS for s in manifest["seeds"]}
    assert len(rows) == len(expected)
    assert {(r["domain"], r["method"], r["seed"]) for r in rows} == expected
    prefixes = 0
    for row in rows:
        name = f"{row['domain']}-{row['method']}-{row['seed']}"
        directory_run = directory / name
        assert read(directory_run / "application-result.json") == row
        assert read(directory_run / "frozen-recommendation.json") == row["recommendation"]
        ledger = entries(directory_run / "observations.jsonl")
        assert len(ledger) == row["evaluations"] <= row["cap"] == manifest["cap"]
        assert read(directory_run / "trajectory.json") == row["trajectory"]
        best = None
        prev_seconds = prev_model = 0.0
        for i, (entry, step) in enumerate(zip(ledger, row["trajectory"], strict=True)):
            if entry["result"]["status"] == "success":
                value = entry["result"]["outcomes"]["rmse"]
                best = value if best is None else min(best, value)
            assert step["evaluations"] == i + 1 and step["best_validation_rmse"] == best
            assert step["study_seconds"] >= prev_seconds and step["model_seconds"] >= prev_model
            assert step["study_seconds"] >= step["model_seconds"]
            prev_seconds, prev_model = step["study_seconds"], step["model_seconds"]
        if manifest["mode"] == "fixed":
            assert row["evaluations"] == 96
            assert [s["evaluations"] for s in row["checkpoints"]] == list(CHECKPOINTS)
            for snap in row["checkpoints"]:
                assert read(directory_run / f"frozen-{snap['evaluations']}.json") == {
                    k: v for k, v in snap.items() if k != "test"
                }
            history = (
                ROOT.parent / "local_models/results/extended-fixed" / name / "observations.jsonl"
            )
        else:
            target = manifest["targets"]["targets"][row["domain"]]
            assert target == row["target"]
            first = next(
                (
                    i + 1
                    for i, e in enumerate(ledger)
                    if e["result"]["status"] == "success"
                    and e["result"]["outcomes"]["rmse"] <= target
                ),
                None,
            )
            assert row["target_reached"] == (first is not None)
            if first:
                assert first == len(ledger) and row["stop_reason"] == "target_reached"
            elif row["stop_reason"] == "evaluation_cap":
                assert len(ledger) == 200
            else:
                assert len(ledger) < 200 and row["stop_reason"] not in ["target_reached", "", None]
            for step in row["trajectory"]:
                expected_hit = (
                    step["best_validation_rmse"] is not None
                    and step["best_validation_rmse"] <= target
                )
                assert step["target_reached"] == expected_hit
            history = (
                ROOT.parent
                / "local_models/results/convergence-target"
                / name
                / "observations.jsonl"
            )
        if row["domain"] in ["hydro", "solar", "copper"]:
            assert history.exists(), f"Missing required historical ledger: {history}"
            old = entries(history)
            assert [comparable(e) for e in ledger[: len(old)]] == [comparable(e) for e in old], name
            prefixes += 1
    return rows, prefixes


def format_number(value, precision=4):
    return "NA" if value is None else f"{value:.{precision}f}"


def median_metric(rows, field):
    vals = [r[field]["rmse"] for r in rows if r[field] is not None]
    return format_number(median(vals)) if len(vals) == len(rows) else "NA (missing scores)"


def median_validation(rows):
    values = [r["recommendation"]["outcomes"].get("rmse") for r in rows]
    return (
        "NA (missing scores)" if any(v is None for v in values) else format_number(median(values))
    )


def main() -> None:
    fixed, nfixed = verify(RESULTS / "fixed")
    target, ntarget = verify(RESULTS / "target")
    assert nfixed == 27 and ntarget == 45
    for mode, rows in [("fixed", fixed), ("target", target)]:
        audit = read(RESULTS / f"{mode}-audit.json")
        assert (
            audit["results_sha256"]
            == hashlib.sha256((RESULTS / mode / "results.json").read_bytes()).hexdigest()
        )
        assert (
            audit["source_sha256"]
            == hashlib.sha256((REPO / "scripts/audit_complex_models.py").read_bytes()).hexdigest()
        )
        assert audit["attempts"] == sum(r["evaluations"] for r in rows)
        expected_recs = sum(
            sum(s["recommendation"]["action_id"] is not None for s in r["checkpoints"])
            + (r["recommendation"]["action_id"] is not None)
            for r in rows
        )
        assert audit["recommendations_recalculated"] == expected_recs
        expected_hashes = {}
        for row in rows:
            name = f"{row['domain']}-{row['method']}-{row['seed']}"
            expected_hashes[name] = hashlib.sha256(
                (RESULTS / mode / name / "observations.jsonl").read_bytes()
            ).hexdigest()
        assert audit["ledger_sha256"] == expected_hashes
    frozen = read(RESULTS / "targets.json")
    old = read(ROOT.parent / "local_models/convergence-targets.json")["targets"]
    assert all(frozen["targets"][d] == v for d, v in old.items())
    for name, digest in frozen["source_sha256"].items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest
    for d in ["hymod", "solar_diode"]:
        vals = [
            e["result"]["outcomes"]["rmse"]
            for p in (RESULTS / "fixed").glob(f"{d}-*/observations.jsonl")
            for e in entries(p)
            if e["result"]["status"] == "success"
        ]
        assert frozen["targets"][d] == 1.05 * min(vals)
    quality = read(RESULTS / "data-quality.json")
    assert (
        quality["source_sha256"]
        == hashlib.sha256((REPO / "scripts/check_complex_data_quality.py").read_bytes()).hexdigest()
    )
    assert (
        quality["data_sha256"]
        == hashlib.sha256((REPO / quality["data_path"]).read_bytes()).hexdigest()
    )
    lines = [
        "# Larger BMI models: 96-call checkpoints and 200-call targets",
        "",
        f"Completed {len(fixed)} fixed studies ({sum(r['evaluations'] for r in fixed)} calls) and "
        f"{len(target)} target studies ({sum(r['evaluations'] for r in target)} calls). "
        f"Verified {nfixed} historical fixed prefixes and {ntarget} historical target prefixes.",
        "",
        "Two new seven-parameter chains extend hydrology and solar modeling. The existing "
        "three models, datasets, splits and accuracy targets stay unchanged. The new models reuse "
        "existing datasets; they add model complexity, not independent data or new domains.",
        "",
        "## Sensor QA correction",
        "",
        f"All {quality['columns']['module_c']['count']} cached module-temperature readings equal "
        f"{quality['columns']['module_c']['minimum']:g} C and are unusable. Measured-temperature "
        "RMSE/ranking and earlier claims of observed intermediate temperature truth are withdrawn. "
        "Frozen raw diagnostics remain for provenance, but are not valid accuracy evidence. "
        "The AC-power objectives use simulated module temperature, plausible ambient-temperature "
        "and irradiance forcing, and measured AC power. No rows, splits, targets or primary "
        "optimization results were changed. Sensor range screening does not certify their accuracy.",
        "",
        "## Fixed-budget comparison",
        "",
        "Median held-out RMSE across seeds 0-2. Each row uses checkpoints of the same search "
        "trajectory; these are paired observations, not independent replications. Only validation "
        "error selects recommendations. Lower is better. Hydrology uses mm/day, solar uses kW, "
        "and copper retains the source's unresolved native unit multiplier.",
        "",
        "| Model | Method | Test at 12 | Test at 24 | Test at 48 | Test at 96 | Validation at 96 | Study seconds at 96 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for d in DOMAINS:
        for m in METHODS:
            group = [r for r in fixed if (r["domain"], r["method"]) == (d, m)]
            tests = [
                median_metric(
                    [next(s for s in r["checkpoints"] if s["evaluations"] == n) for r in group],
                    "test",
                )
                for n in CHECKPOINTS
            ]
            validation = median_validation(group)
            lines.append(
                f"| {d} | {m} | "
                + " | ".join(tests)
                + f" | {validation} | {median(r['study_seconds'] for r in group):.2f} |"
            )
    lines += [
        "",
        "Median validation RMSE across the same seeds:",
        "",
        "| Model | Method | Validation at 12 | Validation at 24 | Validation at 48 | Validation at 96 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for d in DOMAINS:
        for m in METHODS:
            group = [r for r in fixed if (r["domain"], r["method"]) == (d, m)]
            values = [
                median_validation(
                    [next(s for s in r["checkpoints"] if s["evaluations"] == n) for r in group]
                )
                for n in CHECKPOINTS
            ]
            lines.append(f"| {d} | {m} | " + " | ".join(values) + " |")
    lines += [
        "",
        "## Calls to the frozen validation target",
        "",
        "Five separate seeds (3-7), stopping immediately at the target or after 200 attempts. "
        "Existing targets are unchanged. Each new target is 1.05 times the lowest validation "
        "RMSE in its fixed matrix, frozen before these five seeds. This is a development quality "
        "target, not global convergence.",
        "",
        "| Model | Target | Method | Reached | Calls by seed 3-7 | Median successful calls | Mean calls consumed | Median study seconds | Median test RMSE |",
        "| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for d in DOMAINS:
        for m in METHODS:
            group = sorted(
                [r for r in target if (r["domain"], r["method"]) == (d, m)], key=lambda r: r["seed"]
            )
            hit = [r for r in group if r["target_reached"]]
            calls = ", ".join(
                str(r["evaluations"])
                if r["target_reached"]
                else (
                    ">200"
                    if r["stop_reason"] == "evaluation_cap"
                    else f"stopped@{r['evaluations']}"
                )
                for r in group
            )
            med = str(median(r["evaluations"] for r in hit)) if hit else "NA"
            lines.append(
                f"| {d} | {frozen['targets'][d]:.4f} | {m} | {len(hit)}/5 | {calls} | {med} | "
                f"{mean(r['evaluations'] for r in group):.1f} | {median(r['study_seconds'] for r in group):.3f} | {median_metric(group, 'test')} |"
            )
    lines += [
        "",
        "A >200 value is censored, not convergence at 200. Successful-only medians exclude "
        "capped or terminated runs. Mean calls consumed is a restricted computational cost and "
        "cannot alone rank methods with unequal success rates. Missing scores are not silently "
        "dropped. Individual JSON records retain actual termination reasons.",
        "",
        "## Timing, adaptive actions and failures",
        "",
        "Study time includes optimization and durable bookkeeping. Model time covers BMI "
        "evaluation, including model initialization and any copper training fit. Imports, input "
        "loading, backend construction and held-out scoring are outside the study timer. Runs "
        "are sequential with one Torch CPU thread. These are single-machine measurements; "
        "model-dependent cost and bookkeeping matter alongside evaluation counts.",
        "",
        "| Experiment | Model | Method | Median model seconds | Median optimizer/controller seconds | Adaptive BO actions | Fallback actions | Failed attempts |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, rows in [("fixed", fixed), ("target", target)]:
        for d in DOMAINS:
            for m in METHODS:
                group = [r for r in rows if (r["domain"], r["method"]) == (d, m)]
                raw = [
                    e
                    for r in group
                    for e in entries(RESULTS / mode / f"{d}-{m}-{r['seed']}" / "observations.jsonl")
                ]
                adaptive = sum(e["action"]["suggested_by"] == "system:bayes" for e in raw)
                warmup = 8 if d in ["hymod", "solar_diode"] else 4
                # Successful observed count controls initialization; labels identify actual policy.
                fallback = 0
                for r in group:
                    successful = 0
                    for e in entries(
                        RESULTS / mode / f"{d}-{m}-{r['seed']}" / "observations.jsonl"
                    ):
                        fallback += (
                            m == "bo"
                            and successful >= warmup
                            and e["action"]["suggested_by"] == "system:sobol"
                        )
                        successful += e["result"]["status"] == "success"
                failed = sum(e["result"]["status"] != "success" for e in raw)
                lines.append(
                    f"| {mode} | {d} | {m} | {median(r['model_seconds'] for r in group):.3f} | "
                    f"{median(r['controller_and_optimizer_seconds'] for r in group):.3f} | {adaptive} | {fallback} | {failed} |"
                )
    lines += [
        "",
        "For an expensive model, fewer calls can reduce time when saved evaluation cost exceeds "
        "additional optimizer overhead. This is conditional on unchanged search behavior and is "
        "not a measured speedup on another model. A capped baseline provides a lower bound on "
        "calls to target, not an exact eventual convergence time.",
        "",
        "## Evidence and limitations",
        "",
        "The audit checks every successful objective and each checkpoint/final recommendation. "
        "Existing models use vector kernels as a reference. Solar diode uses an independent "
        "vector Lambert-W solver against the scalar Brent BMI implementation. HYMOD is rerun "
        "through BMI with a daily water-balance check. Audit JSON files retain counts and hashes.",
        "",
        "HYMOD states are conditional on the chosen initialization; slow reservoirs are not "
        "guaranteed to equilibrate during the inherited warmup. The solar module is a "
        "representative CEC snapshot, not the identified site hardware. Its parameters need not "
        "be identifiable from aggregate AC measurements. Model complexity does not establish "
        "physical realism or predictive skill. Validation optimization and held-out improvement "
        "remain distinct. Partial-observation BO is not evaluated by this suite.",
        "",
        "See ../PROTOCOL.md for sources, bounds, targets and timing definitions. "
        "workflow/results.json retains actual BMI component-swap diagnostics. "
        "fixed/ and target/ retain ledgers, manifests, timings and frozen recommendations. "
        "Each retains the exact earlier workflow.py and README.md under source/. The later diagnostic fix "
        "deep-copies component metadata before swapping. Initial incorrect swap diagnostics "
        "are preserved in workflow-initial/. Intermediate diagnostics before sensor QA are in "
        "workflow-before-temperature-qa/; corrected diagnostics are in workflow/.",
        "",
    ]
    with (RESULTS / "trajectories.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            lineterminator="\n",
            fieldnames=[
                "experiment",
                "model",
                "method",
                "seed",
                "evaluations",
                "validation_rmse",
                "target",
                "study_seconds",
                "model_seconds",
            ],
        )
        writer.writeheader()
        for mode, rows in [("fixed", fixed), ("target", target)]:
            for row in rows:
                for step in row["trajectory"]:
                    writer.writerow(
                        {
                            "experiment": mode,
                            "model": row["domain"],
                            "method": row["method"],
                            "seed": row["seed"],
                            "evaluations": step["evaluations"],
                            "validation_rmse": step["best_validation_rmse"],
                            "target": frozen["targets"][row["domain"]],
                            "study_seconds": step["study_seconds"],
                            "model_seconds": step["model_seconds"],
                        }
                    )
    (RESULTS / "RESULTS.md").write_text("\n".join(lines))
    print(f"Verified {len(fixed) + len(target)} studies; wrote {RESULTS / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
