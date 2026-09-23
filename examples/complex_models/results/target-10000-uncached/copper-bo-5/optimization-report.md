# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"model":"rational3","ridge":7.714528345603081e-08}
- Objective and constraint observations: {"rmse":0.19597913769610728}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 5.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 3819828f7b85d3fbd4d6553fb4f071d16e99a19b14945e565153e6bbb5069fca
- Ledger hash: 70907f63ef6f61874c0f5596f831edcad3e982432034983facd9663a74bd4324

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
