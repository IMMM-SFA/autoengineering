# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000157
- Configuration: {"alpha":0.34728496173431445,"beta":0.1,"cmax":334.65677205786733,"kfast":0.5029475452010764,"kslow":0.003108003725991348,"pet":"hargreaves","pet_scale":0.6583925212627095}
- Objective and constraint observations: {"rmse":1.136279936576662}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 158.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 8c5086a6c484701be632d376f469f85c22fa53704d0679ee304efff0fd499d77
- Ledger hash: 49ca1112ab622279ac9d0d3ab499192a58eb4d24d79cf8c7afffa21160fa5a95

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
