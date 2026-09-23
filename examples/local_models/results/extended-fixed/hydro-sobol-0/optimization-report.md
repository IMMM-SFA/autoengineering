# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000022
- Configuration: {"capacity":118.60311886295676,"pet":"hamon","recession":0.9411777024157345}
- Objective and constraint observations: {"rmse":2.5898775711961144}
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
- Manifest study hash: 08d1cb221d3bc17230f3e72420c032ee333a8d7b785a13cda50d7a50f40e036c
- Ledger hash: f50b9f74e0e0c84aeea1980fd3170aeced3509e2f7160f6c4882abd9d6295249

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
