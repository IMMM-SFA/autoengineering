# Real models on a laptop

Three offline examples couple CSDMS BMI model components and compare explicit component swaps,
random search, Sobol search and whole-system Bayesian optimization. They use measured response data and preserve unfavorable
results. No GPU, external service or API key is needed after environment installation.

| Domain | Model chain | Measured target | What can change |
| --- | --- | --- | --- |
| Water | Hamon/Hargreaves PET -> soil bucket -> linear reservoir | USGS discharge | PET method, soil capacity, reservoir recession |
| Solar energy | Ross temperature -> PVWatts DC -> PVWatts inverter | PVDAQ inverter AC power and module temperature | Ambient-only or Ross temperature, heat loss, aggregate loss factor |
| Materials | Temperature basis -> polynomial or rational regression | NIST copper thermal expansion coefficient | Regression family and regularization |

The materials case is an empirical regression pipeline rather than a coupled physical simulator.
The water and solar cases contain physical submodels. The system YAML files describe these chains.
`run.py` uses `validate_arrays`, `rank_opportunities`, and `swap_component`, then invokes the
public `OptimizationStudy` controller. Only the terminal response has a validation target in the
water and materials cases. A terminal error cannot identify which physical component is wrong.

## Run

From the repository root:

```sh
pixi install -e examples
pixi run -e examples python -m examples.local_models.run \
  --output outputs/local-models --seeds 0 1 2 --evaluations 12
```

The default runs all three domains with random, Sobol and BoTorch policies. For a short smoke run:

```sh
pixi run -e examples python -m examples.local_models.run \
  --output outputs/local-models-smoke --methods sobol --seeds 0 --evaluations 4
```

Use a new output directory for each invocation. The suite refuses to overwrite prior results.
Each study writes its controller manifest, observation ledger, frozen recommendation and
`application-result.json`. The root `results.json` retains every completed study. Progress is printed
for every evaluation. The default matrix has 27 studies and 324 model evaluations. BoTorch uses
one CPU thread. Measured runtimes belong to the result files; model call count alone does not
measure practical efficiency.

```sh
pixi run -e examples python -m examples.local_models.component_probe \
  --output outputs/local-components
pixi run -e examples pytest tests/test_local_models.py -q
```

The component probe reuses a saved temperature trace for a different downstream configuration and
checks exact agreement with a complete rerun. It also constructs two temperature traces with the
same mean but different downstream mean power. This tests whether the current scalar coupling
representation is sufficient. These are component and representation tests, not a claim that
partial BO improves this application. The prior partial-BO gate remains failed.

## Data and models

The exact selection rules and comparison budget are in [PROTOCOL.md](PROTOCOL.md). Tests are held
out from both regression fitting and optimizer feedback. Solar and water are short conditional
hindcasts with measured weather. Copper mainly evaluates interpolation, with two test points outside the training temperature hull.
These examples are not operational forecasts or engineering design validations.

- Water: the existing `examples/leaf_river/data` cache contains 2019-2020 USGS station 02472000
  discharge and NOAA GHCN station USW00003940 weather. The original fetcher records conversion to
  basin-depth discharge using 1947.7 square kilometers. These US federal observations are reused
  as received; the cache has no original API response or quality flags, and the distant weather
  station is not a basin-average forcing. That limits interpretation. See
  [USGS station](https://waterdata.usgs.gov/monitoring-location/USGS-02472000/) and
  [NOAA GHCN Daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily).
  The existing PET and bucket functions are reused. The new linear reservoir conserves water
  exactly. Its simplified structure omits explicit groundwater, snow and spatial variability.
- Solar: Deline and colleagues, NREL,
  [PVDAQ public datasets, OEDI submission 4568](https://data.openei.org/submissions/4568),
  licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). We select system 9068,
  inverter 2, January 1-7, 2024, from bounded byte-range excerpts of the 2024-2025 files. CSVs
  are joined on the original local timestamps. Incomplete last records from range requests are
  discarded explicitly. No timestamps are interpolated, no missing sensors are filled, and
  negative or missing power plus low-irradiance rows are excluded by the registered rule.
  Source metadata are preserved. The 4738 kW total DC rating is divided equally between the
  two inverters; string metadata do not fully reconcile that allocation, so this is a declared
  modeling assumption. Measured back-of-module temperature approximates cell temperature.
  The plant has CdTe modules; this simplified model does not resolve spectral response,
  tracker geometry, snow, mismatch or curtailment. A fitted loss factor may absorb such errors.
  See the [pvlib temperature models](https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/temperature.html)
  and [PVWatts model manual](https://pvwatts.nrel.gov/downloads/pvwattsv5.pdf).
- Materials: Thomas Hahn, NIST,
  [thermal expansion of copper](https://www.itl.nist.gov/div898/handbook/pmd/section6/pmd641.htm).
  The 236 observed pairs are extracted from the original `Hahn1.dat`, with response units retained
  as supplied by NIST. Certified fitted coefficients in the source file are never used by a model.
  Polynomial and rational forms follow the [NIST case study](https://www.itl.nist.gov/div898/handbook/pmd/section6/pmd64.htm).
  Our rational denominator coefficients are constrained to be nonnegative. This avoids poles at
  positive temperature but changes the family from the unconstrained NIST certification problem.
  Federal NIST data are attributed to their source and carry no added project license restriction.

`data/sources.json` records source URLs, byte ranges and SHA-256 hashes for the new downloads.
`data/raw/` preserves those bytes, including compressed solar excerpts. Rebuild the selected tables
without a network connection:

```sh
pixi run -e examples python -m examples.local_models.prepare_data
```

`data/preparation.json` records row exclusions and split counts. The study manifest hashes the
prepared data, protocol, example source, reused water models and environment lock. Dependency
installation does require network access on a machine without a populated Pixi cache.

The example driver reads BMI class paths and exchange connections from candidate YAML.
It couples components through BMI initialize, set_value, update, get_value_ptr and finalize.
The package-wide Python/command runner has not gained a BMI backend; this driver is scoped to
the examples. Opportunity ranks compare terminal RMSE with the training-mean response
reference evaluated on validation rows. Solar temperature is ranked separately against the
ambient-only temperature reference. These are diagnostic references, not release thresholds.
Only copper fits model coefficients on the training subset. Hydrology uses earlier forcing to
carry state into validation; solar optimization scores only its validation day. The solar
training window supports component diagnostics, not an additional hidden fitting step.


## BMI components

The wrappers inherit the official `bmipy.Bmi` abstract interface. `bmi_base.py` implements lifecycle,
variable access and scalar-grid methods. `bmi_components.py` implements these numerical components:

| Class | Inputs -> outputs | Time interpretation |
| --- | --- | --- |
| `PetBmi` | Temperature and day of year -> potential evaporation | Daily step, units `d` |
| `SoilBucketBmi` | Rainfall and PET -> ET, excess water and soil storage | Daily state update |
| `LinearReservoirBmi` | Excess water -> runoff and reservoir storage | Daily state update |
| `SolarTemperatureBmi` | Irradiance and air temperature -> module temperature | Independent sample index, units `1` |
| `PvWattsDcBmi` | Irradiance and module temperature -> DC power | Independent sample index |
| `PvWattsInverterBmi` | DC power -> AC power | Independent sample index |
| `TemperatureBasisBmi` | Temperature in K -> scaled temperature | Independent sample index |
| `CopperRegressionBmi` | Scaled temperature -> expansion coefficient | Independent sample index |

Every exchange variable is a length-one float64 array on scalar grid zero. Grid topology and
spatial-coordinate functions that do not apply raise `NotImplementedError`, following the
[BMI grid guidance](https://bmi.csdms.io/en/stable/bmi.grid_funcs.html). The driver rejects missing
inputs, mismatched units, incompatible grids and differing time steps/horizons. It always
finalizes initialized models, including on failure. The solar and materials clocks count cases;
they do not imply that missing nighttime observations have been simulated.

BMI copy, pointer and indexed access are tested. Pointers stay valid through updates until
finalization. Reinitialization resets water storage and time. The unchanged numerical functions
in `kernels.py` provide a separate reference for parity checks; workflow and optimizer evaluations
use the BMI chain. `CopperRegressionBmi` fits training coefficients during initialization.

Copper's source table does not give an explicit response-unit multiplier. The wrapper therefore
returns the opaque unit string `source_expansion_units`. This preserves the measured numeric
scale, but is not a portable UDUNITS unit. Resolve that metadata before coupling the copper output
to a model requiring a physical expansion unit. This example implements the BMI method interface;
it does not claim complete unit interoperability for the copper response.

For a standalone component:

```python
import numpy as np
from examples.local_models.bmi_components import SoilBucketBmi

model = SoilBucketBmi({"capacity": 100.0, "end_time": 2})
model.initialize()  # Alternatively pass a YAML configuration path.
model.set_value("precipitation", np.array([20.0]))
model.set_value("potential_evaporation", np.array([0.0]))
model.update()
print(model.get_value("soil_storage", np.empty(1)))  # 70 mm
model.finalize()
```

See the [CSDMS BMI specification](https://github.com/csdms/bmi) for the coupling contract.


## Recorded comparison and checks

[Development results](results/RESULTS.md) include all seeds, adverse comparisons, runtime and
partial-observation interpretation. The final matrix uses BMI throughout. Preliminary direct
adapters and the interrupted boundary-decoding run remain separately labeled.

Regenerate the report and audit all recorded predictions:

```sh
pixi run -e examples python -m scripts.summarize_local_models \
  --directory examples/local_models/results/bmi-development --output outputs/local-models-report.md
pixi run -e examples python -m scripts.audit_local_models \
  --directory examples/local_models/results/bmi-development --output outputs/local-models-audit.json
pixi run -e examples python -m scripts.check_solar_bmi_closure \
  --output outputs/local-models-closure.json
pixi run -e examples python -m pytest tests/test_local_bmi.py tests/test_local_models.py -q
```

Create `outputs/` first if it does not exist. Audit and closure outputs must be new files.
The restricted-family closure check supplements the general reversal probe: Ross temperature
means can reconstruct attainable traces on fixed forcing, while mean DC power does not preserve
inverter output exactly. Application partial BO remains not implemented or evaluated.

## More evaluations and a common stopping target

The follow-up comparison doubles the fixed budget from 12 to 24 complete-model
calls. A separate experiment uses five new seeds and stops each method at a frozen
validation RMSE target or 60 calls. All evaluations still execute the BMI chains.

```bash
pixi run -e examples python -m examples.local_models.convergence --mode fixed --output outputs/local-models-extended
pixi run -e examples python -m examples.local_models.convergence --mode target --output outputs/local-models-target
```

Output directories must be new. See [the protocol](CONVERGENCE_PROTOCOL.md) for
target construction, timing boundaries and censored runs, and
[the results](results/CONVERGENCE_RESULTS.md) for the paired budget comparison,
evaluations to target, success rates, elapsed time and held-out error. Reaching a
shared validation target measures search efficiency without claiming a global optimum.
