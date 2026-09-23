# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000008
- Configuration: {"heat_loss":49.915395676492835,"loss":0.667794243851693,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.6803212316816}
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
- Manifest study hash: 521bc5f5fe4a2ae9b44cf508f6f486cd13b4b259f144f7070b9c9ce588b8ee5f
- Ledger hash: 47a4b560bb0c3946c14c36ebc021861c5b833a077405d201bed9a311075cd7a8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
