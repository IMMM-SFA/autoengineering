# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000005
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 97dbc5613662109a18b70b0fbd03f6ee1140794ae5ceabce983a25cb0db37838
- Ledger hash: 0d5bdb0d0bcfe558091d87184f08194017b2c49ba4994ed5322fba39e4007f14

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
