# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000056
- Configuration: {"model":"rational3","ridge":1.4812004353773246e-07}
- Objective and constraint observations: {"rmse":0.1959746119287382}
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
- Manifest study hash: 12853fe6d0565b670f1f582d6f4d2bb525c87a1ba5fcc0749c4499e1d05243e4
- Ledger hash: cef78976eb6a0507632e22ef1c2ad1fdab7c248c869d02ed619f8722544f4f0c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
