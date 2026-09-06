# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000051
- Configuration: {"capacity":174.051646143198,"pet":"hargreaves","recession":0.9240855702199041}
- Objective and constraint observations: {"rmse":2.2719076382488574}
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
- Manifest study hash: 67c3f1170d4137065ee3290e368c0b28c1dc1b09dc3d683778988ce02d59ca4e
- Ledger hash: bb29d41218c2ecde081aeb71ecd48fe842a521483f2d3b96750749818c1f6f98

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
