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
- Manifest study hash: ea7c8b40739ac454267febff90f08883f3a5233ee01def2a7e2b26728495ae76
- Ledger hash: 01206a7992351f82801330a599ae2092d7bb2b2b0c29181a1b32864c45d372be

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
