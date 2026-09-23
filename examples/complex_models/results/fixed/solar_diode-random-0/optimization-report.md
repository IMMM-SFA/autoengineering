# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000090
- Configuration: {"a_scale":0.8723161903513361,"heat_loss":33.56184692894746,"io_scale":0.3212190755724867,"irradiance_scale":0.952184127163681,"loss":0.6865927818828873,"rs_scale":0.6736354322617133,"rsh_scale":1.002031455846911}
- Objective and constraint observations: {"rmse":174.35142424318758}
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
- Manifest study hash: 41ed2a760fa2405306289ce769a5ae3979616835b382b8e6bf348f3ccf2c1ea6
- Ledger hash: b32ecf20f9a4d5e615e0352eb7b21ad7ccb3d4fd4176d55e56f09d90520f6d71

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
