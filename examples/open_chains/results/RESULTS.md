# Open model chain results

## Independently maintained model chains

These are finite component-swap comparisons, not extra RMSE domains in the frozen Bayesian benchmark. All three execute their real upstream software locally. These fixed candidate lists are independent of the separate 2000-call target experiment.

| Chain | Selection objective (minimize) | Baseline | Selected | Selection gain | Evaluations | Seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| solar | selection AC power RMSE (kW) | 269.766 | 267.507 | 2.25861 | 4 | 0.995 |
| wind | negative annual energy (GWh) | -142.354 | -143.237 | 0.88313 | 3 | 1.879 |
| hybrid | negative energy revenue (USD) | -1.06197e+07 | -1.08159e+07 | 196173 | 3 | 46.687 |

Solar selected `steady_faiman_ablation` using 2018. On 2019, AC RMSE changed from 241.8799 to 239.8996 kW. This is conditional on measured POA and the declared jointly observed subset. Implausible 2019 module-temperature readings invalidate that intermediate diagnostic, without changing the power score. The test period was inspected during example development and is a temporal holdout, not blinded external validation.

Wind selected `topfarm_20`. On the finer five-degree grid, modeled energy changed from 143.0625 to 143.1247 GWh. The finer-grid gain is 0.0622 GWh. This is a numerical sensitivity check, not observed plant improvement. Bounded feasible iterates do not establish convergence.

Hybrid selected `cbc_buffered_soc`. 1 policy was excluded by the unchanged numerical/physical screens. Gross revenue omits capital and degradation costs and terminal SOC value. Perfect 24-hour foresight and a separate price-year scenario are assumptions, not forecast skill or realized income.

| Chain | Candidate | Status | Inner optimizer / physical diagnostics |
| --- | --- | --- | --- |
| solar | baseline | evaluated | See sensor QA and selection/test coverage |
| solar | steady_faiman_ablation | evaluated | See sensor QA and selection/test coverage |
| solar | sapm_module | evaluated | See sensor QA and selection/test coverage |
| solar | faiman_u0_30 | evaluated | See sensor QA and selection/test coverage |
| wind | baseline | evaluated | not_run; 0 wake function and 0 gradient evaluations |
| wind | topfarm_5 | evaluated | not_converged; 7 wake function and 6 gradient evaluations |
| wind | topfarm_20 | evaluated | not_converged; 23 wake function and 21 gradient evaluations |
| hybrid | baseline | evaluated | SOC 10.000-90.823%; final 11.453%; screen passed |
| hybrid | cbc_dispatch | infeasible | SOC 10.000-91.234%; final 10.709%; Battery SOC screening range [9, 91] exceeded: [10.000004674858543, 91.23432861631625] |
| hybrid | cbc_buffered_soc | evaluated | SOC 10.000-86.321%; final 10.906%; screen passed |

Sources, commands, limits and raw evidence are linked from [the open-chain README](../../open_chains/README.md). Each result includes source, environment and artifact hashes. Summarization recomputes objectives from saved arrays. The [older 200-call report](../../complex_models/history/a262556/RESULTS-200.md) is preserved.
