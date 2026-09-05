# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000032
- Configuration: {"capacity":191.2467917674221,"pet":"hamon","recession":0.9264042558155103}
- Objective and constraint observations: {"rmse":2.4865417070221314}
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
- Manifest study hash: 1f7a19469e0b644dac86b5cb248968220d4503edf0ab6928b8a74ab4f7d5b417
- Ledger hash: d8fd33c0a2f64c9f14650662b06946ae3dce5d24c929333c19616d71bee498bb

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
