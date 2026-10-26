# Optimization study

## Recommendation

- Feasible: True
- Action: default
- Configuration: {"k_base":0.85,"recharge_frac":0.1,"uh_peak":3}
- Objective and constraint observations: {"bias":1.166833561246644,"kge":0.2715076757145758,"nse":0.08204133776209976,"rmse":2.8035561280232284}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 917bda2b4efbc13828db181976d8485ef9ff353ba4beeb086c1852c4ca19575e
- Ledger hash: afb6da317d763b8b35896075ddc7f99505b0117ddf71ab53938bacf5b17e0f9e

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
