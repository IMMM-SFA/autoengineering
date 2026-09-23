# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"a_scale":0.9028908483684063,"heat_loss":43.41083140578121,"io_scale":1.3357027321400123,"irradiance_scale":0.9210562103427946,"loss":0.7819669059477746,"rs_scale":1.035137489767569,"rsh_scale":1.232563232319926}
- Objective and constraint observations: {"rmse":178.84804051742753}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 669fc8ee9e947288a9d83108c118ae0e6775b07765ae1f61d5332390d4389ca3
- Ledger hash: 86b330c669dd0927b30f5bc53eba7b2d9efb0108ef40ff6db184f3bd35128f6c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
