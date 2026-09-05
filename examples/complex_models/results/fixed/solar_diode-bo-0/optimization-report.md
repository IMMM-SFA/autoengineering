# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000086
- Configuration: {"a_scale":1.0767548813382009,"heat_loss":54.12512021228716,"io_scale":0.3,"irradiance_scale":0.85,"loss":0.6,"rs_scale":0.7226342294448508,"rsh_scale":1.4581879725265932}
- Objective and constraint observations: {"rmse":173.9961788497715}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: ebccc337642fb6b0673d4d0701958cf3ae0d3a5f4bdd50fbbb9fe498b22a193b
- Ledger hash: fb403f9d6e11235f1d340a1528621a4b23ad527ee49f03ade09013351d4cb206

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
