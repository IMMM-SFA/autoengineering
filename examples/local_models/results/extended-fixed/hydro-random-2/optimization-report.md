# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"capacity":156.27213061689056,"pet":"hargreaves","recession":0.8649656384990743}
- Objective and constraint observations: {"rmse":2.7875932684277474}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3522cb48621dffe653dc9f9fe58b14a14fe759e76f4e5d62207a87d333ffcf80
- Ledger hash: 9376d410612a5983e0fb62086ceb318a6c44cca06f1eb70e6991493fdfe02d1c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
