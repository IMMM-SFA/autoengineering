# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"model":"rational3","ridge":6.07422269658425e-08}
- Objective and constraint observations: {"rmse":0.1959822510548131}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: dfb7699ce8dd05ecc8b043bc925427583cbe6d74c26c1c3371319933e26b12c1
- Ledger hash: 8c98ca431425e774daa965a7f1bac40864cd024351c16c1bfe5d8b08e6fb67ca

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
