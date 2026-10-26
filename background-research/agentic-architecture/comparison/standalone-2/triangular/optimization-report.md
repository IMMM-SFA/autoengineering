# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"k_base":0.8099801635742188,"recharge_frac":0.04457894548773765,"uh_peak":3}
- Objective and constraint observations: {"bias":-0.5243216075962523,"kge":0.46806291876626294,"nse":0.48973817397633634,"rmse":2.090230749969821}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 16.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 917bda2b4efbc13828db181976d8485ef9ff353ba4beeb086c1852c4ca19575e
- Ledger hash: d3521a44b4dbe7047c6ee4f632936b269b0de83fb499fa7b5090caa593556997

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
