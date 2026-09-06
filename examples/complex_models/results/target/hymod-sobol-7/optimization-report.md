# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000034
- Configuration: {"alpha":0.33536430746316903,"beta":1.2765930834226311,"cmax":436.3090339541675,"kfast":0.5338111110031605,"kslow":0.002372080917103917,"pet":"hamon","pet_scale":0.933834589086473}
- Objective and constraint observations: {"rmse":1.3168303638507015}
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
- Manifest study hash: 0b1a5f7182c6dc6a176cb17f08fb6a3aee6d62c9214994d6f33a5c8c0230b25c
- Ledger hash: 7cecd5fbd296e7fecbf9abe94929fdf9e373c6a55a497d63191f856569042fc9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
