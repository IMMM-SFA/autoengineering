# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 7.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ca9e61c585059a93c0d8a37890aa4e2ca48692128a5a875194e5c259e4f92fe9
- Ledger hash: 87cd307277d39dd46fea06555d4c7aefcdd13a3d8918eff9a40e10f8cb90c747

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
