# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"capacity":153.2512424699962,"pet":"hargreaves","recession":0.9336902514100074}
- Objective and constraint observations: {"rmse":2.252317950717041}
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
- Manifest study hash: d241639910be588ed96367ab4384d61cb7d6a12cdb24947d67e912b34dba8a37
- Ledger hash: 02c19d45862d6defac4330f016dfcdaf9d66137bd79ecc79762e5a4745165dba

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
