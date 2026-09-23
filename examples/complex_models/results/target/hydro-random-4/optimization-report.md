# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000198
- Configuration: {"capacity":176.3343141701978,"pet":"hargreaves","recession":0.9423770663279165}
- Objective and constraint observations: {"rmse":2.1363234888585785}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 199.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3ac14f912358c8a87a7ea1bf2ab967d99b35bfe19326b99b8786084bbd9557af
- Ledger hash: 5c6fa35fcaf11743875519283b1d43d1b3f2fca4a118cfe5c10b464ff3f3ecfa

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
