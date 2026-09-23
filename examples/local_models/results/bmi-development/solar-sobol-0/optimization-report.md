# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"heat_loss":27.149401218630373,"loss":0.6707330422941595,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.0199143850484}
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
- Manifest study hash: f6f33ef6a7319ec0264eb259c79c8525df5d087d6fbab8df6473929fa1490f41
- Ledger hash: 215264af15ea77176fa397688e9fa687cc704e79c32fe0d9191e73184ca480da

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
