# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"heat_loss":34.52785481501774,"loss":0.6654094770136539,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.534471092378}
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
- Manifest study hash: 5ac9007135e88a8306d31cee8b19d0435e7133c422bfaa0df0aac59d6fd0375b
- Ledger hash: 52a453ac7095405fd1b40deacc23dbdd16ad07364b927072473687ed524a02b7

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
