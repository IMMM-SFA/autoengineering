# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"model":"rational3","ridge":1.7323950672424206e-08}
- Objective and constraint observations: {"rmse":0.19599479143277304}
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
- Manifest study hash: 3342303b08e4002ae5fe350a039c782b803186089fa4c5c443ddf36a70e098f4
- Ledger hash: a02f0576bf377bddd37621aff35cb0a62b564a4176dce4c50c8ad8e046c2cd93

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
