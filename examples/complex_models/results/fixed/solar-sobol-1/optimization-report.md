# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000024
- Configuration: {"heat_loss":44.96578139718622,"loss":0.6538723222911358,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.11339502934877}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 957b1e7525aae0281a5dd43545cd3cf179452a76a59b09b0041bda8958e80de2
- Ledger hash: c70325499cfe0de63a7e1707d49cc7566dbd021b9ddfa79b039dccbf5113f573

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
