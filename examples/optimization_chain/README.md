# Optimization chain example

This offline example runs a deterministic three-component chain through the whole-system
optimization controller. The checked configuration uses Sobol search, not BoTorch. It searches a
categorical architecture, a continuous gain, an integer stage count, and a conditional curvature.
The objective maximizes negative root mean square error while absolute bias must not exceed 0.3.

The known feasible optimum is the linear architecture with gain 1.25 and two stages. The evaluator
also returns a controlled model failure when gain times stages exceeds 6.8.
`expected-result.json` records that analytic optimum and the recommendation from the checked Sobol
run.

Run these commands from the repository root. The system path is resolved relative to the
optimization file.

## Bounded start and resume

Start with three evaluations:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --max-new-evaluations 3
```

Resume the same study to its terminal budget:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --resume
```

Add `--format json` to either command for JSON output.

## Inspect the results

```sh
pixi run python -m json.tool outputs/optimization-chain/manifest.json
pixi run python -m json.tool outputs/optimization-chain/recommendation.json
sed -n '1,160p' outputs/optimization-chain/optimization-report.md
```

`observations.jsonl` is the append-only action and result ledger. `manifest.json` binds that ledger
to the run specification, system, evaluator source, and `input.csv` hashes.

## Check reproducibility

Use two new directories, then compare the scientific records and recommendation:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/repeat-a
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/repeat-b
cmp outputs/repeat-a/observations.jsonl outputs/repeat-b/observations.jsonl
cmp outputs/repeat-a/recommendation.json outputs/repeat-b/recommendation.json
```

The manifests intentionally contain runtime timestamps and are not expected to be byte identical.

## Workflow boundary

The architecture category selects implementations already provided by the evaluator. It does not
research alternatives or train a replacement model. The example demonstrates a working BO-layer
contract while the unified model DAG, harness, interactive app, and broader method-selection
workflow remain in progress. See the [optimization guide](../../docs/optimization.md) and
[model improvement criteria](../../docs/model-improvement.md).
