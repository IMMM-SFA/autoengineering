# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000057
- Configuration: {"heat_loss":22.869214983699717,"loss":0.6493515554561724,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.07750609711547}
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
- Manifest study hash: 3aec86668c82ddf98e33d03d036cc32ee766813a692d9daa7236660dcd4537b0
- Ledger hash: cb8c4ab347212ea92316be7005f829f0ae48567d8473c5e50e64a11e7fc382c2

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
