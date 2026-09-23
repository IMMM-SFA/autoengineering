# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000042
- Configuration: {"capacity":148.11862022557725,"pet":"hargreaves","recession":0.88512711197915}
- Objective and constraint observations: {"rmse":2.660527123805576}
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
- Manifest study hash: 98ab6f9d786a5c4f79968c4f7ecff1e75c398f6e1dc489f7eef1a958cc44fb5a
- Ledger hash: 1451a546f46dcbe0aaa2c0ef23d59ec88f40d31ac144b4cb06ecfb0f3e60bbb4

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
