# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"model":"rational3","ridge":3.9455864640038066e-06}
- Objective and constraint observations: {"rmse":0.19971166313321398}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 7.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 938bef7ba88725dfa36d2e781a276e7d07a993ecb874136376277b30e6b481af
- Ledger hash: f0b156b13a1dd83295be508fb7c45ea471b24059f5e535adc4b015da1d667720

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
