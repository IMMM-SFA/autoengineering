# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000078
- Configuration: {"a_scale":1.190452853962779,"heat_loss":39.67473318334669,"io_scale":0.4413407913280307,"irradiance_scale":0.857018928322941,"loss":0.6156019697897136,"rs_scale":0.64840217613881,"rsh_scale":0.5944759205303994}
- Objective and constraint observations: {"rmse":173.61509347185935}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 59f865f003ac40ad3c8787d18c5a587903bf653a2776e3a7685456a40a9ef86a
- Ledger hash: 39e97c5cdd2d8eaf77c0e32008ca291bfca17641f6013deb19b56a11f04accb6

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
