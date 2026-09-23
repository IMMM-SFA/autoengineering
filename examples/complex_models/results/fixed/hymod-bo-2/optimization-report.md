# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000092
- Configuration: {"alpha":0.3695783384459436,"beta":0.1,"cmax":1000.0,"kfast":0.4796236449203565,"kslow":0.0018693531382392235,"pet":"hargreaves","pet_scale":0.5}
- Objective and constraint observations: {"rmse":1.1238470502422406}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: f7437de3cd3f906cfd140060eb1d2a8d9d6b192b4a410662375aebc628a24333
- Ledger hash: 2f17076b466faba9300742dae743916acb4a51dbbd077d92b70c057cebc7d692

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
