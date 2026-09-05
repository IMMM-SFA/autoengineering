# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000033
- Configuration: {"model":"rational3","ridge":1.3756368805657352e-07}
- Objective and constraint observations: {"rmse":0.1959744354233358}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 11c0bcdecf3ca7a0ab174febca2f1049c43922a95db1360061e66183d45652b8
- Ledger hash: ceceecb07ed16b3028b00b03f323056c93d0b1c85a504c2b46006216169932f9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
