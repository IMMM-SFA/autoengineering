# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
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
- Manifest study hash: 043845b1118f96c65ffbecf0b4b408eee7223f13b363098e7b18fab586798e3d
- Ledger hash: d0f26b59a6459977ab9b50327a56e043d9f61aabb08218f48466e04b17d3f906

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
