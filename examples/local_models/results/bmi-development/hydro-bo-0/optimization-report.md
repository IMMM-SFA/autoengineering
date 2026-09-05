# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: f4df6b05681743b3136b1a1bf3e0ff37780049778d7b047fc87ce3896269fb51
- Ledger hash: ad10e698dd0def8252af6d91891d1989b899d700040d3b325d542f15478bf0d5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
