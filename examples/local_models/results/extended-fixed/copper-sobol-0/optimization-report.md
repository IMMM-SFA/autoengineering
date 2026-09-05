# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"model":"rational3","ridge":2.1078727842948533e-08}
- Objective and constraint observations: {"rmse":0.19599344579277864}
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
- Manifest study hash: f933fb9abecaaeaf6b57cdbfecf8b5672d11cf4626fa05804a64ceeb2b9ae546
- Ledger hash: 0118a59b3d7a5bc25159cab4919eb1557561dc5267260d9af6b6cf06e1638f16

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
