# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000167
- Configuration: {"capacity":176.91644948563257,"pet":"hargreaves","recession":0.9493520754015514}
- Objective and constraint observations: {"rmse":2.0879260543352087}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 168.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ddcf9a77b5f6c11e3aa23f8dfa85565a1d9d5e26a1031200dc465d3cd9bd2e5a
- Ledger hash: 761afdb13acf175ae34e40c5d5718918e90a7bf7197a8ef4ec2ebcb2a1d72c1f

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
