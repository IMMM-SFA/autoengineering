# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000094
- Configuration: {"a_scale":0.9343228571623041,"heat_loss":60.0,"io_scale":0.6544551091993827,"irradiance_scale":1.075248688869527,"loss":0.6,"rs_scale":0.5,"rsh_scale":0.6373595949687693}
- Objective and constraint observations: {"rmse":173.87447830551548}
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
- Manifest study hash: 98abd1dd84f94e2f51719533f5bf6d14d77a57259990dcac4efb39411908f51a
- Ledger hash: e0fedb4771f1f065e4924f5eac0e5d57a96fc221ea4d4a1a03bb8e9028054cd0

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
