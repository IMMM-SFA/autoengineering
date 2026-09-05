# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
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
- Manifest study hash: c3bc2fef9b66aa19981b4a58e3530dc3b6b547c7e6ea92092dc1061c66088e50
- Ledger hash: 5e42e616fb5fd4d2df7b346434add34bbf4e4cef4bf14a5118d0d9aa88909cb9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
