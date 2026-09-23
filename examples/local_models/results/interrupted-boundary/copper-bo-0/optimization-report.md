# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"model":"rational2","ridge":1.4742077650713794e-07}
- Objective and constraint observations: {"rmse":0.3898933419393808}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 89113bdfa9e4dc39eee6ed523fc98c7986cd2e6b2fe942bf5bc553be85f7004c
- Ledger hash: ec0456350098ae8debabb3e07e91ee5906c5c05b9fcb1d1e9ef87675a7449c1d

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
