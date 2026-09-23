# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000094
- Configuration: {"alpha":0.38524510637815146,"beta":0.1,"cmax":263.2345724322424,"kfast":0.4920869578881816,"kslow":0.001708167911619523,"pet":"hamon","pet_scale":1.032641672453452}
- Objective and constraint observations: {"rmse":1.08407348852375}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 63d838e4599f68561bd308c9ba2cfc850f79fb056906c14ce9ebbb47dc5e7e7e
- Ledger hash: a3c12c5201d89b59e2b3dcf1ec574bac26142072fea96699de7d022eaa874333

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
