# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000207
- Configuration: {"capacity":184.2400454171002,"pet":"hargreaves","recession":0.9374590031802654}
- Objective and constraint observations: {"rmse":2.158993279097928}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 208.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: d315afd1091a6808b3fc8ee5d545f2af94245eface86d181bf37d875a8085559
- Ledger hash: 86332d91cdc4c1521a309f85d3fcd64ca2cba905b809fe204932d2ad279a11b6

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
