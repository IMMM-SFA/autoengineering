# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"source_current":0.04670589206740261}
- Objective and constraint observations: {"source_power":0.21630366857301633}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 5.033223418518901
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 340203f44cabd655c9c5912951d2a3b878b487f7c9a43981ef35a619fdbcc03d
- Ledger hash: 7ffc759b7122897df1e07e935ef01ee100deca7c55e4cab0cfc66c2093864822

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
