# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000011
- Configuration: {"heat_loss":52.081743410854834,"loss":0.6483360013326058,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0794632912374}
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
- Manifest study hash: 23e1fc6b4f77aa89112fd8fd69c30a64522bb9de9d0d35b1b87f420ddf23a4c4
- Ledger hash: fdf1592e86fa9920a4be46d369e16ea3ec45bfc5cbf4a8368371c9769dca526d

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
