# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000336
- Configuration: {"capacity":180.7742659188807,"pet":"hargreaves","recession":0.9426721127703785}
- Objective and constraint observations: {"rmse":2.128010893702043}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 337.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 92f8e6f3e6eabf728ca759270e8b0e5abe6bf20f327a59a5ee19b678782c17a7
- Ledger hash: ec6dfa7c3a4e448e24cf31d56b028d7e7f7877587f2ab740f676ac63c4ae77d0

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
