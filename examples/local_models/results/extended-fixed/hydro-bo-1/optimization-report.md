# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 18347290a9f8d565d9f6547418bb12d055daad7b326766daaef6599a0ab6bcd5
- Ledger hash: cfa6c4331ce3ff5c47513d3f6178317ff0ae50007ff9b970523e9e27828247b7

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
