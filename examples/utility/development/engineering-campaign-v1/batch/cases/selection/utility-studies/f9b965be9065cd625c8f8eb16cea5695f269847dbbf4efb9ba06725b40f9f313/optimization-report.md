# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"source_current":0.03456821138970554}
- Objective and constraint observations: {"source_power":0.11854625333653068}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 4.523145456798375
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: d12c4e311b57dda6482ce8463d5e753c4c97bf79ac450d71c68b9ac73c209522
- Ledger hash: da321da0d8c1092d61549e913494d655446d225bb3fef519dce8276c3edd802b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
