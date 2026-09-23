# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000160
- Configuration: {"capacity":165.59086036716442,"pet":"hargreaves","recession":0.943477672958211}
- Objective and constraint observations: {"rmse":2.1470511060312574}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 161.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 15b7cfcc4441388a3e5ffb589d12d1225e817fef9563d3b9140c27613d38fc72
- Ledger hash: c81ebf8c106c610db349976910c8f2ffb503d23d22c549f92ddf96a1b3519420

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
