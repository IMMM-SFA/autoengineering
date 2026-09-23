# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"heat_loss":60.0,"loss":0.6495612635362041,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0775599041313}
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
- Manifest study hash: ff2fb5eb5cb23d7cdddc25f0d6613425cb5244ea97d3314cd5528480038dbcd7
- Ledger hash: 8394d3d9cfd12de004307b0e7367d75fb961c2374844b92b1adba0ba752f0346

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
