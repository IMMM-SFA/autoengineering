# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"heat_loss":44.866151036694646,"loss":0.7044127462897449,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":180.38855162774908}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 39c57a48e07f2e33781ae74e5989fb190ecac5edbc7e2bd21c9136d644fb353e
- Ledger hash: a415856540a3aa8c64fb80cb774cfc95e49cd40f8b16dd4ba5ebc4d6d367d814

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
