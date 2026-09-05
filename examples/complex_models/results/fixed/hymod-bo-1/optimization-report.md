# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000076
- Configuration: {"alpha":0.5124407984395596,"beta":1.766060350453182,"cmax":669.3623119721148,"kfast":0.47382267830094216,"kslow":0.001,"pet":"hamon","pet_scale":1.5}
- Objective and constraint observations: {"rmse":1.2409135630730266}
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
- Manifest study hash: 14b78d3d70ad2625217358743e3352ee2f8ef2a9143b7498694d59fbafa7a604
- Ledger hash: 20a9f3c6bf9a0fa66c4ce545a3cec32b7c6b73d40c704024ed0ce7a6b5d276cc

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
