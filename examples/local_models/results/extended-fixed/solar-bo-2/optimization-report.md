# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000016
- Configuration: {"heat_loss":33.75701429456605,"loss":0.6496209935168424,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.07760391281883}
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
- Manifest study hash: e030506c2bcb4d4e9a05d21e76164654a0bce925c549262da87475abbebfc439
- Ledger hash: a4f791479d4184091f295b790414a71853ef7d0ea9405c8152d732a938816529

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
