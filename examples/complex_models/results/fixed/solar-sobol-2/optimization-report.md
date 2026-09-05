# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000071
- Configuration: {"heat_loss":41.72795475460589,"loss":0.6495215374510735,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.07753767594625}
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
- Manifest study hash: deb789a46a823118e0561b9d7ec65fa45507c1a69273cd6c6e62c88900bb79c3
- Ledger hash: 8c8dcbbd840e236f9beedf63c75d01b1e3818cffdc8ac93983785594f31df0f7

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
