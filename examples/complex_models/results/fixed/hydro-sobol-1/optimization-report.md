# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000058
- Configuration: {"capacity":141.66253495961428,"pet":"hargreaves","recession":0.9070489044301211}
- Objective and constraint observations: {"rmse":2.511946223420028}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: de4bfe1fa4a0f45a0f24d3385685d560cd6d69137b138107f78fd593f2855b91
- Ledger hash: de6fed1c6623791955e897baae0b2bc4cd7ae09fa30324d2de902196724e03ff

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
