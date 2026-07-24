---
name: auto-research-loop
description: Run the bounded auto-research improvement loop over candidate replacement models — swap each in, execute the chain, validate with the package's metrics, keep what improves, and produce an evidence-first cited report. Use after deep-research-candidates has produced candidates.yaml. Adapts feynman's /autoresearch loop and openresearch-cli's experiment-tree + evidence-first reporting.
---

# Auto-Research Loop

You are testing candidate replacement models honestly and keeping an auditable
record. The creative step (which candidates to try) already happened in
`deep-research-candidates`; here you measure them with the package's own
`validate_arrays` / `rank_opportunities` and let the evidence decide.

The deterministic loop lives in the package (`autoengineering.research.auto_improve`)
— you do not re-implement it. Your job is to wire up the run, invoke it, and report.
This adapts feynman's bounded `/autoresearch` loop and openresearch-cli's
experiment-tree discipline (see the repo `NOTICE`).

## Cardinal rules (experiment-tree discipline)

- **The baseline is immutable.** It is the control every variant is measured against.
  `auto_improve` never mutates the input system; keep it that way.
- **Same measurement across nodes.** Use identical `metrics`, `thresholds`, and the
  same `observed` data and `validate_output` for every candidate. The only variable
  is the swapped component.
- **Grow down, not sideways.** The loop already descends from the current best node.
  A tree that is all direct children of the root with no grandchildren means nothing
  stacked — surface that in the report rather than hiding it.
- **Evidence before conclusions.** Read the `ValidationResult`s before proposing the
  next move. Do not claim an improvement the metrics do not show.

## Step 1 — Confirm the run

Before starting, confirm with the user (feynman `/autoresearch` does this too):

```
Optimization target: <metric(s)> ( <direction> )
Observed data:       <path> (column)
Output scored:       <run_chain key, e.g. routing.streamflow>
Candidates:          <candidates.yaml> (N candidates)
Max iterations:      <N>
Stop target:         <e.g. nse >= 0.5, or none>
```

Do not start the loop without explicit approval.

## Step 2 — Provide `run_chain`

The loop needs a callable `run_chain(system) -> {output_name: array}` that executes
the model chain. Two ways to get one:

- **Automatic** (clean feed-forward chains): add a `runnable` block to each component
  in `system.yaml`, then

  ```python
  from autoengineering.research import build_feedforward_runner
  run_chain = build_feedforward_runner(system, {"weather_data.precip": precip, ...})
  ```

- **Hand-written** (chains with inter-component arithmetic): write a small function
  that runs the models and returns the named arrays, as the examples do
  (`examples/leaf_river/run_auto_research.py`).

Every candidate's `runnable.inputs` must be satisfiable from a graph edge or from the
`source_arrays` you pass in.

## Step 3 — Run the loop

Via the API:

```python
from autoengineering.research import auto_improve, load_candidates, write_report

tree = auto_improve(
    system, run_chain, observed,
    validate_output="routing.streamflow",
    candidates=load_candidates("candidates.yaml"),
    metrics=["rmse", "bias", "nse", "kge"],
    thresholds={"nse": 0.4, "kge": 0.4},
    target={"nse": 0.5},        # optional satisficing stop
    max_iterations=20,          # bounded
    workdir="outputs", slug="my-system",
)
write_report(tree, system, "my-system", "outputs")
```

Or via the CLI, where `--chain module:factory` is a factory that takes the system and
returns `run_chain`:

```bash
pixi run autoengineering improve system.yaml \
    -C candidates.yaml --chain run_auto_research:make_run_chain \
    -b observed.csv -O routing.streamflow -t nse=0.5 --max-iter 20
```

## Step 4 — Evidence-first report

`auto_improve` writes `autoresearch.md`, `autoresearch.jsonl`, and a `CHANGELOG.md`
entry; `write_report` adds `outputs/<slug>.report.md` and `outputs/<slug>.provenance.md`.
The report leads with the baseline → best metric table (evidence), then the kept
changes, then the candidate `sources` as References.

Before you conclude, verify on disk that the artifacts exist and that any claim you
make matches the metric table. Render the tree for the user:

```bash
pixi run autoengineering experiments outputs/autoresearch.jsonl
```

Final response: state the baseline → best metric change, which swaps were kept, and
link the report and provenance files. If nothing beat the baseline, say so plainly —
a null result is a valid, auditable outcome.
