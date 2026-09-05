# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000017
- Configuration: {"model":"rational3","ridge":1.7063821058449603e-06}
- Objective and constraint observations: {"rmse":0.19720155675856146}
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
- Manifest study hash: 1d8ce5e9f6d2be0decb83735967ef5ba186a52c00280fb26ac0cfe1a71be2880
- Ledger hash: 6dcb3a14499022d8c964375903762c0d7007788aa4bbb9ba80e4d22201d2333a

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
