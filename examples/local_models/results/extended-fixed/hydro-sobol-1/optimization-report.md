# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"capacity":66.96133969351649,"pet":"hargreaves","recession":0.9431581432931124}
- Objective and constraint observations: {"rmse":2.6076476742303027}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: e565d56e78bce16fd2899bf1119e5bcd3bda3854ef2788aea50b8e290afa8db6
- Ledger hash: fcd7fe8b29eb8ed20ed14341c20618d192f40f9edeee93e7496d3ed979f38914

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
