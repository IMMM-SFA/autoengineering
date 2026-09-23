# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"heat_loss":19.828992363062167,"loss":0.6495652887781519,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0775624702757}
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
- Manifest study hash: ac569cf5384d815a597ae4cebace86d3eeffe9530e0d50b6c22d78b554c5fe47
- Ledger hash: 52cb8c44976cef9a24946da7aca61163ace52a473df371618dd0c8e327b63241

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
