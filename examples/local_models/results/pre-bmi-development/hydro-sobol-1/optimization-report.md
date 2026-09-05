# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"capacity":66.96133969351649,"pet":"hargreaves","recession":0.9431581432931124}
- Objective and constraint observations: {"rmse":2.6076476742303027}
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
- Manifest study hash: b95bb9ca5b59a7603da7359995fd400e3cb77a0a32591d01bd86d4e181d53576
- Ledger hash: f436f0e233d3314359264767eb61a5f03c6bb4a0e08410a34f7b164e5480aac8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
