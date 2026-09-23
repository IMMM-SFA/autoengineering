# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"model":"rational3","ridge":8.21917915015978e-06}
- Objective and constraint observations: {"rmse":0.20416668932215265}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 36a6500bf80d56c0f0e86b0bcdb6874bd73dda26359efa412b444e2036db1863
- Ledger hash: ffa51086b208f585d0c0948d9a14c32916db5996593075317e5ccfb59db641c3

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
