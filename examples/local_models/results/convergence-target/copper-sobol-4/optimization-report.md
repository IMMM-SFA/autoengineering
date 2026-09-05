# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"model":"rational3","ridge":5.4988866480231636e-08}
- Objective and constraint observations: {"rmse":0.19598354409531066}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 16c8116388691c4eaa9bc898ee78d3747c412f943cbb7cb927d256678a1f07a1
- Ledger hash: 2e2a13cad59d646df60d3cfd5d09cc764f5a6268d9964bfeaab2f2cb2266edf9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
