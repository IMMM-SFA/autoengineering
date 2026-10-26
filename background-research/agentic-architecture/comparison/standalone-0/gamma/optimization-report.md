# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"gamma_scale":1.5,"gamma_shape":2.5,"k_base":0.92,"recharge_frac":0.03}
- Objective and constraint observations: {"bias":0.005509299909219862,"kge":0.5553855667363086,"nse":0.448585875569402,"rmse":2.172884471271197}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 16.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: fdc6917d9e8487eebd0f20edf054b2beac6a67b04e12fe92f2737fcc6882b8f9
- Ledger hash: 7dc9872ef3e1c925caab55ac2aaa6f4d2bb80e4d7b568bbae9efce27e66d65b7

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
