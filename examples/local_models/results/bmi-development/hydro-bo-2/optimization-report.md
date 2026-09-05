# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 8dc299f4f8d8089feb4f6137bd9cf541ae60882ac5cd2c88792f24ce60c6833b
- Ledger hash: e87ca8463b5cb32ac64db05e394871bcbbf533e707a3d51ad77019ace45c8e3e

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
