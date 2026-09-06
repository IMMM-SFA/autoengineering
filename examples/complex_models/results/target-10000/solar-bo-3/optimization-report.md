# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"heat_loss":52.402018806897104,"loss":0.6217362124007195,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":176.4353468192891}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 3.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 13fec4c1b760688ae98690e4b31966b1a2831cb4a6522112d625cd734fc0e047
- Ledger hash: 5c9f558f205488cf581a468b4c936dc1466a63614d5ecd7d58690dea6ee4c888

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
