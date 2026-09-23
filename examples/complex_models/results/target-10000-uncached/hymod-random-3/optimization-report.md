# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000970
- Configuration: {"alpha":0.3233288957652412,"beta":0.12138022591844433,"cmax":213.32940086403383,"kfast":0.5226537986533167,"kslow":0.007541083152463684,"pet":"hargreaves","pet_scale":0.7768074121014692}
- Objective and constraint observations: {"rmse":1.2321137319643258}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2424.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 35c5e2a2104fc0bc269b9c5732888a50358eb14fda899361ef71d12500eef4ce
- Ledger hash: d4e49cb10310843584b27c105752a6b84d1df7040864545e1a5442e1a0dbce6a

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
