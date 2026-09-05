# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000015
- Configuration: {"model":"rational3","ridge":2.0599673496944493e-07}
- Objective and constraint observations: {"rmse":0.19598020929214044}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ba9f01f807260e72306943545446df41aad16879001cb4bd776b459e6a777527
- Ledger hash: 1886649c5449fed419592cdd196f51cb095f98ca7e7ce4696b1da056fc40617b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
