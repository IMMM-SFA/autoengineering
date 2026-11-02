# Part 5 final test proposal

Use a new river basin, a different solar site, new circuit load cases and a
separate wind dataset for the final comparison. These choices give us a concrete
path forward without requiring an existing private dataset or a separate person
to supply one. They are proposed choices, not admitted tasks or run authority.

## Data and scenarios

| Task | Proposed development and selection data | Proposed final test | What the test can establish |
| --- | --- | --- | --- |
| Hydrology | CAMELS basin 01491000, Choptank River near Greensboro, Maryland. Use 1980 for warmup, 1981-1999 for fitting and 2000-2004 for selection. | Reserve 2005-2014 discharge. Use the Daymet forcing product throughout. | Performance on a basin different from the exposed Leaf River example, with later years held out within that basin. This does not test transferring fitted Leaf River parameters unchanged. |
| Solar | PVDAQ site 2107, inverter 1. Fit on 2019-2020 and select on 2021. Preserve the measured-POA conditional AC question and use this site's actual equipment. | Reserve calendar year 2022 AC power. | Later-year conditional AC reconstruction at a different site from 9068. Measured contemporaneous POA is an input, so this is not an advance weather forecast. |
| Engineering | Keep the existing coupled OpenMDAO circuit and source-current design variable. Use the existing nominal-resistance development cases. | Use the 24 new load/ground combinations defined below. | Robustness to predeclared component tolerances under the circuit model. These are authored engineering assumptions, not observed field data or empirical validation. |
| Wind | WIND Toolkit V2 at the grid point nearest longitude -70.5, latitude 41.5. Use 2007-2009 for development and 2010-2011 for selection. | Reserve 2012-2014 wind speed and direction. | Modeled layout energy under different resource years at the selected point. This is not measured turbine-power prediction or a real lease design. |

The [CAMELS catalog](https://zenodo.org/records/15529996) advertises daily data
through 2014, and its [basin name file](https://zenodo.org/records/15529996/files/camels_name.txt?download=1)
contains 01491000. This confirms the basin's identity, not complete discharge
coverage or quality. Use basin-area metadata for discharge conversion and retain
the original quality flags. Keep the final discharge separate from fitting and
selection. Do not load streamflow-derived CAMELS attributes computed across the
reserved years into selection. The separate
[daily partition preparer](../utility.md#hydrology-partition-preparation) now
separates normalized development and reserved artifacts with authored tests.
The separate `hydrology_camels` parser now supports a bounded raw Daymet/flow
pair with declared checksums and authored tests. It preserves source dates and
requires a declared hour field. Actual source files and daily interval semantics
remain unqualified. The separate
`hydrology_site` development adapter now binds latitude and area and calls both
existing PET families with explicit latitude. Its authored water-balance and
development-boundary checks pass. Real source verification, basin adequacy and
private execution remain unqualified. The old Leaf River defaults stay unchanged.
The separate `hydrology_learned` development profile now supplies a conservative
learned routing candidate with fitting-only training and frozen inference on
authored data. This does not admit it to the proposed comparison or establish
adequate training support at Choptank.

The [PVDAQ documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md)
identifies site 2107 as a fixed ground-mounted California facility. Its
[public equipment and channel metadata](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2107_OEDI/metadata/2107_system_metadata.json)
advertises timestamps from December 2018 through November 2023. It lists inverter
1 AC power in kW, POA irradiance in W/m2, ambient temperature in Fahrenheit and
wind speed in mph. Convert the latter two explicitly. The reported 5-15 minute
support and inverter interval convention need a new alignment contract. Reusing
9068's equipment or assuming uniform five-minute sampling would be incorrect.
This replaces the site-specific preparation, not the existing 9068 evidence.

The [WIND Toolkit V2 API](https://developer.nlr.gov/docs/wind/wind-toolkit/wtk-download/)
documents 2007-2014, hourly extraction, UTC, leap-day handling and 80 m wind
channels. Propose an explicit 80 m hub height with the supplied V80 power curve,
and qualify that hardware binding before execution. Preserve the four-turbine
layout problem and spacing checks in local coordinates. Coverage at the chosen
point, exact grid identity and access terms still need verification. The API
requires a key and email. No request containing either has been made. Prefer an
anonymous public-data route if practical, otherwise present the exact request
before sending personal information or starting server-side extraction.

For engineering, use the Cartesian product of ground voltage
`{-0.05, 0, 0.05}` V, resistance R1 `{95, 100, 105}` ohm and resistance R2
`{9500, 10000, 10500}` ohm. Remove the three already exposed cases where both
resistors have their nominal values. The remaining 24 cases are equally
weighted. The +/-5% load tolerance is a proposed design assumption. Preserve
the native coupled solver and derivatives. Add and qualify the resistance
bindings before using them. The separate
[load development profile](../utility.md#circuit-load-development-profile) now
has direct/wrapped parity, derivative and supervised recovery checks on other
authored loads. Its native SLSQP recipe now covers supplied sets containing the
controlling load/ground corner, with independent fresh checks of every case.
Installed development execution and offline receipt checks now pass. Protected
final scoring remains open. Require node 2
voltage of at least 0.62 V relative
to the fixed external reference in every case, with constitutive residuals at
most 1e-10 A. Do not silently reinterpret this as voltage relative to the moving
ground node.

## Access and reuse

The [source access record](../../examples/utility/proposals/confirmation-v1/rights-access-evidence.json)
binds the inspected metadata and the remaining access questions. No observation
file was acquired in this review.

| Source | Identified terms and access | Remaining preparation |
| --- | --- | --- |
| CAMELS | The [DOI registrant's record](https://api.datacite.org/dois/10.5065/D6MW2F4D) points to the chosen Zenodo archive and retains a registration condition under UCAR terms. [UCAR's data policy](https://www.ucar.edu/terms-of-use/data) specifies CC BY 4.0 where copyright applies unless otherwise stated, and requires the recommended citation. | Resolve how the recorded registration condition applies to acquisition from the current archive. Retain the CAMELS citations. Do not infer permission or independence merely from an anonymously readable metadata file. |
| PVDAQ | The [official OEDI catalog](https://data.openei.org/data.json) identifies submission 4568 and declares CC BY 4.0. The exact extracted record and catalog hash are saved in `oedi-catalog-license.json`. Public S3 object listings have been checked without credentials. | Preserve attribution and dataset-specific terms. The generic OEDI AWS registry's CC BY 3.0 US statement must not replace the more specific catalog record. Final channel completeness and rights notices still need source-level curation. |
| WIND Toolkit | The [managed AWS registry](https://registry.opendata.aws/nrel-pds-wtk/) declares CC BY 3.0 US and anonymous S3 access. The annual CONUS object names and sizes were verified without credentials, email or weather retrieval. | Freeze source versions and a bounded point-extraction method. Verify the selected grid cell, height, UTC support and variable semantics before joining years. |

The anonymous wind archive has a source-version boundary: 2007-2013 annual
objects are under `conus/v1.0.0/`, while the 2014 object is under
`conus/v1.1.0/`. The proposed years are unchanged, but combining those versions
requires a documented comparability check. The eight annual HDF5 objects total
12,295,111,327,536 bytes. Do not download those whole objects for this single-point
study. Prepare a range/subset strategy with byte and request caps first. No such
extraction has been attempted.

Use a trusted preparation path to separate mixed-period source files into
development and reserved artifacts. A file that contains both kinds of rows
must not become an advisory worker's input. Preparation should publish source
hashes, timestamp coverage and predeclared quality-mask decisions, without final
observations or model-performance summaries. Dataset reuse terms do not grant
scientific admission, change the package license or prove an untouched test set.

## What counts as useful

These margins are proposed judgments for this study, not published standards or
values selected from final-test performance. Before confirmation, compute each
reference quantity once using the unchanged baseline on the admitted development
data and freeze its numeric value and units. A zero or invalid reference blocks
the proposed rule rather than creating a zero margin.

| Task | Minimum useful gain over the conventional route | Secondary limits |
| --- | --- | --- |
| Hydrology | RMSE reduction of 5% of the fixed development-baseline RMSE, expressed in mm/day. | Absolute volume bias at most 10%, with degradation at most 2 percentage points versus conventional. Nonnegative stores and daily water balance must pass. |
| Solar | AC RMSE reduction of 5% of the fixed development-baseline RMSE, expressed in kW. | Absolute daytime energy bias at most 5%, with degradation at most 1 percentage point versus conventional. Equipment-specific nighttime and AC limits must pass. Energy bias requires qualified interval integration. |
| Engineering | Mean source-power reduction of 5% of the fixed development-baseline mean power, expressed in W. | All 24 voltage and residual checks pass. Worst-case source power may exceed conventional by at most 1%. |
| Wind | Mean annual energy gain of 1% of the fixed development-baseline AEP, expressed in GWh. | All geometry/spacing checks pass. No final-test year loses more than 2% energy versus conventional. |

The reference is fixed before the final test. For example, a development-baseline
RMSE of 2 mm/day would produce a 0.1 mm/day useful-gain margin. This is an
illustration, not a measured result. It avoids redefining the required gain after
seeing final-test errors.

Plan ten paired repetitions, two budget regimes and seven routes: unchanged
baseline, conventional, single agent, full workflow and three role removals.
That is 560 logical cells, including 480 adaptive cells. An identical deterministic
baseline can supply one reference per task across its 20 logical cells only under
the frozen reuse policy. Its physical work and allocated shares remain visible.
The repetitions are not independent river basins or solar sites.

Require successful, feasible selections in all assigned repetitions for a positive
scientific verdict. Show conditional paired effects and the full failure
denominators separately. Propose 95% familywise confidence across the 48 planned
task/regime/route contrasts, with Bonferroni adjustment. Freeze the exact interval
and time/scenario-dependence procedures after development profiling. Ten repetitions
are a planning count, not a power claim. Do not conclude equivalence from a wide
interval. Retain an extra role only if its predeclared comparison supports its
benefit and added cost. No expert effort is assumed to be zero.

## Admission and execution

The [metadata record](../../examples/utility/proposals/confirmation-v1/metadata-evidence.json)
contains source URLs, hashes and the inspected factual fields. This pass read
catalogs, equipment/channel metadata and object names and sizes. It did not fetch
discharge, AC measurements or the chosen wind series. Prior personal or external
use remains unknown. Existing exposed periods and the unresolved 9068 partial
cache remain excluded.

Next, verify rights and metadata, establish the separation of development and
reserved data, and check coverage without comparing candidate performance. A
missing period or channel blocks the named choice. It does not authorize choosing
a replacement based on favorable results. Any replacement gets a new proposal
identity. Quality exclusions must be fixed before scoring.

Profile only the proposed development data, qualify the new site/load/resource
bindings and protected scorers, then produce numeric budgets and a complete run
package. This proposal starts no models, providers, training, remote jobs or
confirmation. The task dossiers remain blocked drafts and `protocol.json` remains
absent until the scientific and execution prerequisites are actually met.
