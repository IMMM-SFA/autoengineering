# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 54149c0a7d4e2913162d93e9a8bb4e0877606245fd53d4368171f80c483f96d0
- Ledger hash: fa5e907d065d78caf6c6fa1a1d305ac5e31f65da0f53b24ca091c7a509b7f968

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
