# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000025
- Configuration: {"alpha":0.701643501573957,"beta":0.3977483359625235,"cmax":437.9806658008998,"kfast":0.49288389755525097,"kslow":0.004840733759298614,"pet":"hamon","pet_scale":1.2745671719621212}
- Objective and constraint observations: {"rmse":1.2004920763963522}
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
- Manifest study hash: 6e3936927644e75b42be732339d7d0c606d17b0ab8b433c812e0ceeb5f7bfa96
- Ledger hash: adbd1edf6a32f96ebe9b71a3020532bb0ce92beedda104e8e38c09dae48f8a6b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
