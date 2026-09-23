# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000072
- Configuration: {"alpha":0.5708633876980181,"beta":1.9013892878005645,"cmax":951.9217007026308,"kfast":0.3956300635503506,"kslow":0.004447963988617676,"pet":"hamon","pet_scale":1.263401442773623}
- Objective and constraint observations: {"rmse":1.4166969538218734}
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
- Manifest study hash: b59cd5d8430c8f2ac5f143d687afeae20e2551d0d776d1050e1a6d9e934e74e4
- Ledger hash: 21e8f09d9e36199ad7a254d37bcbb0e8bdb04942ad9ef7d44d3e8dd2fdf9e4f3

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
