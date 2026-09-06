# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"model":"rational3","ridge":5.4988866480231636e-08}
- Objective and constraint observations: {"rmse":0.19598354409531066}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 10d0b7944bb7392e4a85b33d4255b868fbffa407e4d7b115496052ee24beabc8
- Ledger hash: 3b997b4311e8d3896786336e9d21ee2493442487b2ecfc0736414ba8a3374b60

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
