# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000019
- Configuration: {"capacity":151.45953606814146,"pet":"hargreaves","recession":0.9285466043278574}
- Objective and constraint observations: {"rmse":2.298887175851291}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 200.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 97dadb5c4fa2389f838a399c441653ee2bac3ccaa0597c6f3e6e10943190af46
- Ledger hash: dc3a7c2cd16748d8c3f840f6b5cf9410e5a596d6b141854cf1b48bec67929b42

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
