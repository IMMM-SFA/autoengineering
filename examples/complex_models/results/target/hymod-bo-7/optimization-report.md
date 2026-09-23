# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000117
- Configuration: {"alpha":0.6496203727580514,"beta":0.48272532135963475,"cmax":422.2859155166315,"kfast":0.4787611558914743,"kslow":0.010369615470448996,"pet":"hamon","pet_scale":1.5}
- Objective and constraint observations: {"rmse":1.1947862046056594}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 200.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ee9130a3f5f1aeecd918eec61a30b667672ee9b02dc99081d3f59a8ca72c9266
- Ledger hash: fa6ddb9b7ebba9e46012c7a7c2707377a21d4938db17cc2c74b6d8bf597297fd

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
