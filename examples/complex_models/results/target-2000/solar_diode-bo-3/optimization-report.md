# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"a_scale":1.0378497857281792,"heat_loss":60.0,"io_scale":3.0,"irradiance_scale":1.0075429227347856,"loss":0.6,"rs_scale":1.8110041227693403,"rsh_scale":2.0}
- Objective and constraint observations: {"rmse":178.90082647304618}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 10.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ef481120d87a33c23e6ed24cd264d59bb9cf1363e035ed820f035f766b63ee46
- Ledger hash: 383e3ed15cf7e793ee86548c83c5f6bff4166d0fe90992479cb011e8fba8dac8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
