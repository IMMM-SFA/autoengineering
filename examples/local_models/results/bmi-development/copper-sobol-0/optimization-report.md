# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"model":"rational3","ridge":2.1078727842948533e-08}
- Objective and constraint observations: {"rmse":0.19599344579277864}
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
- Manifest study hash: 0bf18dc9a785e37986481e5cb572f759fa0aa41ffbbc5447dcf721a16175b4f9
- Ledger hash: 4645119e9e83cdf7235d47e8502a6caead490d9d7ab51f7c9e4c1de49a5bbc67

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
