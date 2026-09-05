# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000031
- Configuration: {"model":"rational3","ridge":9.3309362234864e-08}
- Objective and constraint observations: {"rmse":0.1959768744819118}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: f7b561f17eed900ec9150d027de7e58164773bdd8a094998f955252b9d2955ea
- Ledger hash: b3ca4c822fcb6b951cdec1d7fd3d52e559e7f8de130746379b7ebfec91a4a126

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
