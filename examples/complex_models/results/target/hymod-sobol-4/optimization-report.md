# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000047
- Configuration: {"alpha":0.8307905580848455,"beta":0.46636765850707884,"cmax":499.8240460593429,"kfast":0.5460615351796151,"kslow":0.05225144132741058,"pet":"hargreaves","pet_scale":1.340285126119852}
- Objective and constraint observations: {"rmse":1.2943705306550526}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 200.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 9aed716ca8adbf25a163e9f5562c5527fd4a231fc93b7c0c5650aed1ebcb5aa0
- Ledger hash: 9d53cd972f8288056b441eeff74d7f2a6cb06e3304be437a33984325b8dd87e0

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
