# Optimization study

## Recommendation

- Feasible: True
- Action: eval-001205
- Configuration: {"alpha":0.30972178494557734,"beta":0.1096609964966774,"cmax":297.77672740369894,"kfast":0.5327763080596924,"kslow":0.0022345069695985445,"pet":"hamon","pet_scale":0.7196095641702414}
- Objective and constraint observations: {"rmse":1.1782878935588688}
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
- Manifest study hash: 2e8ed5833ebb8f3054cc1795e644c3629af2c9155598ffbb20f54a93a91f855e
- Ledger hash: ca185af5f6ebda02ec6b1c53e6cbf2f212d9df5ffc6a29ca08fcd6c45cca8bda

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
