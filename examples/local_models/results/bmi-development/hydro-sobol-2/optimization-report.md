# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"capacity":66.50056920945644,"pet":"hargreaves","recession":0.8646651983261108}
- Objective and constraint observations: {"rmse":3.548664124657178}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: aa1b2ed734c5e0c25b8457b138bbce1a9f610a158e8a0617f31df4d6e379931b
- Ledger hash: 06e565155476a5f5394bc143bbdbd27792cdd56e41631b510cafc8b6079638af

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
