# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"model":"rational3","ridge":5.350829026856091e-08}
- Objective and constraint observations: {"rmse":0.19598389612508613}
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
- Manifest study hash: a3909cf9002d2b242d5074d4fc6f3ca59534d870b443516ca65d893251d77a95
- Ledger hash: ceb0375411737cb3ea3ef0b8474e28c721e7163669a6a1da74b8848fd746a1e0

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
