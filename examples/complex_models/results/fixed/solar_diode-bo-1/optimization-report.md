# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000042
- Configuration: {"a_scale":1.2,"heat_loss":60.0,"io_scale":0.9514325376235723,"irradiance_scale":0.85,"loss":0.6521355880434374,"rs_scale":0.5,"rsh_scale":0.5}
- Objective and constraint observations: {"rmse":173.43488404277312}
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
- Manifest study hash: 02d782a92853bbdd5e2859ab2bfed1f477692dee556e5babd1d97748f64c3766
- Ledger hash: 98d9b642e046354bc3f490e7e7d302fbab2753a2d2e81c9b5767ddfc7cb8af81

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
