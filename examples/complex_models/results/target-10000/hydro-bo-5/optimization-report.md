# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 7.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: d9595db35533ca6150363c64e801bf37f29931b65c2575508d464a9ada942cc0
- Ledger hash: 8f0d6a2f04fe1488bd709192886163493d980e5a029a71a018e9249bd1f84bda

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
