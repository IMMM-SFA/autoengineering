# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000061
- Configuration: {"alpha":0.3570704047128711,"beta":0.1,"cmax":247.637118079643,"kfast":0.4799280473637233,"kslow":0.0012150020272434184,"pet":"hamon","pet_scale":0.9218753907103607}
- Objective and constraint observations: {"rmse":1.128073589616546}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 62.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: cfc50209ca7b2c59913a381ab1c2361abedcf50df82bb58981fec5bd4270db40
- Ledger hash: 0534689e57ac30f1cb85f87b9b94b44adbf5bad8a8aaa880663bef7a65cdcaf3

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
