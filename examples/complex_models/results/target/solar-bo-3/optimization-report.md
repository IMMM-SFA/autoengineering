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
- Manifest study hash: a1e2e253d6d86f81017918f7f1a22fd0dea6c68113dafd1837d5df38e1713872
- Ledger hash: 5c9f558f205488cf581a468b4c936dc1466a63614d5ecd7d58690dea6ee4c888

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
