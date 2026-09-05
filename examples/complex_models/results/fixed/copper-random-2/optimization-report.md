# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000013
- Configuration: {"model":"rational3","ridge":1.5349820686061922e-07}
- Objective and constraint observations: {"rmse":0.19597480608250212}
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
- Manifest study hash: 6dd444e66918802998035885bf4dc254f7eac816e82d0758f83c1fcb5c6599ef
- Ledger hash: be1d99f323034bb6973f775ef1583d80a831b88b63841c82eb793d2087a96910

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
