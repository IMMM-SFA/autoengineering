# Leaf River execution map

The physical graph and numerical workflow differ. The YAML describes five components and five
edges. `run_auto_research.make_run_chain` supplies additional arithmetic and runnable inputs.

| Stage | Executed operation | State and units | Graph difference |
| --- | --- | --- | --- |
| Inputs | Inner merge of cached flow and weather dates | Daily mm/day, temperature C | CSV identity and date handling live outside YAML |
| Flow conversion | cfs * 0.0283168 * 86400 / 1947.7 / 1000 | Basin mean mm/day | Fixed drainage area in fetcher |
| PET | Hamon with day of year, latitude 31.7 | mm/day, no carried state | Day of year is a runnable input absent from declared ports |
| Bucket | Add precipitation, remove limited ET, spill above 100 mm | Initial storage 50 mm | Fixed Python call, no general runnable entry |
| Runoff | SCS CN 75 applied to bucket excess | mm/day | Fixed for this investigation |
| Recharge | max(precipitation - actual ET, 0) | mm/day | Hidden arithmetic, includes water also assigned to storage/excess |
| Routing | Causal convolution plus qbase[t] = k*qbase[t-1] + fraction*recharge[t] | Initial baseflow 0.5 mm/day | Recharge supplied outside declared edges/ports |
| Score | RMSE, mean signed bias, NSE, KGE | Flow observations at declared timestamps | Evaluation and acceptance outside physical graph |

Routing discards the convolution tail beyond the requested period. The prototype checks the full
convolution sum, records the finite window, and carries model state continuously from January 2019.
The baseflow recurrence starts at index 1, so recharge at index 0 is unused. Its state is a flow
rather than an explicit reservoir storage. This prevents treating its sum as a conserved basin flux.

The reference driver records arrays in `baseline/baseline.npz` and each campaign's family NPZ files.
The controller records fitting calls in separate family observation ledgers. No comparison flow
enters the fitting objective. Independent metric reconstruction lives in `science.metrics` and
`verify.py`; tests compare it with package metrics using the package's observed/simulated order.
