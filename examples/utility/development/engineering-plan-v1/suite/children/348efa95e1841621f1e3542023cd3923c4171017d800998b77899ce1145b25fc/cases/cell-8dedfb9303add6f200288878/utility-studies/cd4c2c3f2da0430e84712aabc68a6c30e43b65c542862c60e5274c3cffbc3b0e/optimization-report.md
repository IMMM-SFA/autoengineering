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
- Evaluator seconds: 5.894776334054768
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 340203f44cabd655c9c5912951d2a3b878b487f7c9a43981ef35a619fdbcc03d
- Ledger hash: 30f34b307f3d233a0329fa2f456105cec7fa21a326c8f58ceaeb8c76eb8e08c5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
