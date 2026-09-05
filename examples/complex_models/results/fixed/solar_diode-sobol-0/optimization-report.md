# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000067
- Configuration: {"a_scale":1.068979225307703,"heat_loss":42.07098368089646,"io_scale":1.521731995027705,"irradiance_scale":0.9606384418904781,"loss":0.6137316591572016,"rs_scale":0.7326501597725643,"rsh_scale":0.7189674468824975}
- Objective and constraint observations: {"rmse":174.22817387332793}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 68052fff048945646d3ccba69154265ac97ab51b06555105260a530514fd80ea
- Ledger hash: 87be86ee3d025223d29c4635ae23f7105f51c545f6faf8e36dd9e92b441664dc

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
