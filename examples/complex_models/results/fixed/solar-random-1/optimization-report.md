# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000013
- Configuration: {"heat_loss":56.2440591862284,"loss":0.6498768672765514,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.07793636465613}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 59946e3b93ff59590128ee13821c0cc277ae268915c6c59995265d9791a9ec73
- Ledger hash: 6d224df33b38c849589a1bb8b1d69f2c8e13f896efe2933be2e1458823f4c8bd

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
