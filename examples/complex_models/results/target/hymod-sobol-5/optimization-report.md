# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000165
- Configuration: {"alpha":0.4908276163041591,"beta":0.7203028720803558,"cmax":451.2284647121245,"kfast":0.5320801138877869,"kslow":0.026173831221881123,"pet":"hamon","pet_scale":1.4797468157485127}
- Objective and constraint observations: {"rmse":1.3089552139106073}
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
- Manifest study hash: 052f6d3b4c801b5d8b3f4736500c93b2ff6623200f550cb558c3df2e609733a5
- Ledger hash: 55978ee818cf8e7d733a93b8d962ef0432b006602b9d3a56d88b25676ab985c9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
