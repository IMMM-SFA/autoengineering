# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000012
- Configuration: {"a_scale":0.8244353897869587,"heat_loss":59.809731929562986,"io_scale":1.9856465922740685,"irradiance_scale":1.0455582499504088,"loss":0.7545407265890389,"rs_scale":0.5100200366402522,"rsh_scale":1.0126050356945135}
- Objective and constraint observations: {"rmse":181.21828026071273}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 13.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: fb66ced729bd83871185aa50aeaee827f591cb4acb40f0899e563896354ecbc0
- Ledger hash: f9d070252bf0d79cef5110f8784712c8afcfdacbbcd37cdc128f8f7f77c1067f

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
