# BMI example development results

__Post-run QA correction (2026-09-05):__ measured solar module-temperature diagnostics
and observed-intermediate-truth claims are withdrawn because the cached sensor is
unusable. AC-power optimization and simulated-trace reuse are separate. See
[the QA record](../../complex_models/results/data-quality.json).

All 27 studies completed, with 324 recorded model evaluations. Recorded study time totaled 127.5 seconds.

Each optimizer used 12 model calls and seeds 0, 1 and 2. The table gives held-out RMSE. Optimizer columns are medians across seeds. Lower is better. Fixed swaps were selected on validation data and used a separate small candidate budget.

| Domain | Unit | Initial model | Selected fixed swap | Random | Sobol | BO |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| hydro | mm/day | 4.0026 | 3.6981 | 2.8250 | 2.8271 | 2.8839 |
| solar | kW | 358.5655 | 301.0604 | 116.8577 | 118.9642 | 121.9417 |
| copper | native source units | 1.0212 | 0.2492 | 0.2489 | 0.2477 | 0.2479 |

Model swaps and parameter search improve the initial examples, but BO does not beat the strongest random/Sobol median in any of these three small comparisons. Three seeds and short validation/test windows do not establish general method rankings.

| Domain | Method | Seed | Validation RMSE | Test RMSE | Model seconds | Study seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| hydro | random | 0 | 3.564312 | 3.177787 | 0.2997 | 4.1173 |
| hydro | sobol | 0 | 3.401117 | 2.959732 | 0.2807 | 3.8886 |
| hydro | bo | 0 | 2.065996 | 2.883923 | 0.2917 | 5.8583 |
| hydro | random | 1 | 2.610428 | 2.814183 | 0.3097 | 4.0285 |
| hydro | sobol | 1 | 2.607648 | 2.809316 | 0.2794 | 4.0643 |
| hydro | bo | 1 | 2.065996 | 2.883923 | 0.2814 | 5.2436 |
| hydro | random | 2 | 2.787593 | 2.825035 | 0.3285 | 4.6914 |
| hydro | sobol | 2 | 3.548664 | 2.827094 | 0.3345 | 4.9809 |
| hydro | bo | 2 | 2.065996 | 2.883923 | 0.3053 | 5.2583 |
| solar | random | 0 | 175.680321 | 116.140727 | 0.2876 | 5.6731 |
| solar | sobol | 0 | 176.019914 | 129.292488 | 0.3000 | 5.4862 |
| solar | bo | 0 | 175.077560 | 121.941722 | 0.2095 | 5.0698 |
| solar | random | 1 | 175.504363 | 116.857693 | 0.2316 | 3.9627 |
| solar | sobol | 1 | 176.133176 | 118.964160 | 0.2134 | 3.8684 |
| solar | bo | 1 | 175.077562 | 121.940106 | 0.2062 | 5.5247 |
| solar | random | 2 | 176.388791 | 128.695077 | 0.2364 | 3.8804 |
| solar | sobol | 2 | 177.054952 | 115.348152 | 0.2567 | 4.0579 |
| solar | bo | 2 | 175.079463 | 122.439976 | 0.2417 | 5.5607 |
| copper | random | 0 | 0.196292 | 0.248874 | 0.1585 | 4.3466 |
| copper | sobol | 0 | 0.195993 | 0.247674 | 0.1635 | 4.0592 |
| copper | bo | 0 | 0.195976 | 0.247930 | 0.1760 | 5.2464 |
| copper | random | 1 | 0.234321 | 0.295076 | 0.1840 | 4.1760 |
| copper | sobol | 1 | 0.195984 | 0.247731 | 0.1715 | 4.3793 |
| copper | bo | 1 | 0.195984 | 0.247731 | 0.1763 | 5.1167 |
| copper | random | 2 | 0.195996 | 0.247663 | 0.1789 | 4.5023 |
| copper | sobol | 2 | 0.195995 | 0.247667 | 0.1828 | 4.5706 |
| copper | bo | 2 | 0.195978 | 0.247965 | 0.1841 | 5.8874 |

Study time includes optimizer and durable controller overhead. Model time measures the BMI chain inside evaluator calls. Held-out evaluation, imports and fixed-swap workflow time outside the study are not included in those study totals.

## BMI and component reuse

Eight components implement the Python BMI interface. The graph driver checks scalar grids, float64 variables, unit matching, complete input wiring and common clocks. Water components retain daily storage. Steady-state models advance by independent sample index.

Saved solar temperature traces reproduce downstream power exactly: `True`. Median repeated BMI component timings were 4.129 ms for temperature, 12.400 ms for DC plus inverter, and 21.102 ms for the complete solar chain.

## Partial observation status

Application partial BO is **not implemented or evaluated** in this suite. The earlier frozen partial-BO gate remains failed.

The arbitrary trace-reversal probe demonstrates general information loss, but does not prove that the registered Ross family lacks a sufficient scalar summary. With fixed irradiance and air temperature, mean module temperature identifies the Ross coefficient and reconstructs the attainable temperature trace.

The registered-family check reconstructed AC outputs with a maximum difference of 3.41e-13 kW. Two attainable configurations with equal mean DC power differed in mean AC power by 0.067068 kW. Thus the separate DC-to-inverter boundary cannot be summarized exactly by mean DC alone.

A temperature component followed by a combined DC/inverter component is a candidate function-network representation for a later comparison. Its cost benefit remains untested; these models are cheap enough that optimizer overhead may outweigh saved model work.

## Evidence and limits

The complete BMI matrix is in `bmi-development/`. `bmi-component-probe/` and `bmi-scalar-closure.json` retain component evidence. Preliminary direct-adapter results remain in `pre-bmi-development/`; the decoder failure is preserved in `interrupted-boundary/`. Neither preliminary directory is pooled with the BMI matrix.

The final BMI source/input hashes were verified when generating this document. Earlier preliminary runs retain hashes and records but not a complete separate source archive. Their role is development history, not the reproducible final comparison.

Hydrology uses a legacy observation cache without original API quality flags. Solar uses one short winter window and an assumed equal DC allocation between inverters. Copper retains an unresolved output-unit multiplier and includes two endpoint extrapolations. See `../README.md` and `../PROTOCOL.md` for source and scientific limitations.
