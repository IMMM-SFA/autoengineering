# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"a_scale":0.9900538973402662,"heat_loss":38.06204256917937,"io_scale":0.4768131960448094,"irradiance_scale":0.9376790958582358,"loss":0.6306728763986301,"rs_scale":1.8941513504342709,"rsh_scale":1.5524730445670063}
- Objective and constraint observations: {"rmse":180.53873600008328}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 8.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: b09aa753c246aa437afe12caed975f3cbd26c169ec37e90b4f2f1947e9f305d6
- Ledger hash: b198a314f527255f8273638cef25022bef494be2c9966437128d9aa66e8d8f49

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
