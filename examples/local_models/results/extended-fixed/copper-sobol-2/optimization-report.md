# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"model":"rational3","ridge":1.7323950672424206e-08}
- Objective and constraint observations: {"rmse":0.19599479143277304}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: c57b6a4ffeb0007cfb910b1880955222a855295d3af8d52e6873f472847d34cb
- Ledger hash: e8849f64ce27dd8c14ecf7c465226a5789cbda1f37dfdc3e3204e98d1006e633

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
