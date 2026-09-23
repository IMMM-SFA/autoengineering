# Optimization study

## Recommendation

- Feasible: True
- Action: eval-001176
- Configuration: {"alpha":0.9334930607315268,"beta":0.35802740841778063,"cmax":553.0287398164846,"kfast":0.4604980749883325,"kslow":0.006621102656066812,"pet":"hamon","pet_scale":1.2008786932256954}
- Objective and constraint observations: {"rmse":1.2399411265032836}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2000.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ab879b2f3a3fa3da4fe188ea020870f8dd21aa7a23ca36c3a46db3f0a68ac3b7
- Ledger hash: 97cb70f55daf4d1729db9d60c10913cf67f5c053c58b64e04dc7b5ac3d010f08

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
