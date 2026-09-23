# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"capacity":153.2512424699962,"pet":"hargreaves","recession":0.9336902514100074}
- Objective and constraint observations: {"rmse":2.252317950717041}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 60.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 70c10081f478bdcc2d47ffb161ec8bc1bf0be5cd38203fee5f271b8df7c4e45a
- Ledger hash: bfd9059be3c3111bd925562cdf85cce64af7556884b557a57df1e1e43204c54f

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
