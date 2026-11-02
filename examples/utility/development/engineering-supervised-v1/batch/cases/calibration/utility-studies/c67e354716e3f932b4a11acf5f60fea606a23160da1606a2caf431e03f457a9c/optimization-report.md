# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"source_current":0.03456821138970554}
- Objective and constraint observations: {"source_power":0.11854625333653068}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 4.516775958240032
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 60703345b430b0515798405672edce994279a699c2a13d330945df2ef364c09a
- Ledger hash: 45b31f1c60d768c6964183ca07c3f917430464cfe82e8ee73b7b6587b77652c1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
