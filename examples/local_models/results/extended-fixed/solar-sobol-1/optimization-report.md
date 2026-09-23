# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"heat_loss":37.56953195203096,"loss":0.685922158928588,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.13317631180675}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 5bb8cef26b354c7f6e6ef1c08342c939d25424c38171c1a86afec7be4d8674b4
- Ledger hash: 6ffa9faab4a6f62ab5a5e7fb3621d84f57baf4c4a821e8f441550c703d8f90e0

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
