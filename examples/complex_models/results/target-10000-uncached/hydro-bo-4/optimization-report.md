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
- Manifest study hash: e41fd8f6c658f15ffe5e6967074314d5ca4224c708a9368cd1781d581fd7ae41
- Ledger hash: c1cc30440b17dbc5ca18e11333879127a1c061e121133ad1a54108995dee9596

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
