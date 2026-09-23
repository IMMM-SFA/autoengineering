# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000005
- Configuration: {"alpha":0.3975344775590114,"beta":2.621485933365125,"cmax":782.2004019557113,"kfast":0.556369421596534,"kslow":0.001302313096234342,"pet":"hargreaves","pet_scale":0.9601447620865183}
- Objective and constraint observations: {"rmse":1.3709699573811824}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 1fbaa03370e2c029303bfb51a52635d95894cc2517abe20c11c6b23d1b331b67
- Ledger hash: 54e81613458ed74a3530269f04bc4adb34d08e551564dd5d90608ce1223e901b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
