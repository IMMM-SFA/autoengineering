# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"dc_loss_scale":0.9181207608391662,"u0":33.89557317434781,"u1":7.676257100093625}
- Objective and constraint observations: {"bias":26.262527739209403,"correlation":0.9654761095387081,"kge":0.9611391880375355,"nse":0.9284782828344323,"relative_bias":0.017783088464538983,"rmse":138.5395705820532}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 19.486286208964884
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 9030adec313dcd23d6b920d7dee0ff21c6f5b9b9e14144cb136bbb1ce0eec4b2
- Ledger hash: d753e86cdf7a29b7b2964a12bf26f0cd19856bb3814022ccc713d17b578fd0a3

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
