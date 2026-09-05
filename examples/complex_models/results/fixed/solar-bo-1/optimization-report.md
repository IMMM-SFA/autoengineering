# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000060
- Configuration: {"heat_loss":33.575553908313935,"loss":0.6493838183870894,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0775041717465}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: d8b72dbd0823ede5a87ad4f9d57b9a439610dc299bb128b2c14d4cb027cbf6d4
- Ledger hash: 28002146596b9907aefab8eef2ca37f955aa0327b901b0c330b1b145f69fb423

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
