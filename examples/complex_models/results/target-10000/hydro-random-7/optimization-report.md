# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000088
- Configuration: {"capacity":198.3228840973398,"pet":"hargreaves","recession":0.936331160963788}
- Objective and constraint observations: {"rmse":2.1521504582731623}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 89.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 423f1630f0b9fc479d4786e6374a7fe55503f5942025d979fc9d6a832f3e7f0d
- Ledger hash: b853f9ddef0b885ecee76324185d9347239fe94d8682356e5e09b5c98d77a40b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
