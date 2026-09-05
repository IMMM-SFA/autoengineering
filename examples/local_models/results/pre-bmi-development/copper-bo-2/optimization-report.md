# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000008
- Configuration: {"model":"rational3","ridge":1.89391333787162e-07}
- Objective and constraint observations: {"rmse":0.19597783815896805}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ea5336bc564e2d2bef294ec966ca3b91d639129fb462979951939f02adbe1574
- Ledger hash: dfdddd50bc7c83fb7a39b4c236f3879f616258e5effff5c76fb298858df33ca2

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
