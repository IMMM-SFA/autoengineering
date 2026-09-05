# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000011
- Configuration: {"model":"rational3","ridge":3.173286097138193e-05}
- Objective and constraint observations: {"rmse":0.2343206305505835}
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
- Manifest study hash: ee6f844f8df421ef69bb4ad4d0e7a80a035b1ea6ca094935df1871b808e9ef39
- Ledger hash: b04e32e8e09979b27bf9f20c854ae6535ec585a112eb8d96cf4f72f88440ab98

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
