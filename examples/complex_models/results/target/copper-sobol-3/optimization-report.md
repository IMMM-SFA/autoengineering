# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"model":"rational3","ridge":8.21917915015978e-06}
- Objective and constraint observations: {"rmse":0.20416668932215265}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ded00537a6be4fbd899fbcd0c855815c6c51db6f6f3beb13a3e5675c3d5ac1e9
- Ledger hash: e305997930d9f039fe65dbc4769d79f18625ffffcbe4cd965e6d444d679eb7b5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
