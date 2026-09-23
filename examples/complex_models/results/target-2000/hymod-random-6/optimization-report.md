# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000025
- Configuration: {"alpha":0.701643501573957,"beta":0.3977483359625235,"cmax":437.9806658008998,"kfast":0.49288389755525097,"kslow":0.004840733759298614,"pet":"hamon","pet_scale":1.2745671719621212}
- Objective and constraint observations: {"rmse":1.2004920763963522}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2000.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 7f836abe99d1d4e786d183174ddd01a29edbc1ef76c8d1759830135017d2c813
- Ledger hash: aaafb27f7a282371b99d3d0cc293b9b552497f31ecba017faecf9af10e6a5ad2

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
