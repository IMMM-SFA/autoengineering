# Solar interval and partition preparation

Status: implemented and tested on authored normalized inputs. No source/site,
scientific adapter, protected scorer or private boundary is admitted by this
increment. The full [Part 5 plan](part-5-utility-confirmation.md) remains the goal.

The proposed site 2107 has mixed sampling, unqualified interval code `L`, and
unresolved equipment/channel joins. The [source review](../reviews/part-5-confirmation-preparation.md)
records those facts. The historical site-9068 profile remains unchanged. This
increment supplies the preparation machinery needed after those source semantics
are resolved. It does not infer them from names, array order or clock codes.

## Interval contract

`examples/utility/solar_intervals.py` accepts normalized AC averages in kW, POA
averages in W/m2, and sampled temperature/wind with declared F/C and mph/m/s units.
Every input record has explicit interval support or observation time, availability
and quality. Aligned rows bind both the exact plan digest and alignment-source
digest. Partitioning rejects rows from a different unit, time, age or algorithm
policy even when their timestamps match. `SolarAlignmentPlan` binds source and semantics-review identities, target
range/cadence, maximum sample age and the causal-hold policy.

Timestamps require explicit UTC offsets and whole-second support. Ambiguous local
clocks, timezone-code strings and fractional support refuse. Output support is
canonical UTC. Ordered average intervals cannot overlap. Ordered sample timestamps
cannot duplicate, and availability cannot move backward or precede observation.

Averages combine only when their complete supports tile a target interval.
Duration weights preserve interval energy. Coarse averages are never divided into
invented finer observations. Missing, late, low-quality or cross-boundary support
blocks scoring. Temperature and wind use only samples already available at each
part of the interval. Holding is bounded by observation age. A sample at target
end has zero weight in that interval. F and mph conversions are explicit. These
held driver means are declared estimates, not recovered continuous measurements.

Driver continuity and scoring eligibility are distinct. Valid weather drivers
remain available when AC labels are missing. If a driver is missing, all driver
fields are masked together. Scoring uses one common mask across observations and
drivers. Unscored AC/energy fields are null, never fabricated zeros. Negative AC
standby is retained for later equipment-specific checks. Negative used wind or
irradiance cannot be hidden by averaging with positive values.

## Partition contract

`examples/utility/solar_partitions.py` consumes that normalized row stream through
four explicit, contiguous warmup/fitting/selection/confirmation windows.
`SolarPartitionPlan` binds the alignment, hardware-review identity, segment warmup
and state policy. Missing AC labels do not reset driver state. A driver gap creates
a new segment with the declared number of unscored warmup intervals. A role
boundary alone does not reset state. Actual model initialization and cadence
support still need task-specific qualification.

The public bundle contains development forcing and separately masked fitting and
selection labels. The private bundle contains full forcing for frozen inference
and separately masked confirmation labels. Future drivers, reserved labels and
private directory names stay out of public data. Source bytes, exposure and
privacy are not inferred from this separation.

Two empty, separate owner-private scopes are required. Create-only claims precede
row iteration. The row count and every target support must match the plan, and
fitting, selection and confirmation must each retain scored support. The private
manifest commits before public data and the public manifest. Interrupted scopes
are consumed and cannot be silently overwritten or retried. Source errors become
a generic error without retaining the original exception as cause or context.
Native Python callers remain trusted and can inspect their own process memory or
traceback frames. An admitted worker boundary must serialize scoped results and
errors rather than expose native exception objects.

Application bounds are one million source rows per channel, two million combined
source rows, 500,000 target intervals and 64 MiB per encoded artifact. These are
row/byte checks, not measured OS RAM, CPU or whole-preparation deadline guarantees.
The aligner supports an output-progress callback containing row counts only.
The new helpers are outside the frozen 315-source guest wheel and do not change
its runtime or activate a private profile.

## Verification and remaining work

Authored analytic tests cover energy-preserving coarsening, unequal durations,
causal availability and delays, maximum age, explicit DST offsets, gaps, overlap,
quality masks, conversions, bounds, immutable inputs and negative standby. Partition
canaries cover reserved labels and drivers, claim/commit order, consumed failures,
role support and source-error sanitization. Driver continuity through missing labels
and reset/warmup after driver gaps are tested separately.

Before using site data, qualify its clock/interval and hardware mappings and the
source parser. Freeze the grid, sample-age, quality and initialization policies
without inspecting candidate confirmation performance. Prepare separated source
artifacts, implement and qualify the actual site-specific model/scorer bindings,
and verify direct/wrapped parity on admitted development data. The historical
five-minute transient model cannot be assumed valid at a new cadence. No actual
observation file, model, training process, scorer, LLM or data-fetch request was
used by this increment. Task admission, the four adverse guest-output cases and
the full independent comparison remain open.

The final source-bound regression passed 76 tests in 1.03 seconds with zero
failures, errors or skips. The v1 checkpoint retains its preceding 74-test scope
and exact source snapshot. An intermediate 75-test check added plan identity;
the final check adds implementation identity. The current source successor is
`examples/utility/source-inventory-solar-inputs-v2.json`. All 224 core and 315
declared runtime sources remain unchanged. The full default suite was not rerun.


## Verified solar bundle readers

`examples/utility/solar_inputs.py` reads sealed development and reserved bundles
with caller-supplied manifest and preparer hashes. It checks exact chronology,
roles, segment continuity, warmup masks and interval energy. The public reader
opens only its four files. The trusted reserved reader checks the full forcing
prefix against public bytes. It grants no label-access authority. Both return
immutable records marked `not_admitted`, refuse changed or incomplete bundles,
and never repair or rerun preparation. Generic errors retain no exception cause
or context. Trusted native callers still control their process and traceback frames.

The [installed-reader archive](../../examples/utility/verification-solar-readers-installed-v1/README.md)
records 85 passing related tests and a copied-input wheel with 228 Python files.
It was installed into an isolated target without network or dependency installation.
The cold reader used relocated authored bundles with source fallback, model imports,
new processes and network denied. Existing native macOS dependencies were inherited.
This is neither fresh-environment nor Linux qualification and does not replace the
frozen guest wheel. The first wrong-directory build was excluded and never installed.
Its evidence remains separate from the corrected build and installed check.

The source successor is `examples/utility/source-inventory-solar-readers.json`.
All 224 core and 315 declared guest sources remain unchanged. Actual observations,
models, fitting, scoring, LLM calls and source acquisition were not used. Raw parser,
site timing/equipment mappings, exposure, model/scorer admission and the full Part 5
comparison remain open. No frozen scientific threshold or task status changed.


## PVDAQ metadata and header review

`examples/utility/solar_metadata.py` verifies the caller-pinned metadata bytes,
system and channel before resolving the CSV header from `sensor_name`. It accepts
only the reviewed average-kW, identity-conversion AC semantics. Duplicate keys,
metric/device IDs and headers, offline channels, unsupported calculations or
conversions and boolean IDs refuse. Equipment links require explicit primary keys,
not similar names or dictionary order. Missing joins remain named blockers.

The [metadata evidence](../../examples/utility/verification-solar-metadata-v1/README.md)
retains the real pinned 2107 review and authored positive/negative cases. Explicit
joins alone do not admit timestamp support/availability, equipment parameters,
quality, exposure, scientific models or private execution. Every result remains
`not_admitted`. The known source still lacks channel/inverter and module/inverter
links and string topology.

The [official DOE walkthrough](https://www.energy.gov/sites/default/files/2024-05/Data_Tools_Webina..._Comms_Final.pdf)
confirms these omissions and the header mapping on pages 21-22. Browser extraction
also displayed four historical example rows from November 2017. The exposure
register records that access without their values, and its preceding bytes remain
preserved. Those samples are outside the proposed 2019-2022 windows. No observation
CSV or proposed-period observations were accessed, and no model, fitting, scoring
or provider call ran. The full PDF bytes were not acquired or hash-verified.

The related regression passed 102 tests with no failures, errors or skips. The
incremental source successor is `examples/utility/source-inventory-solar-metadata.json`.
All 224 core and 315 frozen guest sources remain unchanged. Full default and
platform qualification retain their prior scopes. The Part 5 goal remains incomplete.


A source-pinned solar CSV parser now feeds the existing interval, custody and
reader path. It requires declared headers, clocks, durations, availability, units
and quality codes. Role claims commit before source access. The authored canary
case preserves reserved separation and consumed failures. Thirty-nine focused
parser tests and 93 related solar tests passed. A guarded public reader opens
neither raw CSV nor reserved artifacts. No site observations, model, fitting,
scoring, provider or dependency installation ran. Site clock/equipment facts,
independent exposure and task admission remain unresolved. Frozen core/guest
sources remain unchanged. Current inventory: `examples/utility/source-inventory-solar-csv.json`.

[CSV preparation evidence](../../examples/utility/verification-solar-csv-v1/README.md).


The authored solar CSV workflow now has a bundled module example and a separately
verified 231-Python-file wheel. It prepared inputs and ran public/trusted-reserved
readers outside the checkout, with source fallback rejected. Source access followed
both role claims. The terminal guard refused an explicit reserved read in the public
phase. The CLI also completed. The 95-test regression passed. Dependencies were
inherited from native macOS; no fresh-environment, Linux, guest/private or full
installed-workflow qualification follows. Task admission and the independent study
remain open. Current inventory: `examples/utility/source-inventory-solar-csv-installed.json`.

[Installed CSV evidence](../../examples/utility/verification-solar-csv-installed-v1/README.md).
