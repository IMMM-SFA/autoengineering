# Model examples: 96-call checkpoints and 2000-call targets

Completed 45 fixed studies (4320 calls) and 75 target studies (24972 retained calls). Verified 27 historical fixed prefixes, 45 older target prefixes, and 75 historical target trajectories originally capped at 200. Verified 46 uncached extension prefixes through the applicable cap.

The seven-parameter HYMOD and single-diode chains extend hydrology and solar modeling. The original three models, datasets, splits and accuracy targets stay unchanged. The new models reuse existing datasets; they add model complexity, not independent data or new domains.

## Sensor QA correction

All 639 cached module-temperature readings equal 3276.7 C and are unusable. Measured-temperature RMSE/ranking and earlier claims of observed intermediate temperature truth are withdrawn. Frozen raw diagnostics remain for provenance, but are not valid accuracy evidence. The AC-power objectives use simulated module temperature, plausible ambient-temperature and irradiance forcing, and measured AC power. No rows, splits, targets or primary optimization results were changed. Sensor range screening does not certify their accuracy.

## Fixed-budget comparison

Median held-out RMSE across seeds 0-2. Each row uses checkpoints of the same search trajectory; these are paired observations, not independent replications. Only validation error selects recommendations. Lower is better. Hydrology uses mm/day, solar uses kW, and copper retains the source's unresolved native unit multiplier.

| Model | Method | Test at 12 | Test at 24 | Test at 48 | Test at 96 | Validation at 96 | Study seconds at 96 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hydro | random | 2.8250 | 2.8250 | 2.8141 | 2.8141 | 2.4865 | 6.92 |
| hydro | sobol | 2.8271 | 2.8093 | 2.8093 | 2.8179 | 2.2707 | 6.72 |
| hydro | bo | 2.8839 | 2.8839 | 2.8839 | 2.8839 | 2.0660 | 18.43 |
| solar | random | 116.8577 | 123.3546 | 122.8638 | 122.8638 | 175.0851 | 6.37 |
| solar | sobol | 118.9642 | 119.6787 | 120.2928 | 120.2928 | 175.1134 | 6.56 |
| solar | bo | 121.9417 | 121.9401 | 122.0450 | 122.0261 | 175.0775 | 92.18 |
| copper | random | 0.2489 | 0.2479 | 0.2479 | 0.2479 | 0.1960 | 6.54 |
| copper | sobol | 0.2477 | 0.2477 | 0.2477 | 0.2479 | 0.1960 | 5.82 |
| copper | bo | 0.2479 | 0.2479 | 0.2479 | 0.2479 | 0.1960 | 37.93 |
| hymod | random | 2.8613 | 2.7309 | 2.7309 | 2.6758 | 1.4167 | 7.69 |
| hymod | sobol | 2.6846 | 2.6846 | 2.5527 | 2.5505 | 1.3248 | 7.39 |
| hymod | bo | 2.7735 | 2.9156 | 2.7403 | 2.5731 | 1.1238 | 24.67 |
| solar_diode | random | 135.6157 | 128.7039 | 128.7039 | 128.4311 | 174.4857 | 24.61 |
| solar_diode | sobol | 124.5879 | 123.8332 | 121.3327 | 124.6517 | 174.2282 | 21.27 |
| solar_diode | bo | 124.5879 | 124.5879 | 122.9228 | 124.9850 | 173.8745 | 33.93 |

Median validation RMSE across the same seeds:

| Model | Method | Validation at 12 | Validation at 24 | Validation at 48 | Validation at 96 |
| --- | --- | ---: | ---: | ---: | ---: |
| hydro | random | 2.7876 | 2.7876 | 2.4972 | 2.4865 |
| hydro | sobol | 3.4011 | 2.5899 | 2.5899 | 2.2707 |
| hydro | bo | 2.0660 | 2.0660 | 2.0660 | 2.0660 |
| solar | random | 175.6803 | 175.4546 | 175.0851 | 175.0851 |
| solar | sobol | 176.1332 | 175.2584 | 175.1134 | 175.1134 |
| solar | bo | 175.0776 | 175.0776 | 175.0775 | 175.0775 |
| copper | random | 0.1963 | 0.1960 | 0.1960 | 0.1960 |
| copper | sobol | 0.1960 | 0.1960 | 0.1960 | 0.1960 |
| copper | bo | 0.1960 | 0.1960 | 0.1960 | 0.1960 |
| hymod | random | 1.6944 | 1.5993 | 1.4582 | 1.4167 |
| hymod | sobol | 1.6417 | 1.6417 | 1.3656 | 1.3248 |
| hymod | bo | 1.5052 | 1.3678 | 1.2994 | 1.1238 |
| solar_diode | random | 176.1847 | 175.3630 | 175.3630 | 174.4857 |
| solar_diode | sobol | 176.3502 | 175.1064 | 174.5390 | 174.2282 |
| solar_diode | bo | 176.3502 | 175.1064 | 173.9397 | 173.8745 |

## Calls to the frozen validation target

Five separate seeds (3-7), stopping at the target, backend termination or 2000 attempts. Existing targets are unchanged. Each new target is 1.05 times the lowest validation RMSE in its fixed matrix, frozen before these five seeds. This is a development quality target, not global convergence.

| Model | Target | Method | Reached | Calls by seed 3-7 | Median successful calls | Mean calls consumed | Median study seconds | Median test RMSE |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| hydro | 2.1693 | random | 4/5 | 161, 199, 168, >2000, 89 | 164.5 | 523.4 | 8.022 | 2.8513 |
| hydro | 2.1693 | sobol | 5/5 | 133, 324, 368, 208, 337 | 324 | 274.0 | 16.732 | 2.8549 |
| hydro | 2.1693 | bo | 5/5 | 6, 6, 7, 6, 7 | 6 | 6.4 | 0.428 | 2.8839 |
| solar | 183.8314 | random | 5/5 | 5, 2, 11, 3, 2 | 3 | 4.6 | 0.133 | 120.6910 |
| solar | 183.8314 | sobol | 5/5 | 3, 1, 4, 2, 4 | 3 | 2.8 | 0.134 | 137.8004 |
| solar | 183.8314 | bo | 5/5 | 3, 1, 4, 2, 4 | 3 | 2.8 | 0.138 | 137.8004 |
| copper | 0.2058 | random | 5/5 | 1, 8, 3, 7, 2 | 3 | 4.2 | 0.123 | 0.2513 |
| copper | 0.2058 | sobol | 5/5 | 4, 1, 5, 1, 12 | 4 | 4.6 | 0.164 | 0.2492 |
| copper | 0.2058 | bo | 5/5 | 4, 1, 5, 1, 7 | 4 | 3.6 | 0.175 | 0.2492 |
| hymod | 1.1383 | random | 0/5 | >2000, >2000, >2000, >2000, >2000 | NA | 2000.0 | 322.139 | 2.5401 |
| hymod | 1.1383 | sobol | 0/5 | >2000, >2000, >2000, >2000, >2000 | NA | 2000.0 | 384.328 | 2.5591 |
| hymod | 1.1383 | bo | 5/5 | 158, 62, 146, 67, 313 | 146 | 149.2 | 36.012 | 2.6660 |
| solar_diode | 182.1066 | random | 5/5 | 3, 5, 8, 3, 13 | 5 | 6.4 | 1.081 | 137.1321 |
| solar_diode | 182.1066 | sobol | 5/5 | 13, 9, 1, 5, 4 | 5 | 6.4 | 1.056 | 114.9054 |
| solar_diode | 182.1066 | bo | 5/5 | 10, 10, 1, 5, 4 | 5 | 6.0 | 1.079 | 115.8841 |

A >2000 value is censored, not convergence at 2000. Successful-only medians exclude capped or terminated runs. Mean calls consumed is a restricted computational cost and cannot alone rank methods with unequal success rates. Missing scores are not silently dropped. Individual JSON records retain actual termination reasons.

The user reduced the cap during the 10000-call run. 53 studies are retrospective prefixes ending at the first target hit or call 2000. Their recommendations and held-out scores use only those prefixes; their timings end at the retained call. Raw longer runs remain in target-10000. The other 22 studies ran with a 2000-call budget. The preserved source recorded 49,093 calls; 34,595 later calls are excluded from this analysis. See ../PROTOCOL-2000.md.

## Timing, adaptive actions and failures

Study time includes optimization and durable bookkeeping. Model time covers BMI evaluation, including model initialization and any copper training fit. Imports, input loading, backend construction and held-out scoring are outside the study timer. Runs are sequential with one Torch CPU thread. These are single-machine measurements; model-dependent cost and bookkeeping matter alongside evaluation counts.

The extended target experiment uses a benchmark-local cache of exact-byte parsed ledger records. File integrity, artifact and controller checks still run on every read. The interrupted uncached extension is preserved separately and its observations are verified as exact prefixes through the applicable cap. Fixed-budget timings use the uncached implementation and should not be directly compared with cached target-study timings.

Background test validation overlapped part of the reduced target experiment. Timing comparisons are descriptive rather than controlled throughput measurements.

| Experiment | Model | Method | Median model seconds | Median optimizer/controller seconds | Adaptive BO actions | Fallback actions | Failed attempts |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| fixed | hydro | random | 1.531 | 5.390 | 0 | 0 | 0 |
| fixed | hydro | sobol | 1.534 | 5.212 | 0 | 0 | 0 |
| fixed | hydro | bo | 1.587 | 16.845 | 28 | 248 | 0 |
| fixed | solar | random | 1.215 | 5.160 | 0 | 0 | 0 |
| fixed | solar | sobol | 1.280 | 5.282 | 0 | 0 | 0 |
| fixed | solar | bo | 1.315 | 90.806 | 145 | 131 | 0 |
| fixed | copper | random | 0.814 | 5.731 | 0 | 0 | 0 |
| fixed | copper | sobol | 0.764 | 5.065 | 0 | 0 | 0 |
| fixed | copper | bo | 0.930 | 36.998 | 136 | 140 | 0 |
| fixed | hymod | random | 1.660 | 6.031 | 0 | 0 | 0 |
| fixed | hymod | sobol | 1.615 | 5.730 | 0 | 0 | 0 |
| fixed | hymod | bo | 1.649 | 23.092 | 264 | 0 | 0 |
| fixed | solar_diode | random | 18.298 | 5.969 | 0 | 0 | 0 |
| fixed | solar_diode | sobol | 15.342 | 5.923 | 0 | 0 | 0 |
| fixed | solar_diode | bo | 15.025 | 18.971 | 264 | 0 | 0 |
| target | hydro | random | 2.277 | 5.745 | 0 | 0 | 0 |
| target | hydro | sobol | 4.409 | 12.323 | 0 | 0 | 0 |
| target | hydro | bo | 0.085 | 0.340 | 12 | 0 | 0 |
| target | solar | random | 0.030 | 0.104 | 0 | 0 | 0 |
| target | solar | sobol | 0.029 | 0.104 | 0 | 0 | 0 |
| target | solar | bo | 0.030 | 0.108 | 0 | 0 | 0 |
| target | copper | random | 0.017 | 0.106 | 0 | 0 | 0 |
| target | copper | sobol | 0.025 | 0.138 | 0 | 0 | 0 |
| target | copper | bo | 0.026 | 0.148 | 4 | 0 | 0 |
| target | hymod | random | 30.411 | 292.076 | 0 | 0 | 0 |
| target | hymod | sobol | 36.552 | 346.301 | 0 | 0 | 0 |
| target | hymod | bo | 2.028 | 33.984 | 706 | 0 | 0 |
| target | solar_diode | random | 0.833 | 0.249 | 0 | 0 | 0 |
| target | solar_diode | sobol | 0.816 | 0.241 | 0 | 0 | 0 |
| target | solar_diode | bo | 0.820 | 0.259 | 4 | 0 | 0 |

For an expensive model, fewer calls can reduce time when saved evaluation cost exceeds additional optimizer overhead. This is conditional on unchanged search behavior and is not a measured speedup on another model. A capped baseline provides a lower bound on calls to target, not an exact eventual convergence time.

## Evidence and limitations

The audit checks every successful objective and each checkpoint/final recommendation. Existing models use vector kernels as a reference. Solar diode uses an independent vector Lambert-W solver against the scalar Brent BMI implementation. HYMOD is rerun through BMI with a daily water-balance check. Audit JSON files retain counts and hashes.

HYMOD states are conditional on the chosen initialization; slow reservoirs are not guaranteed to equilibrate during the inherited warmup. The solar module is a representative CEC snapshot, not the identified site hardware. Its parameters need not be identifiable from aggregate AC measurements. Model complexity does not establish physical realism or predictive skill. Validation optimization and held-out improvement remain distinct. Partial-observation BO is not evaluated by this suite.

See ../PROTOCOL.md for sources, bounds, targets and timing definitions. workflow/results.json retains actual BMI component-swap diagnostics. fixed/ and target-2000/ retain ledgers, manifests, timings and frozen recommendations. Source snapshots and history/a262556 preserve earlier hashed inputs. The workflow diagnostic fix deep-copies component metadata before swapping. Initial incorrect swap diagnostics are preserved in workflow-initial/. Intermediate diagnostics before sensor QA are in workflow-before-temperature-qa/; corrected diagnostics are in workflow/.


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
