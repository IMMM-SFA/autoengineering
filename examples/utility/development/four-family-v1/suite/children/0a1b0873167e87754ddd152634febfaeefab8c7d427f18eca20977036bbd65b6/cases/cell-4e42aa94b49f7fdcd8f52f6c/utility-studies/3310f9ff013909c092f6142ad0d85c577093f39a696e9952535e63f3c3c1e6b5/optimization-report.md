# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"x_0":424593.40865395125,"x_1":424539.4725096002,"x_2":425656.7421977697,"x_3":425116.2377078887,"y_0":6150053.015187692,"y_1":6151396.765009463,"y_2":6150829.889523674,"y_3":6151070.642458044}
- Objective and constraint observations: {"annual_energy":36.59885863583041}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 1.7264226251281798
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 8467ecda0a6d7640694ed3243ed161346bb6406d8f076ba7a79a967917aa6d43
- Ledger hash: a57b96c8b08ca071602c0bf5f20ed88003d3c4f69d0ebcfc5009a20e8eda6cfb

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
