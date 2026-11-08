---
name: auto-research-loop
description: Run a bounded comparison of executable component replacements and report retained, reverted, and failed trials with their evidence.
---

# Test candidate replacements

Use `autoengineering.research.auto_improve` to test supplied candidates. Read `docs/workflow.md`
for its fitness, threshold, and artifact behavior. This skill adapts feynman's bounded experiments
and openresearch-cli's experiment records. See `NOTICE`.

## Prepare the run

Record the baseline, observations, output to score, metrics, thresholds, stop target, candidate
file, iteration limit, and output directory. Keep the evaluation design fixed. Use authorization
already provided in the session and ask only when a required decision or execution authority is
missing.

Validate each runnable and its inputs before the loop. Provide `run_chain(system)` returning named
arrays. Use `build_feedforward_runner` for an acyclic graph with declared runnable components, or a
handwritten runner where the chain needs additional arithmetic. The Leaf River example shows the
latter.

Use a fresh output directory. The replacement loop does not implement the optimization controller's
durable resume or cost budget. Manage expensive training and model runs through an explicitly
bounded caller until the planned harness provides a common lifecycle.

## Execute

```python
from autoengineering.research import auto_improve, load_candidates, write_report
from autoengineering.validate import PhysicalCheck

tree = auto_improve(
    system, run_chain, observed,
    validate_output="routing.streamflow",
    candidates=load_candidates("candidates.yaml"),
    metrics=["rmse", "bias", "nse", "kge", "pbias", "low_flow_pbias"],
    thresholds={"nse": 0.4, "kge": 0.4},
    physical_checks=[
        PhysicalCheck(name="nonnegative_flow", kind="nonnegative", port="routing.streamflow"),
    ],
    max_degradation={"low_flow_pbias": 5.0},
    target={"nse": 0.5}, max_iterations=20,
    workdir="outputs/replacement-study", slug="replacement-study",
)
write_report(tree, system, "replacement-study", "outputs/replacement-study")
```

This template requires a prepared system, runner, observations, and candidate file. For complete
examples, run `pixi run python examples/leaf_river/run_auto_research.py` or
`pixi run python examples/im3_water_scarcity/run_workflow.py`.

The baseline remains immutable. Each candidate is tried once in order against the current retained
system. Strictly greater fitness without any `PhysicalCheck` or `max_degradation` veto produces a
kept node; candidates that violate a physical guardrail are marked `vetoed`.

## Inspect the evidence

Check `autoresearch.md`, `autoresearch.jsonl`, the `CHANGELOG.md` entry, and the report and provenance
sidecar. Inspect the experiment tree with:

```sh
pixi run autoengineering experiments outputs/replacement-study/autoresearch.jsonl
```

Report terminal and component metrics where available, costs measured by the caller, retained and
reverted trials, and failures. Explain any metric tradeoff. A retained trial is not automatically
an accepted model or evidence of held-out skill. If no candidate improves the baseline, state that
result and preserve the records.

Use `docs/model-improvement.md` to assess possible next work. Do not infer that a failed simple
candidate justifies a deep model. Whole-system BO uses a separate evaluator, run specification,
and controller described in `docs/optimization.md`.
