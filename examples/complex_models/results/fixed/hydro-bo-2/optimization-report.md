# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: dd4e0b2a3834eb5f96175b33cd024e1c681478b276c15a7ba5efc8f242411486
- Ledger hash: ef7a9f7906e6f0032d88e07666dac4e8b8cd4a5f74410945e41177f0a5db6011

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
