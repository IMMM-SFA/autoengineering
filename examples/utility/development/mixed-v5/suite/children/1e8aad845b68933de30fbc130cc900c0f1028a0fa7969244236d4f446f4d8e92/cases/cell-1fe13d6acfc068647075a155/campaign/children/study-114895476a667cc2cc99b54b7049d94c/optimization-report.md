# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000011
- Configuration: {"dc_loss_scale":0.9161775841097595,"u0":31.039551282676463,"u1":6.104626894868604}
- Objective and constraint observations: {"bias":14.71325667895788,"correlation":0.9645409684268414,"kge":0.9620731317390969,"nse":0.9288349912651386,"relative_bias":0.009962755593123785,"rmse":138.19366163153012}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 21.275506667792797
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: e27ceb0413658534240a2e8df5c9ab6df4024817878feaa18f9e07d594026679
- Ledger hash: fb84c9819971176e80a6aad63514c6724cf606ca202b2c0ad2a8385a38f411ea

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
