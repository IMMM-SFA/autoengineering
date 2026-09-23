# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"model":"rational3","ridge":9.730441723600648e-07}
- Objective and constraint observations: {"rmse":0.19646264559703372}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 3c3c8f451034f90286a7af4bc4f056cc1db35e99ec3447d5b2ae961acccc9bf6
- Ledger hash: 8fc4e9bbb19cadc8356649590b1e23286fd82a4317785491dd44f18fdc99795e

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
