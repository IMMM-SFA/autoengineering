# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
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
- Manifest study hash: b5b9cbcbf6c59b6734feeb8fc18049b6b64c7d6fffdc62019c664bef0fdef124
- Ledger hash: 5b5c963b83f83666ced7614a54a8105243f98742351d9de3d6f8fc855b764cc7

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
