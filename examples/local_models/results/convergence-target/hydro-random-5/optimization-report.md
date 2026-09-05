# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000057
- Configuration: {"capacity":195.86747055372948,"pet":"hargreaves","recession":0.8699448860213258}
- Objective and constraint observations: {"rmse":2.6508383900251036}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 60.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: b428bdcb7e26d11b8afcf3ad8ebde5ac83e6c94d056c2e2af4c2e7495ecdbca6
- Ledger hash: 6672385de734d0170a0514517f7855e58a6511b4e878e845d853fca881119655

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
