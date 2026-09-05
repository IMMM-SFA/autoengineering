# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"capacity":192.63299442827702,"pet":"hamon","recession":0.8318980480544269}
- Objective and constraint observations: {"rmse":3.401117447201036}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 254a5dcb8ac015f7051c356f1bc936e41971ee2e07b567138b509ae463e4dce1
- Ledger hash: dda151e113d8ba2ed0f9e0b6e760304f5dc43cb5c96afa0afbf772bfe5a15214

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
