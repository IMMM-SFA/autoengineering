# pvlib and OEDI System 9068

This is a measured-input adaptation of the [existing pvlib plant example](https://pvlib-python.readthedocs.io/en/v0.15.2/gallery/system-models/oedi_9068.html).
The original uses satellite irradiance, tracking, shading and spectral corrections.
Our boundary begins at measured pad-2 plane-of-array irradiance, treated explicitly
as effective irradiance. It excludes upstream irradiance reconstruction. Module
and inverter specifications remain the upstream example's inferred equipment.
The temperature baseline already includes Faiman plus Prilliman transience.
Steady Faiman is labeled an ablation, not silently substituted as the baseline.

The [SETO tutorial](https://pv-tutorials.github.io/2024_Modeling_Webinar/pvlib-tutorial.html)
provides the temperature comparison. We use the pad-2 temperature sensor and
inverter 2, keeping the spatial association explicit. Module and cell temperatures
are assumed equal in the electrical calculation (delta_t=0), as in the upstream
Faiman treatment. Sensor measurements do not independently establish cell temperature.

The [public PVDAQ catalog](https://data.openei.org/submissions/4568) supplies the
four files in sources.json. Software is BSD-3-Clause. Raw inputs are downloaded
into ignored data/ rather than redistributed. Keep source attribution and verify
applicable data terms before publishing a derived data bundle.

Use 2018 for selection and 2019 for test. No fitting occurs on test observations.
Five-minute timestamps follow the upstream US/Mountain localization assumption.
Duplicate timestamps reject; DST ambiguity is excluded. Invalid/missing drivers
break transient segments; the first four samples after each gap are excluded from
all models' scoring. Use nonnegative measured wind/POA, POA>=50 W/m2 for scoring,
finite module temperature and finite nonnegative inverter power. Outages and
clipping remain in the objective. The power score therefore describes the subset
with both power and temperature observations, not complete annual production.
Scored energy bias integrates only retained five-minute intervals.

Temperature range QA marks the entire diagnostic invalid if any scored sensor
value is outside -60 to 110 C. It does not repair readings or alter AC scoring.
The first full development run exposed such readings in 2019. Its raw record is
retained; subsequent reports omit invalid temperature RMSE. Range screening alone
does not certify a sensor. Illustrative opportunity rankings use RMSE divided by
5 C or 100 kW tolerance; these are not scientific acceptance standards.

The example demonstrates conditional reconstruction accuracy, not forecast skill.
Its test period has been inspected during example development, so it is a temporal
holdout, not a blinded external validation study. No candidates or parameters were
chosen using its scores.
