# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000011
- Configuration: {"model":"rational3","ridge":6.452224857938715e-08}
- Objective and constraint observations: {"rmse":0.19598145919108328}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 433cc7f911ea117a3239d33427e02556c7afe0e761c5eeae1705a0c92407f20e
- Ledger hash: c9ba870627d5e06811ca9baee15d0536eb7e17348cfbd3182041d70acc9ebd0b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
