# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 7.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: fa9ca852fd3fbf16b14b8d7f7e718a507d77d64a94aafb3460fb1c20e634b328
- Ledger hash: 8f0d6a2f04fe1488bd709192886163493d980e5a029a71a018e9249bd1f84bda

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
