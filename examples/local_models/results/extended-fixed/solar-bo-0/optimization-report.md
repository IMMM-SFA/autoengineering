# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"heat_loss":60.0,"loss":0.6495612635362041,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0775599041313}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ba6da8eeb2e996d1fb30a2c8665e3b55d85ce17c5526218fb7f15fa4ee46cba5
- Ledger hash: 7dcb6acc1913c722533db336723be3f009e8069cce1708d5fa65f78afec37f4c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
