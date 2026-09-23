# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"model":"rational3","ridge":2.70157628986298e-06}
- Objective and constraint observations: {"rmse":0.19830957458889473}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 8.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 151938bc0195e1b6b0250fba52731e9e59e76f7cd3d804928d64e4cfb690f05d
- Ledger hash: 0d3ed8250f90ad6c6efc5630186965b8d662fba3a47ed5c1c90b308d6f526452

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
