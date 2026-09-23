# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"model":"rational3","ridge":5.350829026856091e-08}
- Objective and constraint observations: {"rmse":0.19598389612508613}
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
- Manifest study hash: 25060116f2dba4480bda855bd4292e63342e3a28fb98353f227c5b379424e1fa
- Ledger hash: 6be69f9464cb023fb24b78f46408e721c03f0f6b39686c2b085ea502c27bf601

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
