# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000031
- Configuration: {"heat_loss":29.108509220505102,"loss":0.6473178620652837,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0851159156334}
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
- Manifest study hash: 109dd9abbc7846e112f239051f63ccc38505fe2dcfec9723a07b2e24390ed806
- Ledger hash: 7a3e4f3a8476ef6e52918aaee7cc2fbca6d1a735488411c1548be9523947d314

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
