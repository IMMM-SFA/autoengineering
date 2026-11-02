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
- Evaluator seconds: 6.8565316260792315
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3bee615b0626340307b8819a02643b0c3e90c82adb767bea5e569d5f520a3a6b
- Ledger hash: 0168f0d7c9b2dbc2a7f8da9d25f980c5b4da150da8fdd4998e4a76bc14aa6855

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
