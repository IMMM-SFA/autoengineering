# Optimization study

## Recommendation

- Feasible: True
- Action: eval-002465
- Configuration: {"alpha":0.6432347399130632,"beta":1.0383373005823178,"cmax":744.884655405791,"kfast":0.5450936880507918,"kslow":0.003950539818598253,"pet":"hargreaves","pet_scale":1.3877382769604543}
- Objective and constraint observations: {"rmse":1.3054818651518167}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4314.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 5c928b3975a47f7be5f6fd57c9903ededd62991e5725b4ac70e5b1e0293c1112
- Ledger hash: 16777fe357db710e247f0c23155e13a44715ee991232f5a6174e2f48a0b5f66d

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
