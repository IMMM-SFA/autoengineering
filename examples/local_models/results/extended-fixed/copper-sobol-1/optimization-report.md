# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"model":"rational3","ridge":5.350829026856091e-08}
- Objective and constraint observations: {"rmse":0.19598389612508613}
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
- Manifest study hash: 0518ecbe55398d90e154f76e9f02f885c1949bfe3e02eb30e17a22961922a373
- Ledger hash: dd46fab2e75f67a24d037a3315244f5a68d1566c1821e48db697de34515b60c2

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
