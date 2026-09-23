# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"heat_loss":19.75890921894461,"loss":0.6400053611956537,"temperature":"ross"}
- Objective and constraint observations: {"rmse":180.00165734869987}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 23fe08a90210229bd2c4de8e08316ca499e89d3971473b1aec56e3ba0647edda
- Ledger hash: 3f57bc041aeb90027b68cf2adb9ce057cb66fef37cfca74943fbb068aad70707

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
