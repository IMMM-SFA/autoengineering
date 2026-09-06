# Optimization study

## Recommendation

- Feasible: True
- Action: eval-002280
- Configuration: {"capacity":148.9891308179309,"pet":"hargreaves","recession":0.9476344488417228}
- Objective and constraint observations: {"rmse":2.151738594126747}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2281.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 1d3b586e1dd62913432e6529030d80a84c01c24961a91f9540b98350e2c07932
- Ledger hash: da0bb529e8c055838a271f7e70648e2d209ae0d4dd4e08ecf8d9cd54fd5d574a

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
