# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"model":"rational3","ridge":4.546461797239275e-07}
- Objective and constraint observations: {"rmse":0.1960724758596784}
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
- Manifest study hash: 58cd5bea72445f90e05d45c42c7daf84fd126d8beb648af213682dc16832ae7a
- Ledger hash: e38698f35d4b39e260871fd35044a84874cab2e76b4a481e8137a1323490f245

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
