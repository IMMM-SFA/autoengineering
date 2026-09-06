# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"model":"rational3","ridge":1.0191398010066943e-06}
- Objective and constraint observations: {"rmse":0.1965047198163146}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 7.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 255f9c1312684fc8c6d58a6aef6e3211ae05bd5af23c3fb9d038c20285d283a2
- Ledger hash: 9ad3f4a8f934305ef086db61c3345525f129962dae490fdc375cd1d39b80970f

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
