# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"model":"rational3","ridge":1.5333804449976467e-08}
- Objective and constraint observations: {"rmse":0.19599552709823775}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: a076da33ac95850a9aae6997822ce9a882e68d1267eded2fdf8eca844c5bceb5
- Ledger hash: 12bd1252040c57e430c78d72ebcb2c8d4238503eb15ed1696df54587adf38735

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
