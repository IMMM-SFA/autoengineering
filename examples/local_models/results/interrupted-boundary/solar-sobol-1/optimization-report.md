# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"heat_loss":37.56953195203096,"loss":0.685922158928588,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.13317631180675}
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
- Manifest study hash: 2564edc8d419c231aeb7430b9db9eefc2db577a9ef63b9a8fdfa537a099f0cb3
- Ledger hash: 2c16e965d82977ed335cf6659ace4aa76ab7f65dfb742890fd34a007c7300e91

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
