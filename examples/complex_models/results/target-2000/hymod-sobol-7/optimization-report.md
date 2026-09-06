# Optimization study

## Recommendation

- Feasible: True
- Action: eval-001874
- Configuration: {"alpha":0.4431226137094199,"beta":1.038091513235122,"cmax":454.28153438927944,"kfast":0.4981772162020207,"kslow":0.001349170527528768,"pet":"hamon","pet_scale":0.9968248950317502}
- Objective and constraint observations: {"rmse":1.244145062404692}
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
- Manifest study hash: a690912f0ed2c75dffc5936c611917f1fa237215a76e6e218cf919af983d37f6
- Ledger hash: d09d213a3585dd61c6b1359fbe7e6868a2bfd049388e90a526a7d1a718db0bed

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
