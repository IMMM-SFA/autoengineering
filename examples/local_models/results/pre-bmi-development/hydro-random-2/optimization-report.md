# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"capacity":156.27213061689056,"pet":"hargreaves","recession":0.8649656384990743}
- Objective and constraint observations: {"rmse":2.7875932684277474}
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
- Manifest study hash: 76b3b5d948163e7e8744bfa27ef3448ae2b59e02a35f373f5e59fa32c3e4335c
- Ledger hash: 12e88893ec28b1d0d4cba67ecbb0cee0270af8f0a97732513a23623ce68b10e6

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
