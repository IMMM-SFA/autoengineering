# Utility comparison preparation

These are blocked task drafts for Part 5, not executable run configurations.
No confirmation data have been acquired or scored by this preparation.

`source-inventory.json` hashes the implementation and dependency configuration
available during initial preparation, including uncommitted Part 3/4 sources.
It excludes raw evidence trees and is not a clean execution provenance record.
`exposure-register.json` preserves known exclusions and unknown exposure history.
The four files in `tasks/` record questions, candidate pools, checks and blockers.
Null thresholds and partitions are deliberate admission blockers, never permission
to execute with an unlimited budget or infer independent evidence.

Wind layout is the selected fourth family. The supplied Horns Rev distribution
is development evidence. A finer direction grid cannot serve as independent
weather confirmation. The engineering draft asks a new source-power design
question using the intact coupled circuit. Exposed scalar scenario bindings now
have supervised development checks. Independent scenarios still require admission.
Existing target fits cannot answer that question.

The [annual wind contract](../../docs/reviews/part-5-wind-annual-comparison.md)
now pairs annual producer outcomes by exact source, preserves failures and
reports separate generator-version strata without dropping 2014. Its authored
metadata tests do not execute wind models or broaden the development reader to
reserved years. Protected scoring and scientific source admission remain open.

The [annual wind kernel](../../docs/reviews/part-5-wind-annual-kernel.md) now
evaluates supplied, identity-bound in-memory annual drivers. It journals every
start and refuses reuse after success or publication failure. Authored parity
passed against the existing hourly profile. It supplies no private-source access,
selection barrier or OS isolation and remains outside the admitted scorer registry.

The [annual wind custody helper](../../docs/reviews/part-5-wind-annual-custody.md)
now prepares separate private binary drivers and public identity metadata before
suite selection. One-use source access requires the complete barrier and original
charged grant, with explicit private read and byte reservations. It acquires no
weather, registers no scorer and does not supply OS isolation or task admission.

The [annual wind development callback](../../docs/reviews/part-5-wind-annual-callback.md)
now connects the frozen layout to charged source access and the kernel. It pins
annual work before returning a score and supports metadata-only score recovery.
Its authored backend tests do not qualify private or native execution. No CLI
scorer registration or complete cost/report integration is supplied.

The [native callback control](../../docs/reviews/part-5-wind-annual-native.md)
now passed on authored drivers with three actual PyWake evaluations. Its public
proof replays without private inputs or optional model imports. The recorded
netCDF4 import warning and remaining environment/private-runtime limits prevent
broader qualification or an independent scientific claim.

The [core wind cost reader](../../docs/reviews/part-5-wind-cost-report.md) now joins
caller-pinned annual work into the existing reports. Cost-input schema version 2
carries both load and wind callbacks. An installed core-only reader passed without
examples, model imports or private weather. Unmeasured work and complete-cost
limits remain explicit.

The `hydrology_partitions` preparer separates normalized daily development data
from reserved driver/label artifacts, with explicit basin metadata and quality
masks. See [hydrology preparation](../../docs/utility.md#hydrology-partition-preparation).
It performs no model execution, data acquisition, source-byte verification or
privacy/exposure admission. The proposed Choptank observations remain unacquired.
The separate `hydrology_camels` parser now checks declared source hashes, Daymet
columns, basin metadata, daily alignment and missing-flow sentinels before
yielding normalized rows. Its authored checks do not authenticate acquired files
or resolve the documented Daymet hour-field ambiguity.
The [versioned legacy-source record](../../docs/reviews/part-5-camels-source-version.md)
now also binds declared archive/metadata hashes, HUC02 and explicit no-shift/no-fill
behavior. It does not verify archive membership or daily physical intervals.
The separate `hydrology_site` adapter now binds latitude and basin area, preserves
the supplied conservative equations, and bridges prepared development forcing
without labels or reserved dates. Its authored lifecycle, water-balance and
boundary tests do not admit a real basin or qualify private execution.
The `hydrology_learned` development profile now fits a conservative two-coefficient
storage-dependent routing rule. It accepts fitting labels only, persists a frozen
fit and training-work receipts, and runs inference without optimization. See the
[learned profile](../../docs/utility.md#learned-hydrology-development-profile).
It remains outside the independent comparison registry. No real basin has been
trained, and the existing learned-candidate admission refusal remains in place.
The offline training-cost reader verifies v2 intent/result/fit bindings from copied
artifacts without model imports or execution. It preserves unknown partial work
and distinct repeated fits. Authoritative campaign commits, suite reservation
integration and profile qualification remain required before independent use.
Successful worker training artifacts and explicit bundles now join the parent
campaign's lifecycle event on completion and saved-result recovery. The campaign
cost reader verifies original-event training work and retains unknown preparation
when the origin/allocation is missing. Stopped registered failures now retain
terminal training receipts and any completed fit. Missing work remains unknown;
invalid raw receipts block accounting. Cancellation after a durable fitting intent
now preserves terminal evidence in normal/recovered execution. Optimizer-step
counters and other kill profiles remain unqualified.
The versioned trained selected state now seals the fit and all training receipts,
with offline verification and complete closure archival. It preserves the
existing frozen-baseline reference journal. A capability declaration is required
at the barrier. The local `hydrology-learned-routing-v1` registration now trains
through an explicit fitting grant or infers from a declared verified selection.
Its authored worker tests include recovery and frozen inference without fitting
data. Scripted prediction/mixed route writers now archive and freeze exact trained
states with reserved training starts and inner routing work. Authored recovery and
baseline-reference tests preserve one original fit. Independent task admission,
private scoring, learned-alternative admission and installed/other-platform
qualification remain open. See
the [learned profile](../../docs/utility.md#learned-hydrology-development-profile).

The separate `engineering_load` profile now supports scalar resistance forcing
through the intact solver and supervised executor. See the
[load development example](../../docs/utility.md#circuit-load-development-profile).
Its authored parity/recovery tests do not evaluate or admit the proposed final
load cases. The native `engineering_load_native` recipe supports a supplied
controlling corner and retains fresh checks of every case. Installed development
execution, saved-result recovery and base-only native receipt reconstruction
have passed outside the checkout. Protected scoring and final task admission
remain open.

The separate `engineering_load_robust_native` recipe handles up to 24 supplied
cases without a combined corner. Its
[authored verification](verification-engineering-robust-native-v1/README.md)
covers native execution, separate scenario checks and installed core-only receipt
reconstruction. The new recipe now has selected-source installed execution on macOS ARM64; see
[installed evidence](verification-engineering-robust-installed-v1/README.md). Linux,
private scoring and independent task admission remain open.

Strict suite records, parent accounting and outcome tools now exist. Freeze
executable dossiers only after development profiling, data custody review and
numeric protocol completion. Consult
`docs/implementation-plans/part-5-utility-confirmation.md` for the full gates.


Optional report figures are described in docs/utility.md. Use report --figures
in an environment containing Matplotlib, then verify the numeric data in the
base environment or use --rerender-figures for image reconstruction. The saved
figure-rehearsal-v2 examples are authored illustrations, not scientific results.
The inconsistent first illustration is retained with an invalidation notice.

The exposed engineering tool rehearsal is runnable in the optional
`interoperability` environment:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_campaign \
  --output outputs/utility-engineering-campaign
```

Use an absent output directory. It runs a baseline, a registered current design
and a numerical study, then reviews and freezes the exact selected state. The
saved `development/engineering-campaign-v2` contains twelve stopped scenario
processes and offline reconstruction evidence. It does not execute suite routes
or independent confirmation. See `docs/utility.md` for the tool contract and
`docs/reviews/part-5-completion-audit.md` for remaining work.

The native SLSQP variant uses the same environment:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_native \
  --output outputs/utility-engineering-native
```

The final `development/engineering-native-v2` preserves sixteen stopped outer
processes and twelve inner native model calls. Native output receives fresh
scientific checks before selection. A successful optimizer returned a design just
below the strict voltage bound, which remained ineligible. No threshold was changed.
Outer process counts, inner calls and derivative work are separate quantities.
This remains exposed development, not a conventional-versus-agent comparison.

The seven-route engineering rehearsal adds scripted advice and parent-bound role
removals:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_routes \
  --output outputs/utility-engineering-routes
```

The final `development/engineering-routes-v3` uses one paired seed and the same
supplied choices for baseline, conventional, single-agent, four-role and three
mechanical-removal routes. It records 99 stopped scientific processes, 85 scripted
host calls and ten mechanical substitutions. These are code-path checks. They do
not measure LLM quality or independent utility. The producer does not freeze the
suite selection barrier or invoke confirmation, and it is not a public utility
execution-plan interface. Earlier -v1 and failed -v2 sources/journals are retained.

The declarative engineering plan uses the public utility commands and archives
selected sources/state for a separate suite freeze:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_plan \
  --output outputs/utility-engineering-plan
```

This producer runs one cell, resumes the rest, checks completed resume, then
separately freezes, verifies and inspects status. It requires a fresh output path.
The plan binds source closure, interpreter/packages and case-scoped execution v2.
It uses exposed circuit data and scripted hosts. It invokes no confirmation or
provider and does not qualify mixed-family or installed-wheel execution.

The three-family producer combines exposed Leaf River prediction, OEDI solar
prediction and the circuit design question in one 21-cell suite. Each task has
baseline, conventional, single-agent, multi-agent and three role-removal routes:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_mixed \
  --output outputs/utility-mixed \
  --solar-cache /path/to/existing/9068-cache
```

Use an absent output directory and the four already verified OEDI cache files.
The loader does not fetch data. Add `--prepare-only` to capture inputs and write an
unallocated suite without scientific or host execution. The full producer runs
one cell through the public CLI, resumes the remainder, checks completed resume,
then separately seals and verifies the selection manifest. This is scripted
exposed development. Wind, independent task admission and confirmation are separate
requirements. It provides no LLM or comparative utility result.

The wind parameter profile (`wind_parameters.py`) keeps turbine coordinates as
scalar parameters and preserves fixed V80 hardware, the rectangle and spacing
checks. Its model identity stays fixed across configurations. Native wind proposals
(`wind_proposal.py`) retain separate wake/gradient callback records and require a
fresh evaluation. A physically tolerated native point outside exact parameter
bounds produces no admissible configuration. Coordinates are never clipped.

The supervised wind parity probe runs in the wind environment:

```sh
pixi run -e wind python -m examples.utility.rehearse_wind_scenario \
  --output outputs/utility-wind-scenario
```

Use an absent directory. Two bounded processes evaluate the four Horns Rev corner
turbines, directly and through the adapter, under the same bundled distribution.
Completed replay launches no new process. The fixed direction step is numerical
configuration, not independent weather. This probe does not implement the public
wind route/native-process bridge or admit the wind task for confirmation.

The bounded native wind process can be rehearsed separately:

```sh
pixi run -e wind python -m examples.utility.rehearse_wind_native \
  --output outputs/utility-wind-native
```

Use an absent output directory. One reserved TOPFARM process may propose a layout.
Only an exact-domain feasible proposal receives a separately reserved fresh wind
evaluation. Callback attempts, completions, failures and unresolved work remain
separate from outer starts. Native convergence alone does not make a model eligible.
The saved development probe and guarded reader are under
`development/wind-native-process-v1` and `verification-wind-process-v1`. This is not
yet a wind route in the public utility matrix.

The public seven-route wind development rehearsal uses callback campaign v3:

```sh
pixi run -e wind python -m examples.utility.rehearse_wind_plan \
  --output outputs/utility-wind-plan
```

It shares one supplied model, parameter domain, scenario and numerical/native
recipes across scripted routes and role removals. Native callback receipts remain
separate from fresh scenario eligibility checks. This is an exposed bundled
wind-development suite, not independent weather confirmation or a utility result.

For one common four-family development suite, use the separate `utility` environment:

```sh
pixi run -e utility python -m examples.utility.rehearse_mixed --include-wind \
  --output outputs/utility-four-family --solar-cache /path/to/verified/solar/cache
```

The output must be absent and the exposed solar cache must already be available.
This prepares 28 cells with one source/lock closure and one parent selection barrier.
TOPFARM requires OpenMDAO 3.39.*, so `utility` pins 3.39.0 separately from the existing
3.41.0 interoperability profile. The old profiles and their evidence remain intact.
The installed wind execution check from exported inputs is recorded under
`verification-installed-science-v1`; it is not independent confirmation.

New wind preparations use execution v3 with bound spacing constraints. To check
rejection before model dispatch alongside one feasible supervised evaluation:

```sh
pixi run -e utility python -m examples.utility.rehearse_wind_preflight \
  --output outputs/utility-wind-preflight
```

An overlapping layout produces scientific infeasibility with unavailable outcomes
and no process reservation. Recovery verifies the original rejection receipt.
Legacy v1/v2 evidence retains its original identity and behavior. The saved probe
and offline rejection reader are under `development/wind-preflight-v1` and
`verification-preflight-v1`. This is development evidence, not independent weather
confirmation or evidence of a utility gain.

The saved four-family diagnostic figures and their full CSV exports are in
[development/diagnostics-four-family-v4](development/diagnostics-four-family-v4/README.md).
They show comparison prediction errors, circuit operating scenarios and the common
wind layout/spacing. Scripts in `scripts/utility_development_diagnostics.py` and
`scripts/render_utility_development_diagnostics.py` reproduce them from pinned
saved artifacts. A fresh installed reader reconstructed the tables outside the
checkout without models or original-source access. All views remain exposed
scripted development evidence, not independent confirmation or utility findings.

The [Claude policy evidence](verification-claude-policy-v1/README.md) records limited
macOS syscall/help/synthetic-helper probes and their failed predecessors. The
archive reader checks saved evidence after relocation without launching programs.
This is not an admitted Claude host or a live utility comparison.

The later [native loopback evidence](verification-claude-loopback-v1/README.md)
exercises the real CLI helper hook and structured-output mechanism with authored
local events. Its installed readers verify saved evidence without models or the
checkout. No provider calls, real authentication or production admission are claimed.

## Offline inference environment inputs

[inference_environment.py](inference_environment.py) prepares and verifies a pinned
Linux x86-64 environment input package without importing wheel code, acquiring
archives, installing dependencies or starting science. It retains the existing
lock's dependency selection rather than solving a new environment. See the
[prepared package](prepared-inference-environment-v1/README.md) for its exact hashes,
size, proposed resource bounds and unresolved image/guest/boundary requirements.
This is an administrative preparation tool; it does not register a private runtime.


[guest_image.py](guest_image.py) prepares a source-matched, pinned image recipe
without fetching or running it. See the [candidate image package](prepared-guest-image-v1/README.md)
for payload bounds, immutable public metadata, unrun qualification cases and
missing execution prerequisites. This does not admit an inference runtime.


[guest_image_context.py](guest_image_context.py) materializes a reviewed recipe from
already-present pinned files and verifies its relocated closure. It does not fetch
or build anything. See the [context verification](verification-guest-image-context-v1/README.md)
for authored test scope and the missing production inputs.


[guest_archive_download.py](guest_archive_download.py) prepares and executes pinned
archive-only requests with no automatic retries, installation or image execution.
[Actual acquisition evidence](verification-guest-archive-download-v1/README.md)
records the verified local archive cache and materialized production context.


[guest_image_build.py](guest_image_build.py) prepares a pinned local candidate-image
job. [The prepared request](prepared-guest-build-v1/README.md) requires separate
approval for base-image acquisition and image assembly. It does not run scientific
confirmation or admit the runtime.


The bundled authored source CSV example runs without models or source acquisition:

```sh
pixi run python -m examples.utility.solar_csv_demo --output outputs/solar-csv-demo
```

Use a new output directory. The example exercises explicit source/clock/quality
policies and separated preparation. Its public authored values do not establish
site semantics or independent confirmation. See
[installed evidence](verification-solar-csv-installed-v1/README.md).

[CAMELS archive verification](../../docs/reviews/part-5-camels-archive-verification.md)
checks exact selected members in a supplied local archive without downloading or
extracting files. Its authored tests do not establish real source admission.

[Current CAMELS catalog review](../../docs/reviews/part-5-camels-catalog-review.md)
records anonymous metadata/range access, repository terms, exact member names
and source quality documentation without acquiring time series.

[Legacy CAMELS methods and NoData review](../../docs/reviews/part-5-camels-timing-review.md)
records the remaining timing gap and a parser repair that rejects documented
-9999 forcing sentinels before partition preparation publishes data.

[Further solar equipment review](../../docs/reviews/part-5-solar-equipment-source-review.md)
records the current regular metadata tables and prize header change logs. Neither
repairs the selected prize site's missing equipment or clock mapping.

[Engineering preflight refusal](../../docs/reviews/part-5-engineering-preflight-refusal.md)
records a consumed development attempt stopped by daemon identity drift and the
subsequent durable, sanitized preflight-reporting repair.

[Revised engineering development reference](proposals/engineering-v3/README.md)
contains a frozen public task definition, 24 actual coupled baseline receipts and
a separately bound proposed absolute gain. No confirmation source was generated.

[Revised engineering conventional profile](../../docs/reviews/part-5-engineering-conventional-profile.md)
records a bounded public SLSQP design and the native-pass accounting distinction,
including failed observers and a retained false buffered-target check.

[Engineering envelope registration](../../docs/reviews/part-5-engineering-envelope-registration.md)
connects that recipe to the typed native driver interface. Result v3 preserves
the fresh corner solve outside the scored population and charges it to the same
inner-call limit. Direct model and supervised fixture checks remain development
evidence.

[Supervised engineering envelope check](../../docs/reviews/part-5-engineering-envelope-supervision.md)
records actual baseline, native-driver and fresh candidate processes through
selection freeze. The 83 root calls and a repaired oversized metadata publication
remain separate from earlier development controls.

[Reserve prior-use attestation](../../docs/reviews/part-5-reserve-exposure-attestation.md)
records the task owner's explicit no-prior-use reply for the three named real
source reserves. Exact source and custody admission remain open.

[Wind NetCDF environment experiment](../../docs/reviews/part-5-wind-netcdf-environment.md)
retains a local patch's passing authored I/O checks and failed broader regression.
The candidate was not promoted and no scientific wind model ran.

[Actual CAMELS source inspection](../../docs/reviews/part-5-camels-actual-source.md)
records full published-checksum verification, selected-member validation and the
actual hour-12 versus README-zero conflict. Only metadata and quality counts were
exported. Timing and task admission remain open.

[Current-owner scientific control](../../docs/reviews/part-5-engineering-current-owner.md)
records a fresh current-daemon profile, one container with 24 coupled solves and
original-score recovery after commit loss. The old failed source/grant remains
consumed. Full private-runtime and task admission remain open.
