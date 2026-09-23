# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000021
- Configuration: {"capacity":167.5978096947074,"pet":"hamon","recession":0.9393172711133957}
- Objective and constraint observations: {"rmse":2.4247672337281507}
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
- Manifest study hash: f69534245655cea252268d41cdee5d95c1edd3b423dc6dad40d3a0951f8b74cf
- Ledger hash: b3a53d1858de44c0fd4814b5104b7d7ce04ec6a318608c5688225f78f7c2e9a8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
