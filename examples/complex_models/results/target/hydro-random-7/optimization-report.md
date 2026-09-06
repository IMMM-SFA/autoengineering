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
- Manifest study hash: afd89ec7eabad38e783e50049d76ff3812c1cb02f24c8d8c55251d933bcaab88
- Ledger hash: b853f9ddef0b885ecee76324185d9347239fe94d8682356e5e09b5c98d77a40b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
