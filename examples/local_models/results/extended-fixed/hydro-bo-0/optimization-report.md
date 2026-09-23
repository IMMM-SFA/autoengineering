# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
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
- Manifest study hash: 59660fe3ad72cf160081b0f7a57e33b6b30d48d3d2f30e3138d268e843a059d3
- Ledger hash: c9277c39bc4269fab4bf043f449ddab64ddab9990685c43b9795dc7e2bfaf750

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
