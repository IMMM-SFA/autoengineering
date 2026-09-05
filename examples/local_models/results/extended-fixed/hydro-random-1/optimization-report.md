# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"capacity":173.049956804522,"pet":"hargreaves","recession":0.8801238177977585}
- Objective and constraint observations: {"rmse":2.6104276849140033}
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
- Manifest study hash: 9651d95a3831e39cb9728b46f9cbdf09fe7cfb0700a1dac811c59898a4efd817
- Ledger hash: 9a4b3591c61d7cbe3da8fde8b93d3121df62329f9eb9f4c57842ca5e49541834

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
