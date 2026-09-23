# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000066
- Configuration: {"alpha":0.3146281004700512,"beta":0.1,"cmax":297.0347827909805,"kfast":0.5041086008105218,"kslow":0.0021053929967556014,"pet":"hamon","pet_scale":0.7690328623167488}
- Objective and constraint observations: {"rmse":1.1345313084975843}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 67.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 655b1dc90d8c97933e486675e80e8ce1cb5f25f325bff087feb7dfcc882fae30
- Ledger hash: 5831de35713521cdb503c7516db73af8b376f238cf1c31a7642492769510413b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
