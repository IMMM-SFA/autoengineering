# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"model":"rational3","ridge":9.879823531088693e-06}
- Objective and constraint observations: {"rmse":0.20572891139796573}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 3.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: d2a99417375d7ba27212f61ac6dde8a768dac4a16ef783eb50c8a95a08dbf0dc
- Ledger hash: 01206a7992351f82801330a599ae2092d7bb2b2b0c29181a1b32864c45d372be

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
