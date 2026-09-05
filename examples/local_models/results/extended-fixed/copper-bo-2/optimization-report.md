# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000016
- Configuration: {"model":"rational3","ridge":9.939889737602441e-08}
- Objective and constraint observations: {"rmse":0.19597621865154757}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 443526f3f32edfa93db5e7b5dd7ea5084d9561df2397bcbe7af57fe123c38a45
- Ledger hash: c7e3f831c83b8905e327175dbf474de5c4d2a4f00c1a32b1af6207187868bb2a

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
