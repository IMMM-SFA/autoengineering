# Optimization study

## Recommendation

- Feasible: True
- Action: eval-005816
- Configuration: {"alpha":0.6762712002208052,"beta":0.5686583675373367,"cmax":639.6892744963293,"kfast":0.4995787755822284,"kslow":0.018513615304219792,"pet":"hamon","pet_scale":1.461713858970798}
- Objective and constraint observations: {"rmse":1.2208607116059018}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 10000.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 7aec36c03766791ee98ba5b2cab212041cf223b48a87727c7496be26052a8165
- Ledger hash: 6a7a9a2031f60983ce254ad74abfc4b55d6d37904c76d46ff593bbe6f7773a99

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
