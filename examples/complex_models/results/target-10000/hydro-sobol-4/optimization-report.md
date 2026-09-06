# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000323
- Configuration: {"capacity":198.80582673475146,"pet":"hargreaves","recession":0.942657551728189}
- Objective and constraint observations: {"rmse":2.1110336468254656}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 324.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 2ae26a45342ae6bd11612077cf30b1c0161143e81f48035bc2e0fb9f514ac808
- Ledger hash: 50cbab2f799a8c8c96354e1062461e39206bb1285bb7e0b345fb1277a4eeb436

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
