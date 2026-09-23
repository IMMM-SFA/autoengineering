# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"capacity":112.03895950658509,"pet":"hargreaves","recession":0.9286193351369336}
- Objective and constraint observations: {"rmse":2.4740480449331703}
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
- Manifest study hash: 9e0e73d80cad5465e9c32bbb19b8bacd295517369156515454a3ad6e10aea676
- Ledger hash: d2e108778aa3b1c1efcfb3e70eae9e0feb7cb90ebba5ad307f940caac03d3dab

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
