# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000063
- Configuration: {"heat_loss":56.23782573766727,"loss":0.646127421341101,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0964109792146}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 93176f3eb25477e76d7a585884b0e90eeef6c4cf451b9212d77ff85ee34276c7
- Ledger hash: e23d25042b361ec761619f52f880c6fa4fd1febcc1c4aa7ffe9da0850d3f43dc

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
