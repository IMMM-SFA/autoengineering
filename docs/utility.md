# Utility comparisons

Part 5 is under implementation. The current package validates immutable utility
matrices, prepares pinned task inputs, accounts for bounded child batches, seals
selections and reconstructs offline evidence. Development adapters cover hydrology,
measured-POA solar, a coupled circuit and supplied wind layouts. Their rehearsals
use exposed development inputs. No independent utility suite has been executed.
See the [interim handoff](utility-handoff.md),
[progress record](reviews/part-5-progress.md) and
[implementation plan](implementation-plans/part-5-utility-confirmation.md).

## Learned hydrology development profile

The initial learned-routing profile now has a versioned frozen selection format.
`TrainedSelectedState` uses `utility-selected-state-v2` and includes
`RoutingSelectionArtifacts`: the fit, profile, intent, result, bundle and parent
lifecycle references. Existing v1 states retain their format. The learned routing
profile cannot use v1 to omit its fitted object.

`read_selected_state(root, artifact)` reads both versions. For v2 it verifies
every artifact digest, the successful original training result, declared model
sources/parameters/seed, fitting prefix, initialization, daily interface and
lifecycle/evaluation binding. It checks original work counts and durations without
loading labels, importing a model or running an optimizer. Companion bytes retain
the parent's 4 MiB total limit, checked before loading the closure.

`archive_selected_state(..., training_root=campaign_root)` copies the complete
verified closure alongside the model sources. The suite barrier requires child
attestation, a frozen candidate, the hydrology task family and an explicit
`frozen_trained_inference` capability request. That request does not qualify an
executor. Ordinary cells keep their fitting/execution seed. An already verified
frozen-baseline reference retains its original source cell's seed and fit, even
when a follower has another logical seed. No fit or scientific execution occurs
during archival, reading or reference copying.

Untrained selections retain their v1 states. The scripted coordinator now writes
v2 states for the supplied trained routing profile. The trained record does not
provide a private scorer or replace the parent's scientific acceptance checks.
Local registered execution is described below. Private
confirmation dispatch and failed-worker receipt capture remain open.
The earlier full base-suite checkpoint predates this increment. Authored sealing,
relocation, reference-journal and tamper checks run with:

```sh
pixi run python -m pytest tests/test_utility_trained_selection.py -q
```

`join_campaign_costs` reconstructs successful profiled training from the event
that originally committed its evaluation and lifecycle. The fit, bundle and all
companions must belong to that same event. Model/configuration/seed identity and
original work counts are checked through the frozen selection verifier. Training
cost remains visible when scientific acceptance rejects the evaluation.

Frozen inference adds no training start. Preparation remains unknown when the
original fit is outside the verified batch, or when reuse crosses cells without
an allocation rule. An existing frozen baseline reference policy distributes
original selection and training receipts once. Generic unprofiled training keeps
explicit unknown work and duration. Outer worker duration overlaps training and
must not be added to training duration as independent work.

These are public artifact readers. Authored supervised helper tests exercise
actual fitting and recovery. Separate registered-worker tests below cover local
dispatch. Real-task fitting data admission, private scoring and the independent
study remain open.

Campaign version 1.1 now supports an explicit `TrainingSpec` with profile
`daily-prefix-supervised-v1`, allowed trusted adapter IDs and one fitting data ID.
Version 1.0 retains its exact serialized fields and receives no fitting payload.
The fitting contract must be exposed daily NPZ observations on an exact forcing
prefix, with matching calendar, timestamp and warmup. Variable-specific physical
semantics remain unchanged. Unscored labels become zero placeholders and retain
an explicit Boolean mask. No date joining or interpolation occurs.

The parent commits a fitting grant with the original attempt reservation. It binds
campaign/model/configuration, adapter, fitting contract, forcing, seed, nonce and
attempt. The worker verifies this commit before reading labels. Training uses a
fresh scratch directory for each attempt. Recovery verifies the same grant and
retains the original successful fit without launching another worker. The policy
refuses confirmation, diagnostic and altered-forcing training. Frozen inference
uses a separate declaration with no fitting permission.

This is a trusted adapter data contract, not filesystem isolation. The supplied
`hydrology-learned-routing-v1` adapter now uses the normal campaign worker. Declare
`routing-runtime.json` in the campaign's provenance sources as application/json.
Its `RoutingRuntimeProfile` contains schema `utility-routing-runtime-v1`, the
immutable site, training profile and an optional trained selected-state reference.
All model source modules and the current entire engine must be declared. Older
engine allowlists alone do not cover this runtime.

For training, leave `selected_state` null and declare the adapter in the campaign's
1.1 training policy. For frozen inference, supply a verified v2 selected-state
reference, declare its six training closure artifacts, and grant no fitting data.
The runtime reads only verified JSON fits and copies their closure into the fresh
attempt scratch. The usual lifecycle publishes the new inference outputs and
retains the original fit. No fitting intent or result is created for inference.
Frozen campaigns can omit fitting data entirely. Saved-worker recovery retains
one original reservation. Training and inference use the same fixed model code.

Actual authored registered-worker tests cover training, recovery, frozen inference
and closure/permission refusal. This is local source-checkout coverage. It does not
admit private scoring, another host/platform, installed packages or an independent
basin. The scripted prediction and mixed coordinators archive the exact selected
fit from its original lifecycle commit. The writer checks every training closure
member in that event before creating a v2 state. Baseline, conventional, single-agent
and multi-agent scripted routes use the same writer and freeze barrier.

Declare the fitting profile digest in each route's scientific grant and request
`frozen_trained_inference` on the hydrology task. A training route also needs reserved
count limits named `training_starts` and `training_routing_starts`, both in its recipe
and suite budget. Before creating a child, the parent reserves one possible fit for
every allowed scientific attempt and the profile's maximum rollouts for each fit.
Missing profile permission, capability or allowance refuses before scientific
dispatch. The fitting policy participates in the numerical recipe identity.

`CaseBinding` retains its legacy serialized fields when training is zero. Positive
training and rollout allowances enter the child mapping and parent reservation.
Actual training costs still come from original attempt receipts. Reserved upper
bounds are not reported as measured work. An interrupted coordinator reuses saved
scientific responses; it does not refit while reconstructing the selection. Frozen
baseline followers reserve no new training, keep the source fit's original seed
and distribute its one original cost receipt under the existing frozen policy.

Stopped registered training workers now retain `TerminalTrainingEvidence` when no
successful model lifecycle is available. Its original evaluation commit includes
the fitting grant, profile, available intent/result and any completed JSON fit.
The cost reader verifies the original reservation and complete terminal closure
without scratch, source modules, labels or execution. A completed fit remains
charged when later inference fails. Failed fits retain their reported starts,
completions, duration and partial-work flags.

An intent without a result proves one training start, while work counts and
duration remain unknown. If no intent survives, training work remains unknown.
Invalid receipt bytes are retained with an invalid marker and block accounting.
Unverified process stop never permits reading mutable training scratch.

Recovery accepts the original stopped supervisor proof for a supplied registered
worker's model failure or timeout. A pending cancellation also permits its original
cancelled supervisor proof, retaining terminal training evidence in the cancellation
commit. Ordinary failures also need matching worker
start/finish records. An early timeout can precede the worker start record; its
owned process identity, nonce and stopped supervisor proof still bind the outer
charge. Conflicting or missing proof leaves the attempt unresolved and blocks
automatic retry. No replacement worker is launched during reconciliation.

Authored tests cover actual rollout-budget failure, failure after a completed fit,
early timeout, saved-worker recovery, receipt loss and cold reconstruction. Actual
registered-worker cancellation after a durable training intent now retains one
training start and unknown partial work, including recovery before parent commit.
Conflicting proof leaves the reservation unresolved. These checks do not establish
optimizer-step counters, other kill/adapter profiles or independent task admission.

Protected inference before private scoring remains an unqualified candidate profile.
The existing private scorer accepts frozen vectors and runs no scientific model.
The [protected prediction increment](implementation-plans/part-5-frozen-prediction-increment.md)
specifies both physical starts, driver-only access, frozen state replay and explicit
parent/child execution bindings. Its versioned grant and replay metadata are now
implemented. `CompositeConfirmationGrant` uses `utility-confirmation-grant-v2`,
requires exactly two scientific starts and reserves the inference timeout plus
model stop grace and the fixed vector scorer's lifecycle allowance. Training and
host calls remain forbidden. The legacy grant retains its fields, one-start rule
and canonical bytes.

`FrozenRoutingInference` validates the original seed, selected-state reference,
driver interface, unchanged historical daily axis/warmup, and site/training profile
hashes. It permits a declared chronological extension with a new scoring mask.
Metadata validation reads no driver arrays or labels and imports no model. A task
must explicitly request `protected_frozen_routing_score`. This request does not
qualify a runtime. Current vector-only services reject composite execution and
recovery before reservations or access. A legacy score receipt cannot complete a
two-start composite attempt. A candidate trusted local inference stage now runs
through `FrozenRoutingExecutor` and the fixed `inference_worker` module. It requires
the original reserved composite access, source/lock pins and a create-only suite
claim before reading drivers. Claims bind the job, nonce, executor and an opaque
workspace digest. They prevent another workspace from repeating the same grant.

Only the declared drivers, frozen fit closure and verified code are staged. The
original driver-root path and labels are not supplied to the worker. Numeric fitting
prefix checks and fixed water-balance/nonnegative/capacity checks precede vector
publication. Both full model outputs and the bound vector are retained. Historical
outputs match the original selected run exactly when the axis extends. No training
intent/result is created. Model failure, timeout and infrastructure/output-limit
failure remain distinct and supply no scoring vector.

Recovery verifies original job/claim, process identity, stopped supervisor and
result hashes. It reads neither original nor staged drivers and starts no worker.
Missing completion proof remains unresolved; another execution is refused. A suite
cancellation prevents new inference while allowing original-result recovery.

This is an unregistered trusted-process candidate, not a qualified private boundary.
Process timeout, array/output bounds and lifecycle recovery have authored tests.
OS isolation, memory/CPU bounds, preparation deadlines, broader cancellation and
pre-launch recovery remain open. A separate `CompositeRMSEScorer` and explicitly
constructed `CompositeConfirmationService` now connect saved inference to the fixed
vector scorer. The default vector-only service remains closed to composite grants.
No private runtime or independent data is admitted.

The composite registration pins inference, executor, label hash, vector source and
runtime, partition and outcome before access. It explicitly declares an unqualified
candidate boundary. The parent grant identity stays fixed. After successful
inference, a create-only public transition binds its archived closure to a subordinate
one-start vector grant whose identity includes the actual prediction hash. That
handoff precedes inner label access. It does not reserve another suite attempt or
replace the parent's identity. Failed inference publishes its original nonnumeric
status without entering the scorer.

Composite receipts bind both stages and their exact public score. An inner score
requires original container-execution metadata. Public readers verify job, intent,
claim, original stop/result evidence, physical checks, output/vector hashes and the
parent/child transition. They need no drivers, labels, model imports, array loading,
process inspection or network. This verifies trusted producer records; it cannot
independently attest OS isolation or process stop. Authored runtime metadata in
tests is not container qualification.

Recovery reuses archived inference and the original saved vector result. It never
starts an unfinished scoring stage. Loss before inner completion remains charged
and unresolved. Cancellation between stages blocks new scoring. Accounting retains
verified inference starts/duration even while the outer attempt is unresolved.
Pending scoring starts stay unknown. Completed inner execution supplies its own
starts/duration; callback time overlaps both stages and must not be added to them.

The separate administrative helper `examples.utility.inference_environment`
prepares pinned Linux x86-64 environment inputs offline. It reads the existing
schema-7 default lock selection and a pure project wheel, follows declared core
dependencies, retains archive hashes/sizes/licenses and publishes a new private
package manifest last. It neither resolves a new environment nor independently
rechecks version constraints. Its reader needs an explicit reviewed digest and
reconstructs the exact metadata from saved lock/wheel bytes. Corrupt pins, unsafe
wheel members, interrupted publication and existing outputs refuse. No archives
are acquired, no wheel code is imported and no environment is installed.

The [prepared inputs](../examples/utility/prepared-inference-environment-v1/README.md)
contain 49 archive pins totaling 265,399,717 compressed bytes. An image identity,
guest transport contract and actual boundary qualification remain open. The review's
memory/CPU/workspace/time values are proposals. `starts_authorized` and
`runtime_qualified` remain false. The current v1 job's host interpreter/workspace
binding cannot be assumed portable into that guest. This helper does not change
runtime registrations, scorer allowlists or any confirmation grant.

Candidate `FrozenGuestInferenceJob` dispatches through schema
`utility-frozen-inference-job-v2`. V1 job fields and serialized shape remain exact.
V2 binds an unqualified `FrozenGuestProfile` covering the reviewed environment,
lock/wheel/source hashes, immutable image ID, Linux x86-64 CPython version/build and
proposed limits. Its scope is independent of host/guest path names and remains
bound to the original grant/executor/nonce. Job/intent/claim hashes must still agree.

Before selected-state/model/driver reads, the fixed worker verifies observed Python
identity, pinned environment metadata and installed code bytes. Missing/extra or
changed core sources refuse. Old wheel metadata without guest transport sources
refuses. Cold job parsing performs no runtime probe or environment read. These
checks do not attest OCI image identity or enforce OS/privacy/resource controls.
V1 supervisor archives reject guest jobs. A qualified owner-side launcher and guest
receipt/archive chain remain unimplemented, and no default service/CLI registers
this profile. See the [successor input package](../examples/utility/prepared-inference-environment-v2/README.md).

`guest_receipts` adds a separate candidate public archive and cold reader for guest
executions. It binds the original job/environment and suite claim to a fixed launch
policy, start, stopped state, cleanup and bounded capture. Original capture digests
remain explicit. Completed worker results retain physical checks and full output
hashes. Timeout, cancellation, OOM/dead/failed exit and incomplete capture stay
nonnumeric and supply no scoring vector. Model and scientific failures preserve
their own status. Unknown lifecycle time stays null.

The caller supplies source, lock, executor and runtime pins. The reader verifies
only saved public metadata/bytes, without model imports, array loads, runtime probes,
processes, network or private inputs. Authored lifecycle projections test this
contract; they are not actual OCI observations. The returned boundary remains
unqualified. The owner must qualify/enforce the actual image/API/policy and validate
original observations before export. The existing local execution archive does not
accept guest proofs, and no default service or launcher integrates the new type.
See [receipt evidence](../examples/utility/verification-guest-receipts-v1/README.md).

`examples.utility.hydrology_learned` replaces linear reservoir routing with a
supervised two-coefficient release rule. It retains the site's PET and soil bucket
and exposes the same AET, discharge and storage outputs. For available reservoir
water `R`, the release fraction is `logistic(b0 + b1 * log1p(R / 100 mm))`.
Discharge is that fraction times `R`, and the remainder stays in the reservoir.
This preserves daily water balance and nonnegative storage. The fixed feature
scale is not estimated from selection data. Capacity and PET family remain
explicit model parameters. The old linear recession parameter is absent.

`RoutingTrainingProfile` freezes the contiguous fitting prefix, warmup count,
quality mask and maximum routing rollouts. At least 20 usable labels are required
outside warmup. This is a software guard, not a claim of statistical adequacy.
Training uses bounded SciPy least squares with intercept in [-6, 6] and storage
coefficient in [0, 3]. It refuses failed optimization and a rank-deficient fitted
numerical Jacobian. Full numerical rank does not establish general identifiability.
There is no observed-discharge input at inference and no fitted normalization.

After verifying public preparation artifact hashes, use
`prepared_training(plan, forcing_document, fitting_document, parameters, scratch,
max_rollouts=120)` to obtain `(site, profile, context, forcing, fitting_data)`.
The bridge includes only warmup/fitting drivers and fitting labels in the training
mapping. Selection and reserved label documents refuse. Pass the mapping through
`run_lifecycle(..., fitting_data=fitting_data)` with
`LearnedRoutingAdapter(site, profile)`. The returned training artifact contains
coefficients, feature/algorithm identity, fitting-data and forcing digests,
source/environment binding, seed, duration and work counts.

Load the frozen artifact with `load_training(root, artifact_reference)` and use
`LearnedRoutingAdapter(site, profile, frozen)` for inference. It accepts no fitting
data, invokes no optimizer, and verifies that its driver prefix exactly matches
training. The daily axis may extend beyond fitting while retaining initialization
and causal state replay. Changed parameters, sources, seed or training profile
require a different fit. One fresh handle permits one history replay.

Training writes a create-only intent and result in its owner-private scratch
directory. Version 2 intents/results bind a unique training attempt ID, so repeated
fits under the same model identity remain separate work. A second start in that
directory refuses. An interrupted intent without
a result remains unresolved. Known failures retain elapsed time, routing starts,
completed rollouts and partial-work uncertainty without private exception text.
The rollout cap includes numerical-derivative calls. `TrainingResult.cost` uses
routing rollouts for this profile, with the unit recorded in the artifact.
Flux preparation is counted separately. Durations, CPU/RSS and total work still
need the enclosing qualified supervisor and suite accounting. No automatic
training-recovery or independent/private execution registration is supplied.

`autoengineering.utility.hydrology_training.read_training_costs` reconstructs
`CostRecord` quantities from committed intent/result references and the frozen
expected model identity, profile, seed and cell digest. It checks the actual fit
artifact, limits, durations and consistency of starts versus completed work.
Missing results and partial work retain unknown quantities. Duplicate references
retain the same receipt identities and are rejected by cost reconciliation.
Repeated physical fits retain different training IDs and separate charges.

The reader imports no model or optional framework and executes no optimizer.
Core NumPy/SciPy dependencies remain available through the generic artifact reader.
It needs only copied public artifacts, not fitting labels or original model/data
directories. Training elapsed time overlaps outer process/lifecycle time and
must not be added to it. Starts, completions and reserved days are different
quantities, not additional copies of the same execution cost.

Callers must obtain references from the authoritative parent commit. This reader
does not establish that parent binding, supervise training or enforce suite
reservations. It accepts only v2 training intents/results. Older v1 development
records remain outside this cost projection. The profile/fit record schemas keep
their prior meanings. The parent now captures successful training artifacts and
explicit bundles in its lifecycle event. Automatic training-cost validation against
that event and suite report integration remain open:

```sh
pixi run python -m pytest tests/test_utility_hydrology_training_costs.py -q
```

`TrainingArtifactBundle` declares one primary trained artifact and at most eight
content-addressed companions. The learned profile exports its fit, profile,
intent and result this way. Its returned artifact metadata names the bundle.
The parent verifies the worker's output hash, duration and training record, copies
the declared closure, then commits those references with the lifecycle record and
original scientific attempt. Companion bytes are bounded at 4 MiB in total.
Untrained lifecycle metadata keeps its original bytes. Training-bearing lifecycle
records use version 2 and retain the original worker training reference alongside
the campaign reference.

Normal completion and saved-worker recovery use the same capture code. Recovery
copies verified saved bytes without rerunning training or scientific work. Once
the parent event commits, readers need no worker scratch to verify the retained
closure. This transport does not admit a training profile or supply fitting grants.
Failed/timed-out training without a completed worker envelope still needs a
qualified terminal-receipt path. Its inner work must remain unknown. Authored
transport checks run with:

```sh
pixi run python -m pytest tests/test_campaign_training_artifacts.py -q
```

The authored tests recover known coefficients and check conservation, fitting
scope, frozen inference, integrity and failed-work accounting. No real basin has
been trained, and no useful predictive gain is established. The old profile's
learned-candidate admission refusal remains in place:

```sh
pixi run python -m pytest tests/test_utility_hydrology_learned.py -q
```

## Hydrology partition preparation

`examples.utility.hydrology_camels` supplies a separate bounded CAMELS-US Daymet
parser for trusted preparation. It accepts bytes, makes no network requests and
extracts no archives. A `CamelsDaymetSource` binds the eight-digit gauge,
forcing/streamflow SHA-256 checksums and the declared forcing hour (0 or 12).
`CamelsArchiveDaymetSource` (`utility-camels-us-daymet-source-v2`) additionally
requires the declared legacy archive and archive-metadata SHA-256 hashes and
HUC02. It fixes the collection to the CAMELS v1p2 basin-mean Daymet archive and
provides expected member paths. The base source decoder dispatches both versions.
Existing version-1 diagnostics retain their serialization and behavior.

Version 2 explicitly uses the same published date without an hour shift and
requires a complete published Gregorian axis without filling. It keeps physical
interval interpretation unresolved and archive membership unverified. The parser
receives member bytes, not archive bytes, so it cannot authenticate their archive
membership. Acquired archive/member provenance still needs an independent check.
Modern Daymet v4 and CAMELS-SPAT timing/calendar conventions cannot substitute
for that evidence. See the [source-version review](reviews/part-5-camels-source-version.md).

`examples.utility.hydrology_camels_archive.read_archive_rows` checks local archive
membership separately. Supply an already open regular binary file, version-2
source and bound plan, exact metadata bytes and a prospective archive-byte cap.
It hashes the complete archive before parsing a bounded central directory and
decompressing only the two exact selected members. It returns a metadata receipt
and private rows. Ordinary and ZIP64 single-volume stored/deflated archives are
supported. It never downloads data or writes extracted files. Invoke it lazily
inside the iterator passed to `prepare` so preparation claims precede reads.
The receipt does not change the source descriptor's admission flags. See the
[archive verification review](reviews/part-5-camels-archive-verification.md) for
the limits, tested preparation pattern and cost scope.

The [current CAMELS catalog review](reviews/part-5-camels-catalog-review.md)
preserves the repository's open/CC BY 4.0 declaration and historical registration
statement. Archive documentation confirms the member paths, basin-area and
streamflow units, and `A`, `A:e`, `M` quality flags. `A:e` remains a distinct
estimated value and participates only when the frozen plan explicitly permits
that flag. Missing values never become usable merely by allowing `M`. Metadata
range access does not qualify daily physical intervals, actual data coverage or
independent confirmation.

Bind `plan.declared_source_digest` to `source.digest` and use site ID
`usgs-<gauge_id>`. The plan's latitude and area must match the forcing header,
whose area is in m2. No streamflow-derived attributes are loaded.

Pass `iter_rows(source, plan, forcing_bytes, streamflow_bytes)` directly as the
rows argument to `prepare` below. It validates both bounded files before yielding
rows. Parsing starts after the preparer claims both output scopes. Each file is
limited to 4 MiB and 20,000 data rows. The parser requires the Daymet column names
and units, matching flow gauge and date columns, and an exact daily axis covering
the plan. It neither sorts nor fills gaps. Daily precipitation in mm/day becomes
the one-day interval total in mm. Flow stays in cfs until preparation converts it.
Only the supported -999 flow sentinel becomes missing. Other negative or
nonfinite flow values refuse. Quality flags are retained for the plan's mask
policy, and observed zero flow remains usable. Missing meteorological drivers
refuse preparation. Both -999 and the legacy Daymet -9999 forcing sentinel are
rejected, including temperature extrema that otherwise pass finite/order checks.
See the [legacy methods and NoData review](reviews/part-5-camels-timing-review.md).

Format references are the
[eWaterCycle-HBV Daymet documentation](https://ewatercycle-hbv.readthedocs.io/en/stable/autoapi/ewatercycle_HBV/forcing/index.html)
and [NeuralHydrology's CAMELS-US loader](https://github.com/neuralhydrology/neuralhydrology/blob/master/neuralhydrology/datasetzoo/camelsus.py).
The [NCAR hour-field discussion](https://github.com/NCAR/CAMELS/issues/1) identifies
a difference between documentation and Daymet files. This parser preserves the
date column and checks the declared hour without shifting dates. Scientific
admission must resolve the forcing/flow interval interpretation. A checksum match
alone does not establish authentic gauge attribution for the forcing file,
rights, prior exposure or private execution. No real CAMELS files have qualified
this parser. Authored checks run with:

```sh
pixi run python -m pytest tests/test_utility_hydrology_camels.py -q
```

`examples.utility.hydrology_partitions` prepares canonical daily records without
running a model or making network requests. It is a separate preparation profile
from the historical Leaf River cache. A `DailyHydrologyPlan` binds source/site
identifiers, a declared source digest, basin area, latitude, accepted flow-quality
flags and four contiguous windows: warmup, fitting, selection and confirmation.
Use portable site names such as `usgs-01491000`.

Pass normalized `DailyHydrologyRow` records to
`prepare(plan, rows, public_root, private_root)`. Both output directories must
already be empty, owner-private and separate, with no symlink components. The
preparer claims their roles before iterating rows. It commits private artifacts
first and the public manifest last. Interrupted or occupied roots cannot be reused.

| Scope | Artifacts |
| --- | --- |
| Development | `forcing.json` ends at selection. `fitting.json` and `selection.json` each contain labels only for their named role, with Boolean masks. |
| Reserved | `forcing.json` contains the complete driver history for replay from the selected model's frozen initial state. `labels.json` exposes observations only at confirmation-mask positions. It has the fixed RMSE worker's `labels`/`mask` format. |
| Control | Both scopes retain immutable preparation claims. Claims and manifests bind the preparer source digest. Manifests also bind the plan, normalized rows and artifact hashes. The public manifest contains no private directory path. |

Precipitation is a one-day interval total in mm. Mean temperature is explicitly
the midpoint of daily minimum and maximum temperature. Flow converts from cfs to
mm/day with the defined SI factor and the supplied basin area. Unknown flags and
missing labels are masked. Masked entries contain zero placeholders, which are
not observations or imputed scores. Missing drivers, date gaps, duplicate dates,
negative unprocessed flow and any requested role without usable labels refuse
preparation. Bounds are 20,000 rows and 4 MiB for each data artifact.

The source parser must explicitly handle raw missing-value sentinels and verify
original source bytes. This preparer does neither. It does not attest exposure,
admit a scientific adapter or provide an OS boundary against the same user.
The separate `examples.utility.hydrology_site` profile supplies a basin-specific
model contract. The final privacy/source admission checks remain required before
real use.

`HydrologySite` binds source/site, latitude and basin area. Its latitude range is
-66 to 66 degrees because the supplied PET solar geometry does not handle polar
conditions. `SiteHydrologyAdapter` calls the existing Hamon or Hargreaves function
with that latitude. It retains the bucket and conservative linear-reservoir
equations, capacity/recession bounds, initial soil at half capacity and initial
reservoir at zero. Basin area binds identity and discharge preparation. The
adapter's fluxes already use mm/day and are not rescaled by area.

For an already hash-verified public forcing document, call
`prepared_development(plan, document, parameters, scratch, role="selection")`
or use `role="fitting"`. It returns `(site, context, forcing)` for
`run_lifecycle(SiteHydrologyAdapter(site), context, forcing,
context.model.inputs, context.model.outputs)`. Each role replays the complete
development driver history from initialization. Its scoring mask selects only
that role's dates. Apply label-quality masks separately when scoring. The bridge
accepts only meteorology ending at selection, rejects label fields and reserved
dates, and verifies the declared min/max temperature midpoint.

Use one fresh handle per history replay. A handle refuses a second run to avoid
advancing stores twice through the same dates. Port units, daily timing, site
identity, implementations and meteorological ordering are checked before model
execution. The old Leaf River profile and PET defaults remain unchanged. These
authored checks do not establish CAMELS source coverage or scientific adequacy:

```sh
pixi run python -m pytest tests/test_utility_hydrology_site.py -q
```

Authored separation, interruption, quality-mask and scorer-format checks run with:

```sh
pixi run python -m pytest tests/test_utility_hydrology_partitions.py -q -p no:cacheprovider
```

## Circuit load development profile

`examples.utility.engineering_load` adds explicit `ground_voltage` (V),
`resistor1_ohm` and `resistor2_ohm` scalar inputs. Only `source_current` (A) is a
design variable. Resistances must be finite and positive. The wrapper sets the
upstream resistor options once, then calls the existing OpenMDAO adapter and
coupled solver. Its residual check uses the actual resistances. Its graph and
source identities differ from the original ground-only profile.

In the optional `interoperability` environment, this authored development case
uses load values outside the proposed final-test scenarios:

```python
from pathlib import Path
import numpy as np
from autoengineering.adapters.python import run_lifecycle
from examples.utility.engineering_load import adapter, context

ctx = context(.05, Path("outputs/load-smoke"))
forcing = {"ground_voltage": np.array(.025),
           "resistor1_ohm": np.array(110.), "resistor2_ohm": np.array(9000.)}
result = run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
print(float(result.diagnostics["residual_norm"]))
```

The supplied `examples.utility.engineering_load:execute` callback works through
`SupervisedEngineeringExecutor` with declared source closure, batch reservations
and saved-result recovery. It provides trusted development execution, not private
confirmation. The proposed 24 final scenarios have not been evaluated by these
development checks.

`examples.utility.engineering_load_native:execute` adds the native SLSQP recipe
for scenario sets containing their controlling corner: minimum ground voltage,
minimum R1 and maximum R2 in one supplied case. It rejects other sets before
constructing a problem. The full OpenMDAO model, total derivatives and current
bounds of 0.01-0.1 A remain. Each native model call is counted, with capacity
reserved for a fresh independent solve of every supplied scenario. Exhaustion
stops the driver. An optimizer success flag cannot override the subsequent
strict scientific voltage check.

`examples.utility.engineering_load_robust_native:execute` is a separate recipe
for up to 24 supplied cases without a combined corner. It selects the case
requiring the largest source current at the common voltage threshold, then uses
native SLSQP and freshly checks every case. The original corner recipe is unchanged.
The [authored verification](../examples/utility/verification-engineering-robust-native-v1/README.md)
documents the exact passive-circuit reduction, work accounting and qualification limits.

The original combined-corner reduction follows from the fixed passive circuit equations.
Set `x = V2-G`
and `d(x) = Is * (exp(x/Vt)-1)`. Then
`R1*I = x + (R1+R2)*d(x)`. For positive current and resistances, `x` and `d(x)`
are positive. With `A = 1+(R1+R2)*d'(x)`, the partial derivatives are
`dx/dR1 = (I-d(x))/A > 0` and `dx/dR2 = -d(x)/A < 0`.
The node voltage also increases one-for-one with ground voltage. That proves
which supplied case controls the lower voltage constraint. In every case,
source power `I*(V1-G)` increases with positive current, so its mean is minimized
at the lowest feasible current. Optimizing the controlling case therefore has
the same minimizer as optimizing mean power for this declared scalar profile.
This argument does not admit other circuit components or design variables.

Authored development tests compare the result with the independent circuit-law
boundary and verify native derivatives, fresh-case records, exact call caps,
owned-process costs and saved-result recovery. A matching wheel has also run
two fixed-load processes and one native process outside the checkout using
exported source/lock inputs and inherited interoperability dependencies. Both
completed paths recovered without new starts. A base-environment reader verified
the copied native report and parent receipts with original source/run roots,
scientific model imports, subprocesses and network access denied. It preserved
all 51 copied files. The [installed development evidence](../examples/utility/verification-engineering-load-installed-v1/installed-execution.json)
records the executed harnesses and results. Installed callers supply the captured
source root, including its lockfile. Protected scoring and final task admission
remain open.

## Offline example

The bundled fixture is an authored two-cell schema example. Its placeholder hashes
are not executable scientific provenance. Preparation reports missing admissions,
source/lock closure and task families. Every fixture selection is not_attempted.
These commands launch no models or providers:

```sh
autoengineering utility validate examples/utility/fixtures/suite.json
autoengineering utility prepare examples/utility/fixtures/suite.json \
  --source-root . --workdir outputs/utility-offline
autoengineering utility status outputs/utility-offline
autoengineering utility freeze outputs/utility-offline examples/utility/fixtures/selection.json
autoengineering utility report outputs/utility-offline --format markdown
autoengineering utility verify outputs/utility-offline
```

Use a new work directory. Preparation refuses to overwrite existing evidence.
`verified_integrity` means saved evidence matches its hashes and journal. It does
not mean the task was admitted, costs are complete or confirmation succeeded.
`cancel WORKDIR` prevents new parent dispatch while retaining charges. Existing
child processes require their own stop/reconciliation evidence.

Fixtures are discoverable after installation with
`importlib.resources.files("examples.utility").joinpath("fixtures/suite.json")`.
The development adapters require their source/data closures and optional runtimes;
installation of the offline reader does not qualify those model environments.

## Evidence contracts

`UtilitySuiteSpec` binds ordered tasks, routes, cells, grants, budgets and protocol
identities. Child batches contain at most 32 cells under shared parent reservations.
Reservations are permanent conservative charges, not observed process starts.
Unknown durations, starts, token usage or prices remain unknown. Receipt quantities
with different units remain separate. Per-attempt durations can overlap and do not
establish inclusive wall time or complete costs.

`utility prepare` accepts optional `--inputs PREPARATION.json`. Its exact schema is
`PreparationInputs`: task preparations, exposure register, lock reference and source
inventory. Trusted adapter/capability profiles come from application code. Preparation
verifies sources and admissions without constructing adapters and grants zero starts.
The current CLI profiles cover the supplied hydrology and solar adapters. Engineering
and wind registry integration remains open. A reviewable preparation is not approval
to execute.

A selection manifest must cover every assigned cell. Selected snapshots must appear
in the child evidence and frozen candidate pool, with verified source bytes. Sealing
is permanent for that suite. Unresolved work blocks sealing. Explicit not_attempted
cells remain visible and provide no confirmation evidence.

The Python analysis interface reconstructs task-specific paired differences from
pinned public score receipts. It reports full assignment denominators, feasible
selection rates, conditional effects and uncertainty. Missing pairs remain
inconclusive. Complete evidence of failed required feasibility remains a failure.
No global score averages RMSE, energy and money. Efficiency remains inconclusive
without complete costs. Authored score fixtures are not confirmation results.

`AnalysisPlan` (`utility-analysis-v1`) preserves its original serialized identity
and reports repetition diagnostics. Those intervals alone cannot support a
scientific gain verdict. `DependentAnalysisPlan` (`utility-analysis-v2`) freezes
the `all_paired_lower_bounds` decision rule and a complete `DependencePlan`.
`PairedDependenceEvidence` binds each public dependence summary to the exact route
and comparator cells, score hashes and task policy. Prediction summaries must
match the frozen partition, RMSE and units. Scenario summaries preserve the
distinction between fixed cases and a declared independent sample. Confirmation
uses `BoundScenarioUncertaintySpec` (`utility-scenario-uncertainty-v2`) to bind
that policy to the complete task partition/forcing manifest. The older scenario
policy remains available for development diagnostics.

Use `bind_summary` with a trusted custodian's registered resampling result, then
archive the returned record as a public artifact. Pass the pinned references and
frozen dependence plan to `analyze_receipts` or `analyze_confirmation`. Readers
verify the artifacts and never rerun private resampling. This does not qualify
an untrusted scorer or provide a private execution boundary.

A scientific gain requires complete feasible pairs, a repetition lower bound
above the useful-effect threshold and a dependence lower bound above that
threshold for every pair. The family error allowance is split equally between
repetition and dependence intervals, then divided across contrasts, regimes and
assigned pairs as applicable. The frozen dependence confidence must cover that
allowance. Fixed scenario censuses use their exact finite-case gain and support
only a claim about those cases. Missing, insufficient or wide dependence evidence
leaves the gain claim inconclusive. Repetition and dependence intervals remain
separate in the report.

## Remaining work

The CLI exposes `run` and `resume` only for the explicit scripted development profile.
It exposes `confirm` through application-owned trusted scorer registrations.
The distributed CLI has no admitted private scorer. Exposed mixed-family and wind
development execution are available. Admitted independent-task execution, private scoring qualification,
custodian production of paired
dependence evidence, remaining qualified-profile integration and complete cost
joining remain unfinished. Linux, a second actual host, installed real-task execution
and the full independent four-family matrix remain unqualified. No positive utility,
efficiency, role-retention or general superiority claim follows from current tests.

Shared deterministic baseline receipts can now be allocated explicitly across
logical repetition cells in the offline analysis API. The reader counts one
physical receipt, verifies unchanged values/status, task/scenario identity and
frozen selected state, and retains every assigned pair. A reused cell with any
existing confirmation charge is rejected, including reserved or unresolved work. Exclusive cost shares sum to one. Adaptive-route reuse and cross-task reuse
reject. Frozen v2 suites now execute one confirmation source per declared group
and reconstruct follower references automatically. Policy v2 can also prepare a common selection reference through the exposed
scripted coordinators.
`analyze_confirmation` consumes committed public suite receipts after the selection
barrier and never invokes the scorer. Missing comparison scores stay inconclusive.

Prediction uncertainty now has a separate frozen segmented block-resampling API.
It binds timestamps, masks, segment IDs, block length and development/partition
identities. Resampling never bridges masked gaps or timestamp gaps. Short segments
remain insufficient rather than shrinking the block after scoring. Scenario
uncertainty distinguishes fixed design cases from an independent scenario sample.
Fixed cases receive a finite-case summary without a population interval. Joining
these custodian outputs to final utility verdicts remains unfinished.

Supplied-role ablations now have an application-owned `AblationBroker`. It uses
registered mechanical catalogue lookup, supplied configuration and coded-evidence
review while retaining the campaign's acceptance and budget transitions. The
omitted role has no host task or invocation. Mechanical actions have distinct
suite receipts. Current execution tests use scripted authored fixtures. Real-task
registration, live-host ablation qualification and the full route matrix remain
unfinished. Child campaign confirmation must stay disabled under the suite barrier.

Selections containing a model use schema `utility-selection-v2`. Each selected
cell pins a child-attested `SelectedState` with the model, exact parameter mapping
and successful evaluation. Candidate replacements also retain their admitted
candidate snapshot. Legacy schema v1 remains readable for manifests with no model
selection; it cannot authorize a selection without parameter evidence. Shared
baseline reuse requires identical selected model and parameter-state identities.
Private prediction envelopes also bind the selection-barrier identity, so an
implementation hash alone cannot stand for a calibrated configuration.

## Scripted development execution

`ScriptedExecutionPlan` binds a complete route plan, supplied CampaignSpec JSON
references, source inventory, lock and worker/batch limits. It is an execution
profile for exposed development inputs. It rejects live hosts, generated code,
private/independent data and child confirmation. It does not admit a real utility
task or establish scientific utility.

After constructing and reviewing that plan and its matching suite, use:

```sh
autoengineering utility run WORKDIR EXECUTION.json --source-root CAPTURED_SOURCE \
  --scripted-development --max-new-cells 1
autoengineering utility resume WORKDIR EXECUTION.json --source-root CAPTURED_SOURCE \
  --scripted-development
```

`run` pins the exact execution plan and refuses existing execution state. `resume`
requires the same pin. Source, lock, prompt, numerical-recipe or resource changes
require a new suite. Completed cells replay without more model/host starts.
For unfinished cells, the scripted coordinator reopens the original campaign and
worker journals and checks the paired campaign input and worker identity. It can
resume after a saved scientific response whose worker acknowledgement was
interrupted. Campaign recovery reads original stop receipts before any new work.
Pending worker calls, pending implementation preparation, unsettled physical
reservations, missing journals and changed inputs block execution. Parent
reservations and child clocks are retained; pause does not reset a budget.

When all cells finish, the result includes a `selection_proposal` artifact. Review
it and pass its saved path to `utility freeze` separately. Execution does not
seal selections or access confirmation labels automatically. The current command
profile supports supplied prediction campaigns. Engineering/wind orchestration,
live-host execution and recovery of pending host calls still require qualification.


## Comparative tables and export verification

`ReportSpec` (`utility-report-inputs-v1`) pins the suite, analysis artifact,
optional dependence policy/evidence and explicit shared-baseline allocations.
Artifact paths are relative to the suite directory. Analysis must match the
suite's frozen analysis digest. Comparative reports require a sealed complete
selection manifest and read only committed public scores. They perform no model
execution, resampling or provider calls.

```sh
autoengineering utility report WORKDIR --inputs REPORT_INPUTS.json --format markdown
autoengineering utility report WORKDIR --inputs REPORT_INPUTS.json \
  --export-directory NEW_REPORT_DIRECTORY
autoengineering utility verify WORKDIR --inputs REPORT_INPUTS.json \
  --export-directory NEW_REPORT_DIRECTORY
```

Exports contain `report.json`, `summary.md` and eight CSV tables: assigned cells,
paired effects, contrasts, contrast failure counts, physical costs, exclusive cost
allocations, role permissions and dependence intervals. Empty tables still have
headers. Unknown quantities are blank, and failed/missing pairs do not receive
invented objective values. The cells table preserves selection status and the
reason confirmation evidence is unavailable. Contrast failure counts describe
score evidence, so a missing score remains `missing_evidence` even when the
selection table explains why no model could be confirmed.

Physical costs list each receipt once. Sum `allocated_quantity` in the allocation
table to obtain exclusive cell shares. Its `quantity` column repeats the original
physical receipt for reference and must not be summed across allocations. Role
permission counts describe reserved calls and do not establish physical starts.
The current cost join remains incomplete, including confirmation, training,
solver and human work that lack qualified joined receipts.

The export directory must be new and contain no symlink ancestors. A manifest is
written last. `verify --inputs ... --export-directory ...` reconstructs every
exported byte from authoritative suite evidence, then checks both manifest and
file contents. Updating a table and its hash cannot make altered numbers pass.
The report pins the suite journal head. Verification uses the current head, so
later journal changes require a new export. Historical-prefix reconstruction is
not implemented. Without these options, existing report/verify commands retain
their accounting-only behavior.

The installed reader check is reproducible with
`scripts/utility_installed_report_check.py WHEEL --output NEW_CHECK.json`. It
extracts a locally built wheel outside the checkout and uses the invoking
Python's dependencies. Seven CLI operations reconstruct a synthetic unattempted
two-cell report with process launches and network connections blocked. This
qualifies offline packaging and table reconstruction only. It does not qualify
installed model execution, independent scientific evidence or the full G8 report
package. Constraint/residual, time-series and complete-cost views remain outstanding.


## Optional scientific figures

Add `--figures` to a comparative report export in an environment containing
Matplotlib. Rendering was exercised in the existing wind environment. Core
readers do not import or require Matplotlib.

```sh
pixi run -e wind autoengineering utility report WORKDIR --inputs REPORT_INPUTS.json \
  --export-directory NEW_FIGURE_DIRECTORY --figures
pixi run autoengineering utility verify WORKDIR --inputs REPORT_INPUTS.json \
  --export-directory NEW_FIGURE_DIRECTORY
pixi run -e wind autoengineering utility verify WORKDIR --inputs REPORT_INPUTS.json \
  --export-directory NEW_FIGURE_DIRECTORY --rerender-figures
```

The figure export includes the existing tables, `figure-data.json`, and SVG/PNG
figures. Each contrast has a paired-effect plot with raw valid-pair gains,
repetition mean/interval, useful-gain threshold and valid/assigned counts.
Dependence evidence produces a separate observation/scenario interval plot.
Intervals retain their frozen method and adjusted confidence labels. Fixed-case
censuses have no population interval. Assignment-count plots show every cell,
including failed, unattempted and unresolved evidence. Outcomes with different
units stay in separate figures.

Light backgrounds, earth tones and status hatching support print and grayscale
reading. The renderer pins its source hash, Matplotlib/Freetype versions, width
and resolution. It resets plotting defaults inside a local context. Rendering
starts no model, scorer or provider and reads no private arrays. Missing
Matplotlib stops before creating an export. Unknown total cost remains an explicit
blocked entry in figure-data.json, without a partial-cost efficiency plot.

Normal `verify` reconstructs table and figure numeric data from authoritative
suite evidence. It checks image bytes against the export manifest and reports
`image_rendering: not_repeated`. Image/hash agreement alone is only internal
consistency. `--rerender-figures` requires the optional rendering environment,
checks its profile and compares regenerated image bytes as well. A rendering
profile change requires a new export. Verification never claims a pixel
reconstruction when it was not performed.

Authored visual checks are saved under `examples/utility/figure-rehearsal-v2/`.
Both 8-inch and 5-inch layouts were inspected. They illustrate a missing pair and
separate scenario uncertainty, with no real scientific utility claim. The first
illustration had inconsistent status counts and is retained as invalidated under
figure-rehearsal-v1. These visual checks do not replace real-task residual,
time-series, scenario-physics or complete-cost plots.


## Declared human-effort accounting

`EffortPlan` freezes named scopes, phases, work kinds, allowed measurement methods,
exclusive cell allocations, an amortization horizon and a primary comparison basis.
Scopes must cover exactly all assigned cells. Common setup and one-time integration
are shown separately from route work and repeated operation. Logs classify setup,
review, repair, intervention, operation, integration or research activity.

`HumanTimeSource` is a public timer or self-reported source record with an actor
hash and ordered UTC epoch timestamps. `HumanTimeLog` binds its exact fields to an
artifact and a work scope. No free-form private notes belong in these sources.
The reader verifies original source fields and hashes, rejects duplicate evidence
and overlapping positive intervals for the same actor, and keeps concurrent work
by different people additive. These totals are person-seconds, not elapsed wall
time. The reader consumes records and does not measure work itself.

`EffortClosure` explicitly closes a scope or marks it incomplete. A closed scope
requires logs, including an explicit zero-duration log for zero effort. Empty,
missing or unknown logs cannot establish zero. Unknown totals remain null even
when some measured work is available. Shared work is recorded once and allocated
with the frozen fractions. First-use and amortized totals remain separate. The
amortization horizon cannot change during reporting. Timer and self-reported
quantities remain distinguishable, and a policy can forbid self-reported values.

`EffortAnalysisPlan` (`utility-analysis-v3`) adds the effort-policy digest and one
`EffortCriterion` for every contrast. Each criterion freezes a scientific
noninferiority margin in the task's outcome units and a minimum person-second
saving. The nominal error allowance is split across repetition, dependence and
effort intervals before the existing contrast/regime/pair adjustments. This new
identity prevents adding an effort rule retrospectively to v1/v2 analyses.

Use `EffortReportSpec` (`utility-report-inputs-v2`) with a pinned `EffortInputs`
artifact to join the public closures. Existing report and verify commands accept
it through the same `--inputs` option. Exports add human-effort cell, allocation
and paired-saving tables. Original physical seconds are repeated for reference
in the allocation table; sum allocated seconds, not the repeated source quantity.

A supported efficiency verdict here has basis `declared_logged_human_effort`.
It requires complete declared logs for every pair, scientific noninferiority on
both repetition and dependence bounds, required feasibility, and a saving interval
above the frozen useful margin. It does not establish computational or monetary
efficiency. Declared closure cannot independently prove that a person recorded all
work, so reports state that limit and keep complete physical-cost evidence false.
Role retention still requires its full frozen ablation and cost requirements.


## Installed development execution check

`scripts/utility_installed_model_check.py` prepares the existing small authored
fixture, installs a locally built wheel without dependency downloads in a new
temporary venv, and runs the CLI outside the checkout. Use an absent physical
output path outside the repository, such as `/private/tmp/utility-installed-check`.

```sh
pixi run python scripts/utility_installed_model_check.py PATH_TO_WHEEL \
  --output /private/tmp/utility-installed-check
```

The retained output includes prepared sources, parent/child journals, model job
commands, stop receipts, selected artifacts and CLI results. The check runs one
cell, resumes the second, verifies that completed resume adds no model work, then
separately freezes, reports, verifies and inspects status. It checks that imported
execution/model modules and scientific command interpreters belong to the installed
venv. The wheel now includes the existing authored campaign fixture module and
small input files needed by this path. The producer uses repository test helpers;
the installed execution itself uses the wheel and captured sources.

Current macOS evidence is under `examples/utility/verification-v1/`. It preserves
the original missing-package failure and the corrected installed result. Inherited
dependencies, an authored model and no confirmation/provider access limit this
check. It does not qualify a Linux runtime, a second host, private confirmation or
an installed four-family real-task comparison. The interim completion audit maps
those remaining requirements in `docs/reviews/part-5-completion-audit.md`.

## Supervised engineering scenarios

`SupervisedEngineeringExecutor` runs supplied scalar engineering scenarios in owned
processes. It preserves `EngineeringStudy` outcomes and required scientific checks.
It uses the existing batch reservations and optimization ledger. It does not turn
an engineering objective into a prediction score.

`EngineeringExecutionSpec` binds the study, trusted `module:function`, ordered
scalar forcing scenarios, source references, lock, timeout and output limit. Use a
separate owner-private captured source directory. Every file must be declared, and
symlinks are rejected. The inventory must include the current core Python sources
and the registration's module and parent packages. Preflight inspects registration
syntax without importing supplied parent packages. The persisted execution binding
also fixes the absolute source directory, interpreter, host environment identity
and installed package names/versions. Changing any of these blocks resume.

Each scenario reserves permission before launching the fixed worker. The process
supervisor bounds elapsed time and captured output, watches the parent, and retains
process identity and verified stop evidence. The reservation includes five seconds
beyond the scientific timeout for stopping and supervision. This trusted-code
profile provides no filesystem, network or memory sandbox and is not qualified for
generated code or private confirmation.

Worker preflight failures remain `infrastructure_failure`. Supplied-code failures
become `model_failure`, and expired processes remain `timeout`. Failed scenarios
retain missing outcomes. They do not acquire numeric penalties. Completed results
must match the original job, forcing, outcome names and required check semantics.
Solver diagnostics carry explicit units and nonnegative values, with integral
counts and Boolean flags. These counters are evidence, not complete cost accounting.

Default recovery reads only verified results from original processes. An original
reservation without a verifiable completed process remains charged and blocks
retry. `EngineeringStudy(..., resume_scenarios=True)` explicitly allows continuing
never-reserved scenarios for the original pending action. This may launch work
during construction while the optimization controller reconciles that action.
It never relaunches an already reserved scenario. Preparing or inspecting a study
must not enable this option.

The exposed circuit rehearsal exercises two Sobol points over three ground-voltage
scenarios while preserving the coupled solve and native derivative counters:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_supervised_engineering \
  --output outputs/utility-engineering-supervised
```

Use an absent output directory. Saved rehearsals under
`examples/utility/development/engineering-supervised-v1` and `-v2` retain their own
captured source bytes. The v2 record has six completed processes and no additional
reservation on completed resume. Its utility verdict is `not_attempted`.
Engineering campaign/route registration, independent scenarios and confirmation
remain incomplete. These development scenarios were already exposed.

## Engineering scientific tools and selection

`EngineeringCampaign` adds durable scientific operations above the supervised
executor. `EngineeringCampaignSpec` freezes one supplied scalar model snapshot,
its baseline configuration, named fixed designs, numerical study and request cap.
Every configuration must belong to the frozen search space. Model sources must
match the execution inventory. The child case must reserve the full baseline,
fixed-design and calibration ceiling before the controller is created.

The existing campaign `EventStore` owns request acknowledgements, scientific result
artifacts, review and selection state. Batch receipts still own physical work, and
`EngineeringStudy` still owns numerical actions and observations. A case binds one
campaign identity and absolute location. A second controller cannot change its
specification, increase its request cap or create another campaign in that case.

The controller accepts existing version 1 `Request` records with these payloads:

| Operation | Payload | Behavior |
| --- | --- | --- |
| `state` | Empty | Return the state and evaluation count without scientific work. |
| `evaluate` | `candidate_id: baseline`, `mode: fixed` | Evaluate the registered baseline first. |
| `evaluate` | A declared design ID, `mode: fixed` | Evaluate that exact registered configuration. |
| `evaluate` | `candidate_id: calibration`, `mode: calibrated` | Run the frozen numerical study, preserving every recorded result. |
| `review` | Empty | Apply engineering gain, secondary-outcome and scenario-check rules to committed evidence. |
| `freeze` | Empty | Seal the current reviewed selection, including its exact model and parameters. |
| `cancel` | Empty | Stop subsequent campaign mutations when no scientific request is unresolved. |

Caller-supplied configuration overrides, import paths and confirmation operations
are rejected. No operation creates observation vectors for engineering scores.
Repeated registered designs reuse their original physical evidence. A new request
still consumes request allowance. Exact committed request replay returns its
original response. Reusing that logical identity for different content is refused.

Scientific request intent precedes dispatch. After interruption, a different
mutation cannot pass an unresolved request. Default retry reads original completed
processes and completed calibration only. `handle(request, resume_scenarios=True)`
explicitly continues never-reserved work under that original request. Uncertain
starts retain their charges. A crash before durable intent can reuse its empty
directory because no physical dispatch was permitted at that boundary.

Replay checks the original model/configuration, process job and execution binding,
scenario forcing, result bytes, status and elapsed time against batch receipts.
Review reconstructs its decision from those records. Selection uses the existing
`SelectedState` schema. Failed baselines and alternatives remain failures, and a
review can freeze an explicit `no_eligible_model` outcome without a selected state.

Opening `EngineeringCampaign(root, batch)` without an executor supports offline
state reconstruction and committed-response replay. It cannot start science or
make a new review, freeze or cancellation mutation. The circuit rehearsal exercises
the complete scientific-tool path:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_campaign \
  --output outputs/utility-engineering-campaign
```

Use an absent output directory. Final development evidence under
`examples/utility/development/engineering-campaign-v2` records four evaluated
designs, twelve stopped scenario processes, review, selection freeze and offline
reconstruction. This is an exposed modeled circuit question. Its verdict remains
`not_attempted` for comparative utility.

This controller connects to the engineering brokers and versioned execution plan
described below. Prediction and engineering keep separate outcome contracts.
Independent scenarios and private confirmation remain open.

## Native engineering driver

`EngineeringNativeCampaignSpec` uses schema `utility-engineering-campaign-v2` to add
a frozen `NativeDriverSpec`. Version 1 campaign identities retain their existing
fields and meaning. The version 2 controller accepts `evaluate` with
`candidate_id: native` and `mode: native` after the baseline. Its `execution_status`
describes the native job, not scientific acceptance of its proposed design.

The native specification binds the supplied registration, scenario execution
profile, iteration and inner model-call ceilings, timeout and output bound. Source
preflight checks the native registration without importing supplied parent
packages. The fixed worker rechecks its source/environment binding before model
import. Owned process supervision bounds elapsed time and output. An original
reservation without verified completion remains charged and cannot launch again.
Recovery can acknowledge an original saved process without repeating the driver.

One batch scientific reservation covers the outer driver process. It does not
represent one inner model solve. The inner ceiling is separately frozen and must
be enforced by the qualified supplied implementation. The circuit registration
passes that ceiling to the existing native SLSQP recipe, which refuses before an
additional model call would exceed it. A test counts actual model entries under a
one-call optimization allowance. These guarantees do not qualify arbitrary new
native implementations or provide a filesystem, network or memory sandbox.

The circuit recipe preserves the coupled solve, native derivatives and physical
scenarios. Its returned records identify driver calls and independent scenario
calls separately. Driver diagnostics are snapshots of one shared problem and must
not be summed as independent work. `utility-native-result-v2` also records
the final driver state, including derivatives performed after the last model solve.
Legacy result v1 remains readable, with absent final counters unknown.

`utility-native-result-v3` adds independent support solves outside the scored
scenario population and an `optimizer_target_met` flag. Support solves count
toward the same frozen inner-call ceiling and have separate cost resources.
The flag describes the optimizer's target, including any declared numerical
buffer. It does not replace the authoritative physical acceptance rules.
Existing v1/v2 records retain their original schemas and resource exports.

The supplied `examples.utility.engineering_load_envelope_native:execute`
registration applies the [declared engineering envelope recipe](reviews/part-5-engineering-envelope-registration.md).
It uses the public controlling corner, a 0.62001 V optimizer target and the
original 0.62 V physical rule. It freshly checks the corner and supplied study
scenarios. A controller must still score the returned current through its
authoritative evaluator before accepting a candidate.

The [actual public controller check](reviews/part-5-engineering-envelope-supervision.md)
now exercises that registration through baseline, supervised native selection,
fresh candidate scoring and selection freeze. Its 49 process receipts cover 83
root model calls. Relocated installed replay verifies those original receipts
without importing a model. This remains exposed development qualification.

The example helper `engineering_native_accounting.account_circuit_pass` describes
per-pass circuit work using exact cumulative counter deltas. A native pre/post
pass may leave the circuit inactive and retain an earlier diagnostic snapshot.
The helper then records no fresh circuit iterations and never assesses design
eligibility. Counter resets refuse. This does not migrate legacy core records.
The [revised public native profile](reviews/part-5-engineering-conventional-profile.md)
preserves all invocation charges, separately counts work between nonlinear
passes, and keeps a failed exact optimizer-buffer check apart from the original
physical acceptance requirement.

`native_cost_records` exports outer process starts, inner model calls, final driver
derivative calls and independent scenario derivative calls as separate resources.
Missing inner results remain unknown on timeout or failure. An unsuccessful driver
can retain known call records without producing an eligible design. These receipts
do not establish complete physical, monetary or human costs.

Successful native output supplies a configuration, not an accepted score. The
controller evaluates it afresh through every declared scenario and applies the
same required checks and engineering decision rules. Its full case reserve covers
the outer driver and these fresh scenario jobs in addition to the other campaign
operations. Native failure commits a visible report without an eligible candidate,
so review can retain a valid baseline. Offline replay verifies original native
job/binding and batch observation bytes without importing the scientific model.

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_native \
  --output outputs/utility-engineering-native
```

Use an absent output directory. The final exposed rehearsal in
`development/engineering-native-v2` records sixteen stopped outer processes and
twelve inner native model calls. The native process succeeded, but its fresh
low-ground voltage was `0.6199999999999917 V`, below the frozen `0.62 V` requirement.
The candidate remained ineligible and the supplied `0.03 A` design was selected.
The threshold was preserved. The earlier -v1 rehearsal retains the result profile
without the final driver snapshot. Neither rehearsal is independent confirmation
or a route comparison, and comparative utility remains `not_attempted`.

This completes the supplied native scientific tool for the exposed circuit.
The engineering plan connects it to conventional and agent brokers, shared suite
grants and the public CLI. Complete parent cost joins remain open. Engineering
readers currently retain the original absolute campaign/job locations. Portable
archive relocation has not been qualified for this profile.

## Engineering route brokers

`EngineeringBroker` reuses the role scheduler, worker grants, durable request
actions and deadline forwarding. It accepts the engineering controller's frozen
supplied catalogue. It does not stage generated code or allow workers to override
scientific configurations. `run_engineering_recipe` supplies baseline and
conventional execution without host calls. The conventional recipe requires the
native-enabled campaign version and runs fixed designs, numerical calibration and
the registered native driver before applying the same review and freeze rules.

Four-role execution uses separate orchestrator, investigator, implementer and
reviewer tasks. Single-agent execution creates only `single_agent` tasks and
handoffs. Its history contains at most four normalized prior handoffs within 8 KiB.
It does not create four synthetic personas. Four-role summaries do not include raw
peer transcripts. Both receive the same parameter domain, scalar scenarios,
declared model-port/outcome units, numerical and native limits, and public
evaluation evidence. Role workflow state is distinct from scientific state.

The broker accepts only exact registered configurations or named numerical/native
recipes from implementation advice. Each calibration result gets its own review.
A failed native proposal remains an explicitly typed failed attempt, without an
invented objective or passed scenario check. A valid advisory stop remains a
completed handoff and stops the route. It does not become malformed output that
automatically spends repair calls. Findings can cite only the current check names.
Scientific checks continue to determine eligibility regardless of advisory review.

Role removals require an assigned `RoleBoundHost` and frozen `RoutePlan`. The
existing mechanical policies supply the omitted handoff and write parent receipts.
No host task is dispatched for the omitted role, and its allowance is not moved
to another role. Paired execution changes only the frozen cell seed through
`paired_engineering_spec`. Numerical-recipe identity records that seed rule while
binding the actual policy, options, limits and scientific choices.

Committed requests replay their original envelopes. Default broker recovery
reconciles verified completed work. `advance(resume_scenarios=True)` explicitly
continues never-reserved scenarios under an original pending request. Unknown
starts stay charged. Cancellation uses an independent inbox, which can be written
while a scientific writer is active. Scenario/native supervision observes that
revocation and retains verified process-stop evidence. Worker deadlines forward
both worker and scientific cancellation. Cancellation cannot authorize more work
or erase original physical records.

The bounded seven-route development rehearsal uses existing parent/child stores:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_routes \
  --output outputs/utility-engineering-routes
```

Use an absent output directory. It includes the four primary routes and three
role removals over one exposed circuit question. Hosts return deterministic
scripted advice. This does not test LLM quality, role utility or independent
scientific improvement. The script finishes child cases but does not seal the
suite-wide selection barrier or spend its confirmation reserve.

The broker and recipe APIs also support the declarative engineering profile below.
No new live-host profile is qualified by the scripted rehearsal. Wind and
independent-task admission remain separate requirements.

## Engineering execution plans and public run/resume

`ScriptedEngineeringPlan` (`utility-scripted-engineering-v1`) embeds a native-enabled
campaign for each assigned task, the route matrix, shared source/lock inventory,
worker/batch limits and runtime identity. It admits exposed scalar engineering
development only. It does not combine prediction and engineering tasks into a
mixed-family plan or admit independent confirmation.

Prepare fresh campaigns with `case_scoped_campaign` before constructing the plan.
This selects `utility-engineering-execution-v2`, whose physical permission names
include the child case. Paired cases can share a batch without sharing a permission
or native job. Execution v1 retains its original identities and remains readable.
Existing runs must not be converted by changing their records.

`engineering_runtime_identity()` binds the interpreter, host environment and
installed package names/versions. Runtime drift is refused before child allocation.
The coordinator checks source closure without importing supplied registrations,
task/outcome/scenario identity, numerical recipes, host permissions, prompt
templates and frozen group allowances. A source-only research grant and no training
grant are required. These checks are not a sandbox or independent task admission.

`ScriptedEngineeringCoordinator` uses existing bounded child groups, permanent
parent reservations, worker journals and scientific controllers. Each case binds
its exact paired input before execution. Finished cases replay without model or
host calls. Pending physical starts still need original stop evidence. Missing
controller/worker journals cannot be replaced after scientific work.

The public commands recognize engineering and prediction plans by schema:

```sh
pixi run -e interoperability autoengineering utility run SUITE ENGINEERING_PLAN.json \
  --source-root CAPTURED_SOURCE --scripted-development --max-new-cells 1
pixi run -e interoperability autoengineering utility resume SUITE ENGINEERING_PLAN.json \
  --source-root CAPTURED_SOURCE --scripted-development
```

Use the same plan, runtime and source root on resume. To continue never-reserved
scenarios under an original pending engineering request, explicitly add
`--continue-pending-scenarios` to `resume`. Default recovery only reconciles original
completed work within that request. This flag does not permit replaying an
uncertain start and is rejected for prediction plans.

Completion archives selected model sources, exact parameter/evaluation state and
matching child evidence into the suite. The CLI returns a selection proposal after
every assigned cell finishes. It does not freeze the proposal or invoke confirmation.
Review and seal the manifest separately:

```sh
pixi run autoengineering utility freeze SUITE SELECTION_MANIFEST.json
pixi run autoengineering utility verify SUITE
```

The full public-command rehearsal prepares an exposed circuit plan, runs one cell,
resumes six, checks completed resume adds no cells, then separately freezes,
verifies and inspects status:

```sh
pixi run -e interoperability python -m examples.utility.rehearse_engineering_plan \
  --output outputs/utility-engineering-plan
```

Use an absent output directory. Outer CLI processes and scientific jobs have owned
supervision. No provider, confirmation or independent data access is part of this
producer. Installed-wheel execution and archive relocation remain unqualified for
the engineering profile. Wind, mixed-family execution and complete cost/effort
joins remain open.

## Mixed prediction and engineering plans

`ScriptedMixedPlan` (`utility-scripted-mixed-v1`) combines embedded
`TaskPredictionCampaign` and `TaskEngineeringCampaign` records. At least one of
each is required. The plan uses one runtime identity, complete source inventory,
lock, route matrix and parent ledger. Every engineering campaign must use execution
v2 and that exact shared inventory and lock. Prediction locks must have the same
path, digest and byte count. Embedding campaigns avoids storing a specification
inside its own source closure.

`ScriptedMixedCoordinator` dispatches prediction tasks to the existing campaign
executor and engineering tasks to the existing supervised engineering executor.
Prediction tasks currently admit the hydrology and solar families with the
supported supplied adapters. Wind and hybrid execution require separate work.
All data must already be exposed, and campaign confirmation must be disabled.
This development profile does not admit an independent task or private scoring.

Before allocation, the coordinator checks all task outcomes, partitions, candidate
pools, sources, numerical recipes, hardware/corpus grants, host permissions and
limits. Engineering input checks enforce an exact source tree without importing
supplied registrations. Both executors retain their scientific outcome rules.
The parent does not combine prediction errors and engineering objectives into a
single scientific score.

The public `utility run` and `utility resume` commands select this profile from the
plan schema and pin its exact record. Use the same arguments as for engineering
plans. The scenario continuation flag applies to original pending engineering
requests. Prediction recovery keeps its existing behavior. Completed resume adds
no work. One selection proposal covers all assigned tasks, and a separate
`utility freeze` seals the shared barrier after all cells finish.

Mixed execution tests use an authored scalar engineering fixture and a linear
prediction fixture labelled as hydrology for contract testing. They exercise both
existing agent brokers, CLI resume, exact state export, shared freeze and recovery
after original scientific responses. They do not qualify a real mixed task matrix,
scientific utility, independent confirmation, a live host or another platform.

Large selected model and parameter records use
`utility-selected-artifact-binding-v1` receipts in selection schema v2. Each small
child receipt binds the artifact kind and exact suite artifact reference, including
its digest and byte count. Verification reads and hashes the full suite payload,
checks the selected model/configuration/evaluation and verifies model sources.
The writer also checks that its payload matches the bound reference. Missing,
changed or mismatched bindings prevent sealing.

Records at most 64 KiB retain the earlier complete-document child receipts. Larger
JSON records remain subject to the artifact reader's 64 MiB bound. The child
receipt limit remains 64 KiB. This permits long time axes and source inventories
without increasing ledger receipt limits or discarding exact selected state.

The exposed three-family producer is
`python -m examples.utility.rehearse_mixed --output NEW_DIRECTORY --solar-cache EXISTING_CACHE`
in the interoperability environment. It prepares Leaf River and solar prediction
campaigns alongside the circuit campaign. All three share the captured runtime,
lock, source inventory and parent suite. Seven supplied routes for each task form
21 cells. `--prepare-only` writes the proposal with no allocation or scientific
execution. The full producer exercises public run/resume, completed resume, a
separate selection freeze and offline verify/status. It requires already exposed
cache bytes and does not acquire confirmation data.

The wind examples now provide fixed-hardware scalar coordinates, bounded native
proposal records and a supervised direct/wrapped scenario callback. The numerical
parameter rectangle is exact. The existing physical geometry tolerance does not
expand it. A native layout outside that parameter domain retains its trace but
produces no admissible configuration. Native success alone never establishes
eligibility. Wake and gradient callback entries remain separate from inner model
solves and CPU work.

The wind scenario profile permits four turbines and one bundled distribution.
Its direction-step field is numerical configuration, not weather forcing. The
registered outcome is modeled annual energy in GWh, with mandatory finite,
spacing, nonnegative power, rating and boundary checks. New preparations use the
v3 preflight described below. Public independent wind task admission remains open.

### Wind native process development

`examples.utility.wind_process` adds separate wind job, result and report records
on the existing native process supervisor. The circuit schema and worker remain
the default. A fixed core bootstrap verifies the source closure before loading the
supplied wind entrypoint. The profile preserves four V80 turbines, the exact scalar
layout domain and the bundled distribution. It freezes separate wake and gradient
callback caps, optimizer iterations, process time and output size.

`rehearse_wind_native` reserves the native driver process, then separately reserves
a fresh scenario evaluation for an admissible proposal. Failed, exhausted,
unresolved or out-of-domain proposals do not receive a configuration. Returned
callback traces retain their actual statuses. Missing traces leave callback work
unknown. Counts of callback entries do not establish inner wake solves or compute
time. Reports and original process recovery retain the original charges.

The saved development probe completed two processes with verified stops and added
zero reservations on replay. The native driver converged after two wake callbacks
and one gradient callback. Fresh modeled energy matched the prior baseline at
37.06343379120568 GWh with all mandatory checks passing. Its guarded base reader
verified original bindings, process bytes, the fresh configuration and 188 archived
sources without scientific imports, dispatch or captured-source reads after archive.
No native gain, independent weather result or utility gain follows from this probe.

The shared callback campaign and public wind route builders below provide the
versioned wind result contract. Installed execution is qualified only for the
recorded source snapshots. Independent task admission and the remaining full-suite
gates stay open.

### Shared callback campaigns and wind routes

Campaign v3 (`utility-engineering-campaign-v3`) accepts the separate
`utility-callback-driver-v1` native profile. Existing v1/v2 campaigns keep their
original circuit contracts. Callback jobs bind canonical supplied options, callback
kinds and ceilings, source bytes, scenarios and process limits. Records retain
final parameters, feasible unscored proposals and callback input/output/status
traces. Unresolved work cannot produce a proposal configuration. Missing returned
traces remain unknown work.

The supplied implementation must enforce callback caps before invoking its model.
The wind adapter uses the existing bounded native driver for that purpose. The
controller also rejects inconsistent kinds, ceilings, indices, job identities and
out-of-domain proposals. Arbitrary trusted code is not automatically instrumented.
Callback entries are not coupled-model solves, solver residuals or compute time.
Fresh scenario evaluations and mandatory checks still determine eligibility.

`examples.utility.rehearse_wind_plan` prepares the seven shared-pool wind routes:
baseline, conventional, single agent, four roles and the three role removals. It
uses the public utility run/resume/freeze/verify/status commands. This is scripted
local development on the bundled distribution. It does not admit independent
weather or establish comparative utility. Use an absent output directory:

```sh
pixi run -e wind python -m examples.utility.rehearse_wind_plan \
  --output outputs/utility-wind-plan
```

The first real wind suite finished all seven cells, added no cells on completed
resume, separately sealed selections and passed public verify/status. Guarded
archive reconstruction is pending at this checkpoint. The prior three-family
rehearsal and this wind suite do not yet constitute one four-family run. The wind
environment lacks pvlib/Optuna, and interoperability lacks PyWake/TOPFARM. A common
runtime, installed scientific execution and the remaining independent-task,
privacy, platform/host and full accounting gates remain open.

Engineering archive readers can use `EngineeringCampaign(..., inspect_only=True)`.
This explicitly read only mode permits a relocated archive and preserves original
job/binding identity strings. It reads physical evidence from local confined paths,
rejects changed jobs, and refuses executors, request handling and cancellation.
Default live opening still enforces the original campaign path. It does not reopen
selection, obtain new allowances or authorize physical work.

The seven-cell wind suite now passes guarded reconstruction from an installed wheel
and copied archive outside the checkout. The reader denies the original checkout,
scientific imports, processes and network access. It verifies all seven selected
states, 25 science and 53 host observations with verified stops, and 193 archived
source files. The cost join remains partial. This qualifies saved wind evidence
reconstruction, not independent utility or installed scientific execution.

### Common four-family runtime

The optional Pixi `utility` environment supplies all four development families:

```sh
pixi install -e utility
pixi run -e utility python -m examples.utility.rehearse_mixed --include-wind \
  --output outputs/utility-four-family \
  --solar-cache /path/to/existing/verified/solar/cache
```

The solar cache must already contain the verified exposed OEDI development data.
Preparation does not fetch data. The output directory must be absent. Without
`--include-wind`, the three-family preparation remains available. The package also
provides a `utility` extra for these dependencies and a separate `wind` extra.

TOPFARM 2.6.2 requires OpenMDAO 3.39.*, so the common profile explicitly pins 3.39.0.
The existing interoperability environment and extra retain their 3.41.0 pin. Do not
combine the interoperability and wind extras. The circuit implementation label
records its actual OpenMDAO version. The common runtime passed circuit parity,
derivative and native-limit checks, wind checks and guarded four-family preparation.
Existing environment lock entries remained unchanged. Linux resolution is recorded
but actual Linux execution remains unverified.

The four-family preparer copies and verifies each supplied source/data reference,
rejects conflicting bytes, and binds both circuit and wind campaigns to the common
source/lock inventory. It prepares 28 cells under one parent and validates the full
proposal before allocation. The real common rehearsal is running at this checkpoint.
It is scripted development on exposed data, not independent utility evidence.

A separate local wheel has now executed one native wind process and one fresh
scenario outside the checkout from an exported bound input bundle. Both stops and
completed recovery verified. A fresh installed reader added no reservations,
observations or events. Its Python audit policy denies checkout opens and network
sockets, with policy bytes bound as an execution input. It is not the private scorer's
required OS boundary. Installed preparation from scratch and installed scientific
execution of every family remain unqualified.

### Preflight geometry in new wind runs

Engineering execution v3 binds declarative minimum-distance constraints to the
execution identity. New wind preparations use this profile for all six pairs of
four turbines. The bound is the existing 320 m spacing requirement with its
0.001 m physical tolerance. Parameter bounds remain exact.

An in-domain layout that violates spacing receives a durable
`scientific_infeasible` result before any scenario reservation or model process.
Its outcome values are unavailable. The receipt records the action, execution,
case, runtime binding, distances and violated constraints. It does not invent
model outputs or a stopped process. Recovery requires the original receipt and
refuses conflicting physical charges. Cancellation or uncertain work prevents a
new rejection. Zero physical cost still consumes one evaluation of the numerical
study's frozen evaluation limit. CPU, verification and human effort are separate
and are not established as zero.

Existing execution v1/v2 records retain their exact serialization and behavior.
The earlier four-family rehearsal remains evidence of its original execution
profile. It has not been rerun or relabelled as v3 evidence. Campaigns, numerical
studies and callback route preparation accept v3. The callback driver itself
still owns and accounts for its native process before fresh scenario validation.
This geometry check does not instrument arbitrary supplied code or admit a task.

A bounded development probe is available:

```sh
pixi run -e utility python -m examples.utility.rehearse_wind_preflight \
  --output outputs/utility-wind-preflight
```

Use an absent output directory. The saved `development/wind-preflight-v1` probe
rejected an overlapping layout with zero starts, then ran one feasible baseline
with a verified stop. Completed recovery added zero reservations. The offline
reader verified rejection and stop accounting with scientific imports, dispatch
and captured-input reads denied. It did not independently replay the feasible
output. Independent weather, private scoring, platform/host qualification and
complete cost/effort evidence remain open.

The separate v3 native/fresh probe completed two stopped processes and added no
work on recovery. A fresh local wheel also read the rejection outside the checkout
with optional scientific packages absent and original-checkout Python opens and
sockets denied. It reused cached base dependencies without editable activation.
That installed-reader check does not establish a minimal dependency environment
or private-data isolation.

### Saved development diagnostics

`scripts/utility_development_diagnostics.py` exports all 28 selected development
cells from pinned evidence. It verifies comparison arrays and selected scenario
records without importing models or dispatching processes. Exported RMSE and bias
must reproduce the saved prediction metrics. It uses the prior qualified reader
and artifact inventory, rather than claiming a new full ledger reconstruction.

`scripts/render_utility_development_diagnostics.py` renders prediction/residual and
engineering scenario figures from those tables. CSV files retain every route.
Exact overlapping curves or layouts are grouped visibly, with membership in the
rendering sidecar. Missing scored support stays absent and task units stay separate.

The checked package is `development/diagnostics-four-family-v4` under
`examples/utility`. It includes code-linked input hashes, CSV, PNG, SVG and captions.
The figures were inspected at 11 and 8 inches. A fresh installed reader outside the
checkout reconstructed all tables and their summary byte for byte from 94 copied
pins, with optional scientific packages absent and original access/network denied.
This advances development reporting. It supplies no independent confirmation,
complete cost comparison, uncertainty estimate or measured agent-role benefit.

### Second-host transport foundation

The application-owned Claude transport primitive is under
`autoengineering.agents.hosts.claude`. It pins executable/version/helper code,
uses fixed bare-mode options, supervises owned processes and recovers only an
original completed job. It never accepts a plain-text fallback as a structured
handoff. Failed results retain bounded raw bytes and available reported metadata.
API credentials cannot enter the supervisor's environment records.

Normalized token totals use the per-model breakdown. The SDK's top-level counters
remain separate diagnostics because they can omit work. Missing categories and
crash zeroes leave normalized totals unknown. `estimated_cost_usd` is the SDK's
client estimate. `billed_cost_usd` remains unknown. Neither the SDK estimate nor
its native budget flag establishes a hard ceiling on actual billing. See the
[official cost semantics](https://code.claude.com/docs/en/agent-sdk/cost-tracking).

This is a transport foundation tested with authored executables, not an admitted
second scheduler host. Host selection, capabilities, qualified boundary/profile,
factory/scheduler/cost integration and actual live conformance remain separate
required work. Production admission still requires a source-compatible qualified
Codex profile. Older pins retain their original source scope. No Claude inference or real credentials were used here.

The later macOS boundary increment adds an actual native helper and structured
roundtrip against an authored loopback peer. Its fixed settings support only an
integer local port and isolated temporary files. The source-compatible policy
passed 14 syscall controls. Failed attempts and offline reconstruction commands are
in the [native evidence guide](../examples/utility/verification-claude-loopback-v1/README.md).
The strict parser requires an explicitly completed terminal result to accept
StructuredOutput's tool_use stop. Plain text remains unsupported.

These are synthetic local probes, not real model calls or provider-cost evidence.
A production broker, host admission/records and scheduler/factory/cost integration
remain unfinished. Resource/lifecycle/privacy, real authentication, actual role
conformance and Linux qualification remain open. Older qualification pins cannot
be reused under changed source. No production admission gate was relaxed.

The [durable Anthropic exchange](../examples/utility/verification-anthropic-exchange-v1/README.md)
now supplies single-attempt request reconstruction, complete-response validation,
local capability checks and saved-byte recovery. It preserves raw reported usage
for rejected handoffs and keeps broker unknowns separate from SDK zero-fill.
Its actual native probes use an authored callback. A real upstream and admitted
production host remain unfinished.

The later [API upstream increment](../examples/utility/verification-anthropic-upstream-v1/README.md)
adds an explicit private API lease and a supervised single-send worker. It pins
the request, API version, host, route and transport source. It preserves uncertain
send/stop states and verifies original saved responses without reopening a lease.
All 299 transport checks and 58 installed checks passed using authored fixtures.
No real authentication or provider call occurred. The API implementation remains
provisional pending authentication preference and full boundary qualification.
Host records, scheduler/factory/cost integration and actual authorized conformance
remain unfinished. No production admission gate was relaxed.

The [owned Claude composition](../examples/utility/verification-claude-composition-v1/README.md)
now joins the native process, durable exchange, endpoint stops and broker usage in
one transport result. Prelaunch job bindings and saved recovery preserve original
evidence. Its actual native roundtrip uses authored JSON, with no provider.
Production host admission, full qualification and scheduler/factory/cost joins
remain open.


The [Claude host/profile checkpoint](../examples/utility/verification-claude-host-v1/README.md)
adds versioned selection, capability/configuration bindings, serial CLI dispatch,
recovery and batch accounting. Installed authored checks cover all four roles,
unchanged resume and permanent charges. Actual qualification and model conformance
remain unestablished. The candidate has explicit platform, authentication, billing,
remote-stop and resource-cap limitations. Full cost/effort joins and independent
Part 5 task/scorer/protocol/platform requirements remain open.


## Supplied wind resource profile

`examples.utility.wind_resource.WindResource` accepts a bounded joint table of
wind direction/speed probability masses. Directions cover a uniform full circle,
speeds are increasing m/s, and nonnegative mass must sum to one. It supports at
most 72 direction bins and 64 speeds, with a fixed 8760-hour annualization. It
does not normalize or regrid input probabilities. NOJ and V80 remain fixed.
Speeds enter as model reference WS without shear/height or air-density adjustment.
A real source still needs metadata, support, quality and exposure admission.

The original bundled-distribution profile remains v1. Native specification/driver
v2 bind the resource digest and registered `wind_resource_scenario` evaluator.
The same verified resource drives native objective callbacks and a separately
reserved fresh evaluation. The layout remains an unscored proposal until that
fresh check passes. Source changes, malformed inputs and changed resource bytes
cannot acquire replacement allowances during recovery. Required geometry, rating,
finite-output and nonnegative-power checks remain in force.

A bundled synthetic example works with the wind environment:

```sh
pixi run -e wind python -m examples.utility.wind_resource --output outputs/wind-resource-demo
```

The output directory must be absent. This performs one synthetic model evaluation
and exports the resource, prediction NPZ and JSON summary. It is not optimization,
independent confirmation or a private scorer. Source/base checks, actual native/
fresh process tests, installed execution and an offline arithmetic reader are in
[resource evidence](../examples/utility/verification-wind-resource-v1/README.md).

This public/development profile includes its resource in the source bundle. Do not
put private confirmation weather there. Protected independent resource scoring,
source rights/custody and the final task/protocol remain unadmitted. The wind
dossier stays blocked_draft. No independent-weather or comparative utility result
is inferred from the synthetic tables.


PrivateRMSEScorer v2 construction uses custodian-supplied artifact metadata and
opens no labels. Scoring validates public predictions before a durable private
access intent and label read. Use ConfirmationService so the suite reservation
and access event precede scoring. Uncertain attempts remain charged. Recovery
checks original worker/process records without reopening labels or rescoring.
The new source-bound identity does not resume private v1 attempts. This accounting
repair supplies no OS qualification: the macOS data-memory boundary remains
unqualified, and real private scoring is refused before access. Positive tests
use synthetic labels and an explicit authored boundary stub.


## Confirmation cost projection

New public confirmation receipts optionally carry a versioned callback measurement
bound to grant, scorer and exact public score. The service measures elapsed time
only around the trusted scoring callback. That duration includes private I/O and
nested workers inside the callback. It excludes registration, grant validation and
reservation work, and it is neither CPU time nor a runtime enforcement mechanism.
Do not add it to overlapping worker durations or describe it as total phase cost.

Accounting now emits confirmation-category reservations, committed access intents
and committed scores. A measured callback adds its completion count and duration.
Worker starts remain unknown without a public execution receipt. Legacy receipts retain their exact serialized
shape and unknown callback time. Uncommitted scores and interrupted callbacks also
retain unknown time. Public reports/CSV exports do not open private data, invoke
the scorer, sample a new duration or fill unknown quantities with zero.

An outstanding confirmation reservation is reported as reconciliation_required,
not not_attempted. Complete-cost evidence remains false: solver/training work,
preparation, CPU/GPU/RSS, provider and human-effort closure still need their own
physical evidence. This is accounting software, not a real confirmation run.


## Pinned engineering work in common reports

`CostEvidenceSpec` (`utility-cost-inputs-v1`) adds the generated-load callback's
public work receipts to common accounting. Each entry names the original grant,
source/scorer registration and a caller-pinned work `ArtifactRef`, or null when
that proof is unavailable. Inputs must cover every charged callback using the
load model/solver resources. Duplicate cells and omitted charged callbacks fail.
No factory, source generator or optional model package is imported by this reader.

```sh
autoengineering utility report WORKDIR --cost-inputs COST_INPUTS.json
autoengineering utility report WORKDIR --cost-inputs COST_INPUTS.json --format markdown
autoengineering utility verify WORKDIR --cost-inputs COST_INPUTS.json
```

Explicit cost inputs produce `utility-accounting-v2` with their digest and the
suite journal head. Without that option, accounting retains its original v1
output. A missing supplied artifact is an integrity error. A null artifact keeps
actual work unknown. A completed score alone does not prove native work counts.

For comparative exports, use `CostReportSpec` (`utility-report-inputs-v3`) with a
pinned `costs` JSON artifact containing `CostEvidenceSpec`. The existing `--inputs`
report/export/verify commands then reconstruct physical-cost and allocation tables
from those proofs. An optional `effort` artifact retains the existing effort
analysis contract. Report-input versions 1 and 2 keep their exact serialization.
Do not combine the standalone `--cost-inputs` option with comparative `--inputs`.

### Annual wind cost inputs

`DomainCostEvidenceSpec` (`utility-cost-inputs-v2`) extends the same path with
`wind_callbacks`. It retains `load_callbacks`, including native and container load
registrations. Use empty tuples for unused domains. `CostEvidenceSpec.from_json`
dispatches both versions. Version 1 retains its serialization for load-only
suites. A suite with charged annual wind resources requires version 2 and complete
wind callback coverage. Missing or duplicate cells fail rather than omitting work.

Each `WindCostInput` supplies the original `ConfirmationGrant`, a
`WindCostRegistration`, and a pinned work `ArtifactRef` or null. Registration
binds the source artifact, callback code, kernel policy, expected model and
geometry identities. The reader verifies the sealed source claim, exact frozen
model and layout, original allocation/access, annual work and source-read records.
It imports no example or optional model code and opens no weather payload.

Wind reservations, annual attempts, verified completions and actual starts are
separate resources. A failed attempt retains its known completions while total
actual starts remain unknown. A null work pin leaves actual work unknown even
after a successful score. All read/byte reservations remain charged. Verified
private payload bytes use `byte` units, distinct from acquisition traffic. Caller
work pins are never refreshed or discovered by scanning the store.

Source reads are completed before annual modeling. A later model failure can
therefore retain the full source-read cost. CPU, peak RSS and inner wake calls are
unknown in this native profile. The generic confirmation callback duration is
separate and must not be added to overlapping kernel intervals. These partial
records do not close preparation, provider or human-effort costs or establish
scientific improvement. The existing comparative report-input version 3 accepts
either cost-input version through its pinned `costs` artifact.

The [wind cost-reader verification](reviews/part-5-wind-cost-report.md) includes
native saved work, failure/unknown handling, comparative exports and an isolated
core-only installed reader. Private runtime and real task admission remain open.

The load profile separates reservations, case attempts, completed evaluations and
model starts. An interrupted case leaves total starts and inner work unknown,
while completed counters remain lower bounds. Do not add those subsets or
reservations to full totals. Component `_linearize` counts include Newton work
and do not measure FLOPs. CPU/RSS, human/setup, provider and generic process costs
remain separate. These work receipts do not qualify private execution or establish
complete cost evidence, efficiency or scientific utility.

The core-only macOS installation reconstructs the preceding native control with
example/framework imports, writes, network and new processes denied after
initialization. The old and new installed CLIs produce identical default report
bytes. The [report integration evidence](../examples/utility/verification-load-cost-report-v1/README.md)
records the scope. The current core differs from the preserved v5 guest wheel.
That historical guest qualification does not apply to the updated checkout.

## Native work in suite cost reports

Suite accounting now joins original circuit, generic callback and wind native
reports to their reserved cells. It checks typed jobs, frozen specifications,
observed report bytes and saved process output without running an entrypoint.
Invalid native evidence produces an accounting blocker. It cannot supply counters.
Native job metadata is limited to 4 MiB in this reader.

| Resource | Meaning | Limit |
| --- | --- | --- |
| Native process starts | Original process identity in a verified stopped report | A subset of generic science reservations; do not add both as starts. |
| Native inner model calls | Circuit solve records | Different from solver iterations and callback entries. |
| Driver final solver/component counters | Final shared-problem snapshot | Do not sum the shared snapshots as exclusive work. |
| Scenario solver/component counters | Sum across declared independent scenario problems | Separate from later fresh evaluation jobs. |
| Wake/gradient callback entries | Attempted/completed/failed/unresolved calls | No inferred inner wake solves or derivative operations. |

Failed traces retain unknown counts, including each generic callback's frozen
kind. Old circuit results without final counters also retain unknown fields.
The circuit verifier now checks original job/completion/stdout before accepting
its counters. Scalar outcomes and feasibility remain separate from these costs.
Full scientific, training, resource, provider and human-effort closure is still
required before any total-cost conclusion.


## Scenario process costs in suite reports

Suite accounting also reads the supervised engineering scenario profile. It binds
an observed receipt to its reserved case, execution binding, scenario job,
original process command, completion and bounded output. The reader imports no
supplied evaluator and does not open its captured source tree.

The projection separates outer process starts, lifecycle duration and each
explicitly declared count diagnostic. Physical residuals and boolean convergence
flags are not costs. Missing solver/component/derivative counts stay unknown.
Failed processes can have a known outer start while their inner work stays
unknown. Unobserved reservations do not acquire inferred starts.

Scenario starts are a subset of science reservations. Lifecycle duration overlaps
process duration. Neither is extra work to add to its enclosing total. These
records do not close training, provider, resource or human-effort costs, qualify a
private scorer or establish scientific utility. Part 5 remains incomplete.


## Provider token components in cost reports

Batch cost projection now retains the normalized uncached-input, cached-input,
cache-creation and reasoning-output token fields alongside input/output/total
tokens. It copies only recorded values. Missing categories stay unknown, including
legacy records and interrupted calls. It does not subtract components from totals,
replace missing values with zeros or use top-level SDK summaries in place of the
adapter's normalized whole-call usage. Components and totals can overlap and must
not be added as separate token consumption.

Accounting Markdown and comparative summaries state that overlap and retain
unknown billed spend. Existing CSV cost tables preserve unknown values as blank
cells. This exposes more of the original usage evidence. It does not measure a
provider bill, establish full cost closure or qualify a live host.


## Campaign lifecycle costs in suite reports

The public campaign attempt profile now joins outer process starts and committed
model lifecycle timing to its reserved suite cell. The reader follows the final
event-committed controller state. It checks the original campaign specification,
attempt, nonce-bound process receipt, lifecycle artifact and output hash. It does
not open original input/source roots, decode model arrays or import an adapter.
Journal replay rehashes committed public artifacts, including any committed
forcing override.
Campaign projections are reused within one join instead of replaying the same
journal for every observation.

The disposable state cache and mutable scratch metadata are not accounting
evidence. Missing committed lifecycle timing remains unknown, including failed
workers and recovered records without that artifact. Outer worker starts are
subsets of science reservations. They do not count inner solver, model or training
operations. Lifecycle timing runs through inspection and excludes cleanup. It
overlaps the enclosing process duration, which must not be added as extra work.

The adapter training record does not declare a cost unit. The reader validates
that record but does not report it as seconds, CPU time or dollars, or declare
training qualified. Full training/resource/provider/human-effort closure and the
independent experiment remain open.


Saved-result recovery also had a software gap: its synthesized receipt omitted
process identity, so the batch observer could not settle the original worker
charge. New campaign-recovery-receipt-v2 records preserve the verified original
identity/stop and commit the lifecycle metadata. Recovered evaluation provenance
retains the actual execution seed. This follows the existing group-absence and
nonce checks and never launches a replacement worker. Malformed process identities
remain unresolved. Legacy recovery receipts without identity retain unknown
starts and lifecycle timing and stay charged. No legacy receipt is rewritten.

## Candidate container RMSE scorer

`ContainerRMSEScorer` in `utility.container_scoring` is a programmatic candidate,
with no CLI or registry activation. It accepts frozen finite prediction vectors
and an explicitly configured local Unix-socket `FixedScorerRuntime`. Construction
does not open labels or contact the daemon. Before private access it verifies the
grant, public data, cached pinned image and server fingerprint. Its durable access
intent binds the original label and public job hashes. Inputs are limited to one
MiB each and the callback needs 64 reserved active seconds for lifecycle/API work.
This reservation is not a strict whole-host callback deadline.

The fixed trusted worker uses the container memory/CPU/PID/isolation controls and
the shared hard 16 KiB child-output cap. It executes no supplied model code. Its
independent watchdog must arm before start and removes the original container.
Offline scorer recovery verifies saved original runtime/source/result/cleanup
evidence without opening labels, contacting Docker or starting replacement work.
Committed suite receipt replay also performs no new scoring. Pending suite
attempts remain charged. `ConfirmationService.recover(grant)` can explicitly
publish a verified original result through the registered scorer's
`recover(grant, model)` method. The method must never start replacement work or
open labels. Recovery requires the original reservation, committed access intent
and unchanged grant. Missing evidence refuses recovery without retry.

Recovered receipts carry `utility-confirmation-recovery-v1` provenance bound to
the original attempt, grant, access, scorer and score. Their original callback
duration remains unknown. Public cost reports count the recovery publication
without inventing scoring starts or filling unknown time with zero. Legacy and
normally completed receipt serialization is unchanged. A committed receipt is
replayed directly, including after an interruption before acknowledgement.

Two synthetic end-to-end controls and extracted-wheel relocated recovery are
recorded in `examples/utility/verification-container-scorer-integration-v1`.
They do not admit real data or qualify the new runtime's complete failure matrix.
Container-specific public cost evidence, independent task custody and the frozen
protocol remain outstanding. The macOS profile is unchanged and has no automatic
fallback to this candidate.

An actual synthetic publication interruption and recovery with deleted labels,
daemon access disabled and new starts forbidden is recorded in
`examples/utility/verification-confirmation-recovery-v1`. The public journal and
cost report also replay from an extracted wheel after relocation, without opening
the private or original root, invoking either scorer method or starting a process.
This is software evidence, not independent scientific confirmation or runtime
admission.

## Container confirmation execution receipts

The registered container scorer can attach
`utility-confirmation-container-execution-v1` metadata to a public confirmation
receipt. It binds the grant, scorer, score, runtime, original container/nonce,
pinned image, source hashes and start/stop/cleanup evidence hashes. It contains no
private paths, label hashes or arrays. The trusted scorer verifies the original
private runtime evidence before exporting it. Offline readers validate the public
bindings. They do not independently attest the daemon or open private evidence.

For a completed fixed-worker execution, reports can record one container start
and one scoring-child process start. These are distinct physical scopes, not two
scientific evaluations. The lifecycle duration runs from the start request through
stopped-container inspection. It includes API/polling overhead and excludes
preflight, staging, creation, output collection and cleanup. It overlaps callback
duration and must not be added to it or called CPU time or total phase cost.
Execution-metadata export occurs after the timed callback and is not included in
that callback measurement.

Recovery exports the same saved lifecycle measurement without new timing or work.
The original callback duration can remain unknown while the nested worker duration
is known. Missing lifecycle measurements stay null. Callbacks without execution
evidence retain unknown physical starts and the old receipt shape. Invalid or
foreign execution evidence leaves the original attempt charged and uncommitted.
Registered runtime/scorer configuration changes refuse before further private use.

Actual synthetic publication/recovery and relocated wheel checks for new and
legacy receipts are under `examples/utility/verification-public-execution-v1`.
The cost reader needs no scorer, private directory, original execution root,
network, model process or optional scientific runtime. Complete cost evidence
remains false: preparation, CPU/RSS, training, provider billing and human work
still need their own evidence. This does not admit independent data or qualify
the candidate runtime's complete failure matrix.

## Original container creation reconciliation

The fixed runtime saves ownership intent before sending create. Lost creation
acknowledgement and pipe-setup failure attempt bounded cleanup of the same original
container. No replacement create or start is issued. The intent preserves the
reserved nonce/name, runtime/configuration identities and input hashes even when
the original ID acknowledgement never reached the controller.

`runtime.reconcile_creation(root)` observes only that original creation. It does
not read job/label arrays or execute the scorer. `stop=True` explicitly permits
removal of the identified owned container. Subsequent observations use its saved
exact ID. Without a known ID, a name lookup returning 404 remains
`absent_at_observation` with creation uncertainty: the original request might
commit later. It is not proof of no launch, and it does not release the scientific
reservation, authorize another attempt or supply a score.

Cleanup retries retain the first snapshot and append later observations. Failed
deletion and API errors remain unverified. Foreign ownership refuses deletion.
The original scored-result recovery remains separate and still requires verified
completion/output/cleanup evidence. Actual local lost-acknowledgement and pipe
failure controls, plus a preserved success/recovery path, are recorded in
`examples/utility/verification-container-creation-v1`. These controls do not
complete runtime admission or independent task confirmation.


## Confirmation command registration

`autoengineering utility confirm WORKDIR GRANT --registration PROFILE` delegates
to the existing confirmation service. Add `--recover` to publish a verified result
from the original charged attempt. An uncertain attempt cannot restart through
normal dispatch, and committed receipts replay without rescoring.

The distributed CLI has no admitted private scorer. A trusted application builds
this same command with reviewed registrations, for example:

```python
from autoengineering.utility.command import utility
from autoengineering.utility.confirmation_command import build_confirmation_command

# registrations contains application-owned ConfirmationRegistration objects.
# Each names its reviewed qualification digest and exact suite/partition/scorer.
utility.add_command(build_confirmation_command(registrations))
utility()
```

The wrapper then accepts `confirm WORKDIR GRANT --registration PROFILE`. Registry
objects come from trusted Python. Grants cannot name executable factories or admit
a profile. Registration binds an explicit admission assertion, qualification
digest, suite, partition, outcome and live scorer identity. The application must
verify the qualification and custody before asserting admission. A digest alone
proves neither privacy nor scientific eligibility. Current private candidates
remain unadmitted.

The command checks the full sealed selection before pinning registration metadata
under `control/confirmation-registrations/`. The pin is not a reservation or access
grant. A changed pin refuses the same grant. The suite journal and confirmation
service remain authoritative for starts, accesses, results and charges. Errors
omit private payloads. An installed authored wrapper exercised interruption,
refused retry, recovery and replay with one callback and one recovery. This
qualifies that transport behavior, not an independent task or private scorer.


## Frozen baseline confirmation groups

Use `utility-suite-v2` only for a newly prepared suite with an explicit
`BaselineReusePolicy`. Its groups name assigned baseline cells, one source cell,
the canonical model snapshot digest, default configuration digest, scorer identity
and exclusive cost fractions. Construct it before creating the suite journal:

```python
from dataclasses import replace
from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import BaselineReuseGroup, BaselineReusePolicy

group = BaselineReuseGroup(
    (source_cell_digest, follower_cell_digest),
    source_cell_digest,
    baseline_model_digest,
    digest(default_parameters),
    scorer_digest,
    (0.25, 0.75),
)
policy = BaselineReusePolicy(
    "utility-baseline-reuse-v1", comparison_protocol_digest, (group,)
)
spec = replace(
    spec, schema="utility-suite-v2", protocol_digest=policy.digest,
    baseline_reuse=policy,
)
```

The fractions are a protocol choice, not a measured reduction in total work. The
original comparison protocol remains referenced by its digest. This changes suite
identity and cannot amend an existing run. V1 suites retain their exact serialized
shape and do not acquire reuse implicitly.

Groups must contain disjoint assigned baseline cells from the same task/scenario.
Their frozen selections must reference exactly the same model and selected-state
artifact. The source must match the declared default parameters and scorer. This
is a deterministic reference profile. A policy assertion alone does not qualify
determinism, data custody, a private scorer or a trained model.

Invoke the existing confirmation service or trusted registration CLI for each
designated source. Followers are references, and the journal forbids new follower
scoring reservations. Source retries/recovery follow the ordinary original-attempt
rules. Analysis, reports and cost exports reconstruct successful feasible source
results and shares automatically. V2 cell tables include `confirmation_reused`.
Failed or infeasible sources retain their actual result and leave followers
unscored. Unknown costs remain blank, and physical quantities are counted once.

This profile handles confirmation after sealing a common immutable baseline.
Policy v2 explicitly opts into selection-reference preparation through the
exposed scripted coordinators. Existing policy-v1 runs retain separate baseline
evaluations and their actual cost.


## Selection acceptance and confirmation outcomes

Executed campaigns bind their acceptance rules through the task's legacy
`outcome_digest`. A confirmation `OutcomeSpec` names a primary quantity, its units,
direction and evaluator. These two digests are different contracts. Use an
explicit versioned task to preserve both before creating a new suite:

```python
from autoengineering.utility.contracts import ScoredTaskSpec

task = ScoredTaskSpec.from_dict(legacy_task.to_dict() | {
    "schema": "utility-task-scoring-v2",
    "scoring_outcome_digest": primary_outcome.digest,
})
```

Keep `outcome_digest` bound to the selection acceptance rules. Grants use the
registered `primary_outcome.digest`. Execution validators continue to check the
acceptance binding, while confirmation checks `scoring_outcome_digest` before
reservation/access. A changed scoring identity creates a new suite identity and
cannot resume the original run. Legacy untagged tasks keep their original direct
binding and serialized shape. A scoring field without the version tag refuses.

This versioned task is metadata, not admission. The primary outcome must agree
with the frozen scientific question, units, data and scorer qualification. It
does not turn engineering objectives into prediction losses or supply private
data access. A bounded authored engineering fixture exercised selection, sealing
and an authored confirmation callback with distinct digests. Independent task and
private-scorer admission remain open.


## Preparing shared selection references

Set the baseline policy schema to `utility-baseline-reuse-v2` and its
`selection_reuse` field to `frozen_reference` before creating the suite. Keep the
comparison execution plan digest in `comparison_protocol_digest`, with the policy
digest bound as the suite protocol. Confirmation-only v1 policies retain their
original bytes and behavior. A changed policy creates a new suite identity.

The source cell must occur before every follower in the frozen matrix. Groups
still require the same task/scenario, supplied unchanged baseline, defaults and
scorer identity. The coordinator checks the supplied defaults before dispatch.
It preserves route order and executes only the source baseline. Followers are
batch-v1.1 `reference` cases with zero host/scientific allowance. Attempts to
reserve either resource against them fail. Parent metadata wall-time allowances
remain reserved; no source or follower allowance is refunded on interruption.

Followers carry the original child-result digest and exact model/state artifacts.
The existing suite/controller journals remain authoritative. Source lineage is
verified before parent completion, during offline reading and at the selection
barrier. Recovery can acknowledge original reference work without a new scientific
execution. An unresolved source blocks followers. A source without an eligible
selection cannot supply an eligible follower.

Source physical costs retain their original receipts and declared exclusive
shares. `baseline_reference_copy_duration` stays unknown until measured. This
prevents a complete-cost or efficiency claim from treating copying as free. The
installed four-cell fixture used one scientific process; a 34-cell test verified
the same rule across child batches. These are integration checks on exposed
scripted fixtures, not independent utility or private-runtime qualification.

## Frozen baseline policy in direct analysis

For suites with a frozen baseline reuse policy, `analyze` and
`analyze_receipts` require the declared group and allocation fractions. Shared
scores must be successful and feasible. A follower cannot supply an independent
score or reuse a failed source. Missing followers remain missing in the assigned
denominators. Legacy suites retain explicit manual allocations.

These checks validate public declarations and score consistency. Only the
journal-based confirmation path verifies the original source grant, selected
model and state, and physical attempt history.

## Candidate guest observation validation

The internal `utility.guest_observations` module constructs a fixed OCI request
from a v2 frozen guest job and launch intent. It validates saved image and container
configuration, original unstarted creation, started/stopped state and matching
cleanup before projecting `guest_receipts` records. It rejects changed commands,
environments, owner/image identities, host mounts, resource/isolation settings,
restarts and contradictory lifecycle evidence. Unknown elapsed time stays unknown.

The module performs no daemon operation, starts no process and samples no new
clock. Its raw-document hashes identify saved producer claims. Authored capture
tests establish record consistency, not actual image identity or enforced privacy.
No default executor or confirmation service uses this candidate path yet. Actual
owner acquisition, durable lifecycle handling and image/resource/privacy
qualification remain required before runtime admission.

The internal `utility.guest_owner.GuestOwnerJournal` persists owner intents and
original observations using the same checks. A create-only suite owner lease binds
the original inference claim, launch identity and owner directory. Its immutable
journal rejects repeated or out-of-order transitions. Create/start intent without
an observation remains uncertain. Reopening reads evidence and cannot retry the
transition. Completed journals project the original start/stop/cleanup records,
with unknown elapsed time preserved. Relocated copies support replay only.

This journal supplies no daemon operations, input staging or dispatch authority.
A future launcher must hold its writer lock across intent and the single external
dispatch. Interrupted initialization requires explicit reconciliation. Watchdog and
early-abort cleanup, actual dispatch/input transfer and runtime qualification remain
open. The existing suite claim remains charged independently of journal phase.

## Candidate frozen guest transfer inputs

`utility.guest_inputs.prepare_guest_inputs` prepares one transfer archive for the
frozen routing worker. It requires the original suite/owner writer locks, lease,
frozen selection and charged composite access. It checks public model, source,
environment and wheel identities before recording an immutable input intent and
reading the permitted drivers. An existing intent prevents another preparation
attempt. The complete package manifest is published last.

The archive contains the exact worker job/intent/claim, environment and lock,
selected state/runtime, fit/provenance metadata, inventoried Python sources and
one normalized driver artifact. It excludes fitting/comparison arrays, labels and
undeclared directory contents. Fixed limits are 1024 files, 4 MiB per file, 32 MiB
payload and 40 MiB transfer bytes. Members use uid/gid 1000, regular-file mode 0600
and directory mode 0700. Links, extensions, duplicates and trailing content refuse.

`verify_guest_inputs` reconstructs saved packages without source/driver roots,
model execution, array interpretation or new clocks. When package preparation has
begun, the owner start intent requires a completed package and pins its digest.
Lifecycle replay rechecks that binding. Legacy evidence-only owner records omit
the optional field and retain their original bytes. Actual dispatch must require
the package binding; a legacy record alone supplies no runtime admission.

Preparation does not transfer or execute the archive. Actual input transfer,
dispatch, watchdog/early-abort handling, image assembly and measured OS/resource/
privacy qualification remain open. No default executor or confirmation service
activates this candidate path. These checks do not admit independent data or set
useful gains and tolerances.

## Candidate stdio guest bootstrap

The versioned `GuestStdinPolicy` uses a fixed `utility.guest_bootstrap` command and
one-shot stdin. The original direct-worker policy retains its fields. The bootstrap
validates a bounded frozen input frame before extracting files into its own private
workspace. It checks the actual interpreter/installed wheel before invoking the
fixed worker, then streams only the original bounded result/output artifacts before
exit. No uploaded source is executed. Malformed or foreign frames refuse.

Completed response capture is published last. `read_capture` reconstructs saved
bytes without a live stream, model, original inputs, runtime probe or new clock.
An interrupted or contradictory capture stays unverified. Worker duration is
preserved independently of unknown container lifecycle time. This codec supplies
no execution authority and does not qualify privacy, resources or actual Docker
attach behavior. The owner API connection, deadline/watchdog and cleanup remain
open. No default executor or confirmation service activates this candidate.

## Candidate Unix attach transport

`utility.guest_attach.attach` connects only to an explicit Unix socket, API version
and immutable container ID. It requests live stdin/stdout/stderr with logs disabled,
requires HTTP 101 and validates bounded Docker output frames. A verified bootstrap
request must match expected job/launch/package digests before its single input
transfer. Stdin then half-closes. Stdout reaches the existing result capturer;
bounded stderr is discarded. Malformed, excess or trailing error output refuses.

An absolute monotonic deadline spans handshake, input, output and EOF waiting.
Progress does not renew it. Cancellation is checked during idle I/O. Failed or
partial writes cannot be replayed on that connection. This transport never creates,
starts or retries a container. Timeouts and closed sockets do not prove a stopped
process. Original lifecycle proof and independent watchdog/cleanup remain required.

Tests include owned local Unix peers, not a daemon or guest. Daemon/image identity,
durable dispatch, actual start/stop and OS/resource/privacy qualification remain
open. No default executor or confirmation service uses this candidate transport.

## Candidate daemon preflight and creation

`GuestDaemonAPI` pins the local endpoint, explicit API version, canonical server
fingerprint and implementation/interpreter identity. Its bounded Unix HTTP reader
handles content-length or chunked JSON under an original absolute deadline.
`GuestCreationController` binds preflight and one unstarted creation to the original
suite and owner journal. It requires both writers, the original charged access,
frozen selection and completed input package. Intent precedes CREATE.

Returned creation responses are saved before interpreting warnings or IDs. Known
successful responses are bound to the created event. Known warnings block recovery;
a genuinely missing response stays unknown. Reconciliation can observe only the
original matching unstarted container and never issues another CREATE. Absence is
not permission to recreate. Legacy events omit the optional response reference.

The controller supplies no start operation until the independent watchdog and
stop/cleanup path exist and are qualified. Tests use authored API projections and
owned Unix HTTP peers. Metadata preflight does not prove OS enforcement. No default
executor or confirmation service activates this candidate API.

## Candidate independent guest watchdog

`guest_watchdog.arm` requires original suite/owner writers, reviewed unstarted
creation, the original runtime identity and a deadline within the grant. It starts
one detached watchdog process with an anonymous owner pipe. Readiness binds the
original plan and actual child PID before any future start may dispatch. Closing
the pipe, cancellation, invalid disarm or the original deadline triggers cleanup.
There is no container create, start, model execution or scientific retry here.

Cleanup verifies the pinned daemon and exact original container ID, image and
owner labels. Resource drift cannot remove authority to clean up an owned
container. Foreign identity refuses mutation. Durable intent precedes each single
kill or forced removal request. Lost responses are followed by observation rather
than another mutation. Saved stop and absence observations remain separate: an
absent container does not supply a missing stop observation or successful result.
Unverified cleanup remains explicit. Completed saved outcomes replay without
contacting the daemon or repeating cleanup.

Disarm requires the parent's completed original cleanup journal and a fresh
observation that the original container is absent. Local FD closure alone is not
stop evidence. The new watchdog remains a candidate tested on authored peers;
actual daemon/image, resource and privacy qualification and durable start/attach
integration remain required. No default service activates it.

## Candidate single-start guest dispatch

`GuestDispatchController.run` connects the reviewed creation, independent watchdog,
Unix attach transport and fixed stdin bootstrap. It requires both original writers,
charged access, immutable inputs and the matching runtime. A fresh dispatch directory
is consumed before arming. The original watchdog plan and actual readiness are saved
as attach intent. Completed HTTP upgrade is recorded before a start intent binds
that evidence into the owner journal. The controller rechecks the unstarted owned
container and sends START once. It never creates a container.

The returned START status, bounded body size and body digest are captured before
interpretation. A missing response stays unknown. Only HTTP 204 with an empty body
permits the one stdin transfer. Original input is half-closed once. Bounded output
must be captured completely before the owner observes terminal state. The surviving
owner measures its dispatch-to-stop interval. Watchdog cleanup retains original
stop and absence evidence. Both cancellation callbacks and newly appended suite
cancellation events are polled during I/O. Cleanup has its separate bounded grace
period and cannot renew the original execution deadline.

`reconcile_dispatch` requires the original owner writer and lease. It reads only
saved watchdog observations and appends lifecycle events that those observations
support. It issues no API, attach, input or model request. Missing start intent or
missing terminal evidence stays incomplete. An absent container cannot fill in a
missing stop. Unknown original duration stays unknown after interruption. A saved
stop is never relabeled when a later cancellation arrives.

`read_completion` verifies the manifest-last completion after relocation using the
owner archive alone. `transport_status` reports complete, missing or unverified
transfer/lifecycle evidence. A complete transfer requires the original successful
START acknowledgement, saved capture, matching terminal state and verified absence.
Cancellation or timeout prevents that verdict even if a capture already exists.
The worker's original scientific status and all qualification requirements still
apply. Completed saved records cannot authorize another dispatch.

Legacy owner events omit the optional dispatch reference and retain their original
bytes/hashes. The new controller remains separate from default executors/services.
Actual daemon/image, installed-package, resource/privacy qualification, archive and
confirmation-service integration, and initialization recovery remain open.

## Dispatch-bound guest archive export

`archive_guest_dispatch` exports a v2 guest inference archive from an original
completed owner. It requires both writers, matching original scopes and a pinned
publisher implementation. Freeze `publisher_identity()` in the application's
registration, then pass that same digest to publication and verification. V2
verification requires this explicit pin. V1 records retain their original schema.

The public record binds the original owner journal, dispatch completion, START
response, capture and observed absence to the existing lifecycle projections.
Private dispatch plans, paths, driver capsules and raw OCI observations remain in
the owner scope. Their commitments are retained as metadata. The public reader
checks producer projections and hashes. It does not independently attest the daemon
or OS boundary. A successful capture's original binary response digest is rebuilt
from the public worker result and permitted outputs without loading arrays.

Publication is create-only with a manifest-last grant pointer. After interruption,
original saved evidence can complete the export without another model, attach or
START request. A published record with missing or corrupt bytes fails verification
and is not silently repaired. Complete, failed, cancelled and timed-out executions
retain their original status and timing limits. In particular, cancellation after
stop observation cannot turn an existing capture into scoring outputs. A missing
start or stop observation cannot become a started-execution archive.

The public closure contains metadata and permitted result/output bytes. It needs
neither the private owner workspace nor the driver capsule for cold verification.
Failed transport exports no scoring outputs. The worker's scientific/model failure
status remains distinct from transport completion. All records retain the
`unqualified-candidate` boundary. Default confirmation execution/recovery and the
legacy local archive reader do not admit this guest archive. The guest executor
facade, composite-service integration and actual runtime/privacy qualification
remain open.

## Candidate guest executor facade

`GuestRoutingExecutor` joins the fixed guest preparation, creation, single-start
dispatch and v2 public archive interfaces. Construction takes explicit source,
driver and work scopes, source inventory/lock, guest/environment metadata, local
API and publisher pin. Its registration binds those identities, fixed policy and
facade implementation. It does not install dependencies, assemble an image, admit
private data or register a scorer.

Execution requires the original suite writer and charged composite access. One
initialization record freezes the job, nonce, claim, owner scope, registration and
absolute deadline before reserved-driver access. That public grant key is consumed
before global claim/owner publication. The same deadline covers preparation checks,
creation, attach, input/output and stop observation. Preparation checks cancellation
and expiry before each bounded input read and before publishing its package. These
checks prevent a late daemon launch after synchronous filesystem work returns;
they do not interrupt a blocked filesystem call. Filesystem timing, OS privacy and
resource enforcement still need actual qualification.

`reconcile_initialization` can complete matching original metadata under the suite
writer. It samples no new clock, reads no source or driver scope and contacts no
daemon. It can finish known empty directories and original claim bytes. Unknown
files/events, changed records, symlinks and missing records after a completed marker
refuse reconciliation. It never prepares inputs or dispatches a model. An intended
attempt cannot execute again from the same or another work directory.

`recover` reconciles saved original dispatch observations and publishes the public
archive when the evidence supports it. It cannot create, attach, start, refit or
reopen original drivers. An uncertain creation, missing dispatch evidence or an
incomplete input package remains charged and requires explicit resolution. In
particular, an unstarted container left before watchdog arming is not automatically
recreated or started. This facade does not yet supply the missing operator cleanup
path for every such early failure.

For a fresh process, `GuestRoutingExecutor.for_recovery(store, grant, work_root)`
loads the original registration without constructing live source/driver/API scopes.
The resulting object refuses execution. A published result can replay with original
work and driver directories absent. Private metadata reconciliation still requires
the original owner scope. The portable v2 archive reader remains available without
constructing any facade. Default scorer/CLI paths remain unchanged. Composite-service
integration and actual runtime admission are still open.

## Candidate guest composite confirmation

`GuestCompositeRMSEScorer` and `GuestCompositeConfirmationService` join the guest
facade's v2 archive to the existing fixed vector scorer. Construction is explicit
and application owned. Vector-only services, local composite services and local
scorers refuse the guest profile before access. The local registration remains v1;
the guest registration is v2 and additionally pins the facade registration, inference
runtime, publisher and policy. Both remain unqualified candidates.

The parent composite grant and its two-start reservation stay unchanged. Inference
must publish original lifecycle/capture evidence before a create-only transition
binds that archive to the prediction-specific subordinate vector grant. The reader
checks the original facade initialization and completion marker against the archive
and registration. Worker science/model/infrastructure failures publish their original
failure and authorize no inner score. Cancellation at the handoff starts no score
worker and opens no labels.

Recovery reads original inference and scoring evidence. It can finish a missing
handoff publication but never starts an inner score that had not completed. A
recovery-only guest facade can recover an original completed score without a live
inference API or original work/drivers. The existing fixed vector runtime must
still supply its original score/stop/cleanup evidence. Public receipt, transition,
score and accounting replay need no private scope, model execution or new clock.

Guest accounting distinguishes inference and scoring container starts and reports
their total. A successful guest chain has one container in each stage and two in
total. Failed inference has no scoring container. An incomplete successful handoff
retains unknown scoring and total counts, even when inference's count is known.
Total container duration is unknown if either contributing stage duration is unknown.
Stage durations overlap the containing callback measurement and must not be added
to it. Local/v1 accounting retains its previous meaning and values.

This is candidate orchestration and producer-record verification. Authored peers
and the fixed local scoring fixture do not establish actual guest inference, OCI
privacy or independent utility. Runtime/private-data admission, early unstarted
resource cleanup, strict filesystem timing, installed/platform/host qualification
and independent scientific confirmation remain open. No default CLI or scorer
allowlist activates this profile.

## Original creation cleanup before watchdog ownership

`cleanup_creation(owner, store, api)` and the facade's `cleanup_creation(grant)`
provide explicit cleanup for an original consumed creation that has no start intent
and no watchdog owner. The suite and owner writers, original lease/claim, charged
access and pinned API are required. Cancellation and changed resource settings do
not remove authority to clean up the exact original CID/image/owner labels.
Foreign identity refuses mutation. Known CREATE warnings remain adverse start
evidence but do not prevent cleanup of an owned resource.

The create-only cleanup plan has one fixed 10-second window. Original response or
created-event evidence supplies a known CID. With a lost response, the original
fixed name can identify the owned CID. Target binding is durable before mutations.
At most one kill and one forced removal may be intended. Intent precedes each RPC;
interrupted recovery skips a consumed operation and never renews the window. A
lost removal response needs an actual absence observation. Saved completion replays
without API calls, clocks or original driver/source scopes. Resumed elapsed time
stays unknown rather than being invented from a new recovery clock.

An absent name after an unknown CREATE response is `creation_unresolved`, because
the original request might still complete. An intended removal without a verified
result remains unverified. Those outcomes retain charges and require explicit
operator resolution. They are not permission to recreate, start or reissue a
consumed mutation. Cleanup intent also prevents creation reconciliation, owner
journal advancement and fresh watchdog/start authority. An existing watchdog plan
retains cleanup ownership and refuses a parallel creation-cleanup owner.

The live facade attempts this scoped cleanup when creation fails before watchdog
ownership, then preserves the original error. It never turns early cleanup into a
one-start inference receipt or a scoring vector. Raw cleanup observations remain in
the private owner scope. Actual daemon/resource enforcement, late unresolved CREATE
and interrupted watchdog-startup resolution still need qualification/operator paths.
This does not qualify the candidate runtime or admit independent data.


The current candidate guest source is also preserved in the
[extracted-wheel verification](../examples/utility/verification-guest-current-wheel-v1/README.md).
Its offline cleanup and composite score/cost readers pass outside the checkout.
The successor prepared inference inputs retain `starts_authorized: false`.
Extraction checks do not establish installation or runtime/privacy qualification.


## Original watchdog startup cleanup reconciliation

`reconcile_startup_cleanup` and the guest facade's explicit
`cleanup_watchdog_startup` resolve an original unstarted owner after interrupted
arming. They require the original suite/owner writers and charged access. The
watchdog holds a separate cleanup lease throughout its lifetime. Reconciliation
refuses a live lease, and a delayed child sees cleanup evidence before publishing
readiness. No replacement worker, attachment, START or scientific allowance is
created. The facade preserves its original error and charges.

The first cleanup fixes a window bounded by ten seconds and the original plan's
cleanup cap. Its reason and consumed kill/removal intents survive interruption.
Expiry produces uncertainty without an API call. Missing legacy timing evidence
refuses a new allowance. Saved outcomes bind the window digest, while old completed
records omit the new optional field and retain their bytes. A start intent is
refused once cleanup evidence exists. Saved replay needs no current runtime or
clock. These are authored fixture checks, not runtime/privacy qualification.

The previous extracted wheel and prepared v4 inputs retain their original source
scope and predate this increment. Current installed/platform/host qualification,
strict filesystem timing, unknown late creation/uncertain removal resolution and
independent admission, thresholds and scientific comparison remain open.


## Offline guest image recipe

The administrative `examples.utility.guest_image` module prepares a candidate
Linux amd64 image recipe from pinned environment inputs. It checks the complete
core source set and every declared wheel Python source before creating output.
A stale wheel, symlink or existing output is refused. Verification reads only the
saved package and an explicit plan digest. It starts no process or network request.

The [prepared recipe](../examples/utility/prepared-guest-image-v1/README.md) binds
an immutable Python base image, a micromamba installer archive, 49 existing locked
packages and a current wheel. No package archive or image layer has been acquired.
The generated pip command targets the locked interpreter with no index or dependency
resolution. The recipe's intended behavior has not been tested in an actual build.
Its qualification proposal and build limits grant no authority.

To prepare another recipe after building source-matched environment inputs, use a
fresh output directory. This administrative command does not build an image:

```sh
mkdir -p outputs
pixi run python -m examples.utility.guest_image \
  examples/utility/prepared-inference-environment-v5 outputs/guest-image-recipe \
  --expected-digest 7c66ecada3955ad940d07fcf409b7f78bf68fc643950340f408d9d398a6fa06e \
  --source-root .
```

Source changes require a new matching wheel/input package. Context materialization,
bounded acquisition/build execution, actual-daemon cases and diagnostic command
profiles remain required before runtime/privacy qualification.


## Materializing existing image inputs

`examples.utility.guest_image_context` copies the recipe's already-present archives,
installer and local wheel into a fresh private directory. It performs no download,
installation, extraction or build. The cache uses the relative names listed in
`plan.json`, including `archives/` and `installer/`. The local wheel comes from the
saved environment package. Unrelated cache files are ignored.

After separately authorized acquisition has supplied the pinned files, run:

```sh
pixi run python -m examples.utility.guest_image_context materialize \
  examples/utility/prepared-guest-image-v1 /path/to/pinned-cache outputs/guest-context \
  --expected-plan-digest f9b1782fb389a6e7d262de44089c5cafb3bde1fb4852ffa36c0e1b57fbb252d3
```

The command prints a context digest. Keep that pin for subsequent verification:

```sh
pixi run python -m examples.utility.guest_image_context verify outputs/guest-context \
  --expected-digest CONTEXT_DIGEST
```

`build/` contains the reviewed Docker context. `proof/`, the materializer source
artifact and `context.json` support verification after relocation. The verifier
requires the exact saved closure and starts no model, process or network request.
An interrupted copy retains its partial output and refuses reuse. Use a new output
directory for a separately requested copy. No context operation changes build or
runtime authorization. The source-checkout helper is not in the preceding prepared
wheel. See [verification limits](../examples/utility/verification-guest-image-context-v1/README.md).


## Runtime archive acquisition

`examples.utility.guest_archive_download` prepares an exact archive-only request
from a verified image plan, then executes that explicit request against its fixed
private cache. It accepts only pinned conda-forge HTTPS archive URLs, rejects
redirects and unexpected HTTP framing, and verifies lengths and hashes before
committing files. Request and GET intents precede network work. Consumed caches
cannot be retried or resumed automatically. Completed caches verify offline.
The API and CLI do not install, extract, build or invoke a daemon.

The [actual acquisition evidence](../examples/utility/verification-guest-archive-download-v1/README.md)
records 50 verified files and a real materialized context. The large outputs remain
local under ignored `outputs/guest-runtime-archives-v1` and
`outputs/guest-build-context-v1`. This closes the missing-archive/context-input
step, not image assembly or runtime qualification. Tool review allowed the bounded
archive-only request. Installation, image acquisition/build and runtime execution
retain their separate authority requirements.


## Preparing a local image-build request

`examples.utility.guest_image_build` prepares one local request from a verified
context, existing Docker client and Unix endpoint. Preparation checks files and
socket metadata without connecting to a daemon. Actual execution requires separate
authority. See the [prepared request](../examples/utility/prepared-guest-build-v1/README.md)
for exact inputs, actions and limits.

The runner uses a fresh empty Docker configuration, excludes ambient remote-builder
and secret environment variables, and requires the pinned local default Docker
driver. Original job/command intents precede client starts. Any failed/uncertain job
stays consumed. A saved completion can replay without another client call.

A surviving owner bounds client time and output. Stopping that client does not
prove daemon cancellation. Build-step CPU/memory settings depend on daemon support,
and the proposed disk allowance is not a quota. Successful preparation records a
candidate image only, with runtime/privacy qualification still false. The request
does not authorize inference, scoring or the qualification matrix.


The [separate administrative wheel check](../examples/utility/verification-host-tools-wheel-v1/README.md)
covers the newer context, download and image-build helpers outside the checkout.
Five CLI help checks and guarded saved-result readers pass from extracted wheel
code. This does not replace the frozen guest image inputs or qualify installation,
Linux execution, a daemon, or the private runtime.

The approved v1 image-build attempt subsequently stopped before acquisition:
its empty Docker configuration could not discover installed Buildx. The original
work is consumed. V2 fixed plugin discovery but then rejected Buildx's `default`
endpoint alias. The [v3 proposal](../examples/utility/prepared-guest-build-v3/README.md)
resolves that context to the exact pinned Unix endpoint before accepting the alias.
All three metadata commands passed in actual read-only diagnostics. Earlier jobs
remain consumed. Approved v3 then pulled the base but stopped at its config-ID
check before building. The [v4 proposal](../examples/utility/prepared-guest-build-v4/README.md)
verifies the manifest/config relationship and descriptor/repository evidence.
All five actual saved pre-build responses pass the corrected rule. A new image
job needed approval. V4 received approval and completed in 45.4099 seconds.
Its Linux amd64 candidate passed the build-time core import smoke, and its saved
completion replayed under a fresh guard from relocated proof. See the
[actual build](../examples/utility/verification-guest-build-actual-v1/README.md).
Future corrected build versions have approval within the established scope and
limits. Runtime/privacy, model inference, protected scoring and independent
scientific admission remain separate requirements.

## Guest Python identity discovery

`examples.utility.guest_identity` binds a fixed metadata-only container to a
verified build and environment. It has no arbitrary command, input-data or
image-pull option. Source/client drift stops before launch; an original request
reserves one create/start and cannot restart. Cleanup uses one original window,
removes only the original owned container and retains unknown outcomes.

The [actual discovery](../examples/utility/verification-guest-identity-v1/README.md)
observed Linux x86-64 CPython 3.12.13 and the expected installed source. Its
candidate profile and saved completion replay without daemon access. The
`verify` command is report-only. This establishes interpreter metadata, not
private runtime, resource, model or independent scientific qualification.

## Candidate resource diagnostics

`examples.utility.guest_resource_runner` permits only six fixed stdlib probes
against the built candidate image. It provides no arbitrary image, command,
host mount, model or scientific-data input. The worker checks actual limits
before any resource action. A separate owner-pipe process owns one cleanup
window, verifies ownership before deletion and never repeats an uncertain DELETE.

The [actual checkpoint](../examples/utility/verification-guest-resources-v1/README.md)
records all six resource controls passing and the original containers absent.
The preceding refused creation remains charged separately. These are separately
identified diagnostics, not completion of the preserved 26-case matrix.
The `examples.utility.guest_resource_reader` module verifies original saved
proofs without daemon, process, clock or canary-file access. It cannot resume a
request or admit private execution. Actual inference and lifecycle controls,
full-chain qualification and independent scientific admission remain open.

## Derivative image with explicit environment

`examples.utility.guest_image_environment` builds a fixed derivative from the
verified cached image. Its scratch final stage copies only the source filesystem,
declares the approved environment and adds provenance labels. It has no arbitrary
Dockerfile, install, pull or model option. The unique local tag must be absent
before one tag operation. The original source digest must match before and after
the single build and appear in the saved resolution log. Consumed work cannot retry.

The [actual derivative](../examples/utility/verification-guest-image-environment-v1/README.md)
passes existing strict image metadata checks. Its fixed discovery probe observed
the expected interpreter and original-container absence. Fresh guarded readers
replay both completions without live services. Core source, the runtime wheel
and historical receipt rules are unchanged. Actual resource, inference and
lifecycle controls must bind the new image explicitly.

## Actual derivative controls and frozen inference

The [derivative resource checkpoint](../examples/utility/verification-guest-resources-v2/README.md)
records six controls passing against the derivative, with cleanup confirmed.
The fixed diagnostic catalogue preserves original-image serialization and admits
the explicit derivative only with its exact environment and inherited labels.

`examples.utility.guest_inference_smoke` prepares an explicitly exposed authored
fixture from an existing frozen selection. It copies bounded metadata, declared
model code and reserved drivers without fitting. One consumed execution invokes
the production guest executor and then reads its saved archive. It does not run
a scorer or admit independent data. The
[actual smoke](../examples/utility/verification-guest-inference-smoke-v1/README.md)
passed all four physical checks in one container, confirmed absence and recovered
from a portable public proof under a fresh guard. Full numerical parity, failure
controls, private scoring and task admission remain separate gates.


The [saved native/guest parity checkpoint](../examples/utility/verification-guest-prediction-parity-v1/README.md)
adds one native reference from the same exposed frozen fixture. All seven outputs
and the scoring prediction vector passed tolerances frozen before execution.
Prediction documents were not exactly equal. Its saved reader recomputes the
comparison without model execution. The [six preflight refusals](../examples/utility/verification-guest-preflight-controls-v1/README.md)
used the production facade with array/driver reads, transport and process starts
blocked. Each produced its exact expected refusal with all guard counters zero.
Neither checkpoint admits a private runtime or independent task. Adverse lifecycle
controls and the full inference/scoring chain remain open.


Two [actual unstarted cancellation controls](../examples/utility/verification-guest-cancellation-controls-v1/README.md)
now verify production cleanup after creation and immediately before START. Two
containers were created and neither started. Production cleanup evidence and
separate actual GETs verify both originals absent. Saved replay from a verified
public archive passed under a fresh guard. Running cancellation, owner/watchdog
loss, adverse output, lost responses and private qualification remain open.


Two [producer acknowledgment-loss controls](../examples/utility/verification-guest-response-loss-v1/README.md)
now verify no retry after real CREATE/START responses are withheld. Original
cleanup and fresh guarded saved replay passed. One started attempt has no model
result and retains its charge and unknown inference time. This is not a network
outage or actual owner-process-loss qualification. Nine adverse daemon cases and
private inference/scoring remain open.


Four [actual owner/watchdog-loss controls](../examples/utility/verification-guest-owner-loss-v1/README.md)
now cover exact owner SIGKILL before watchdog startup, after START and after
capture, plus exact ready-watchdog SIGKILL before START. Original cleanup passed
for all four. Captured success recovered without new inference and with unknown
lifecycle time. The running guest was interrupted before input transfer, and
pre-watchdog owner loss required explicit parent cleanup. Their scope does not
establish model-compute interruption or autonomous pre-watchdog cleanup. Five
adverse daemon cases and private qualification remain open.


An [actual running guest cancellation](../examples/utility/verification-guest-running-cancellation-v1/README.md)
now verifies cancellation after START and before input transfer. The saved
`infrastructure_failure` has no model result or prediction vector, keeps its
charged START and unknown lifecycle time, and replays without new execution.
This does not establish cancellation during model computation. Four adverse-output
cases and private qualification remain open.


The [four-task proposal preparation](reviews/part-5-confirmation-preparation.md)
now makes the existing task choices and gain policies machine readable without
observations or dispatch. The helper rejects invalid development references and
keeps reference binding separate from receipt qualification and task admission.
All dossiers retain unknown exposure and null frozen thresholds. No separate
human custodian is required, but trusted data separation and qualified protected
execution remain required.


The [solar input increment](implementation-plans/part-5-solar-input-increment.md)
adds support-aware average coarsening, causal bounded-age sample holding and
interval-energy integration for normalized records. A separate driver mask keeps
valid weather continuous when AC labels are missing. A common score mask and
explicit gap/segment warmup govern labels. Separate preparation claims and
private-first/public-last manifests keep reserved labels and future drivers out
of public files. This is authored preparation evidence, not site or private-runtime
admission. Actual source timing, equipment mapping and model/scorer bindings
remain unqualified.


Verified solar bundle readers now enforce sealed chronology, role masks, warmup,
energy and exact public forcing replay. The public reader opens only public files;
the reserved reader requires a trusted caller and grants no access authority.
The [solar input increment](implementation-plans/part-5-solar-input-increment.md)
records 85 passing tests and an installed 228-source copied-input wheel on native
macOS with relocated authored bundles. No dependency installation, actual data,
model, fitting, scoring or provider calls occurred. The first wrong-directory
build was excluded and never installed. All 224 core and 315 frozen guest sources
remain unchanged. Source, exposure, scientific and private admission stay open.
The full Part 5 goal remains incomplete.


The solar source metadata reviewer now resolves the documented `sensor_name` CSV
header and verifies AC units, aggregation, identity conversion and explicit device
keys. It refuses ambiguous identities and retains absent equipment joins as
blockers. The pinned 2107 source still cannot supply a qualified hardware mapping.
The [solar increment](implementation-plans/part-5-solar-input-increment.md)
records 102 passing related tests. The official DOE walkthrough also exposed four
public November 2017 example rows, now recorded without values in the exposure
register. No proposed-period observations or observation CSV were accessed.
Models, fitting, scoring and provider calls did not run. All 224 core and 315 frozen
guest sources remain unchanged. No task or private-runtime admission changed.


One actual authored guest-to-fixed-scorer chain completed through the production
composite service: two containers, one inference start and one scoring start, no
fitting or provider calls. Both original containers were observed absent. The score
matches independent arithmetic on public predictions, and saved confirm/recovery
reused it. A guarded fresh reader reconstructs the one score and both stages of
costs from 103 public files. The inference guest uses local ARM64 emulation for
amd64; the fixed scorer is ARM64. This is neither independent x86 hardware nor
private-runtime admission. The [execution evidence](../examples/utility/verification-guest-composite-actual-v1/README.md)
keeps the prepared caps, original receipts, failed setup/read attempts and checks.
The cumulative accounting successor is `guest-qualification-accounting-v5.json`.
The four adverse-output cases and full independent Part 5 comparison remain open.


The unchanged guest now has actual finite-input numeric-overflow evidence. The
frozen Hamon worker received a changed authored inference suffix while retaining
all selected-prefix rows and the exact fitting prefix. It returned `model_failure`
without arrays or predictions, cleaned its original container and replayed without
new execution. One inference start remains charged; no fitting or scoring ran.
The two-start parent reservation remains unfinished and model time stays unknown.
The [numeric-control evidence](../examples/utility/verification-guest-numeric-control-v1/README.md)
records 73 passing related tests and guarded cold failure replay from 96 public
files. Evidence map v7 leaves three adverse-output cases open: physical veto,
oversized stdout and malformed stdio. Accounting v6 preserves all earlier uncertain
work. All 224 core and 315 frozen guest sources remain unchanged. No private-runtime,
independent-data or overall Part 5 completion claim is supported.


Two separately named output producers now have actual local-daemon evidence through
the production readers: malformed result magic was rejected, and an actual stream
crossing the stdout bound was rejected. Both original containers were cleaned up.
These are diagnostic starts, not model/scientific starts. No frozen image or normal
inference command allowlist changed. The [output evidence](../examples/utility/verification-guest-output-diagnostics-v1/README.md)
records 166 passing related tests, caller-pinned offline reconstruction and guarded
cold replay after explicit checkout initialization. Setup refusals and failed
fixtures remain preserved. Evidence map v8 leaves physical veto without actual-daemon
evidence and keeps all three literal fixed-worker cases open. The original full
proposal and runtime/private admission remain incomplete. Accounting v7 retains
30 creations and 24 starts while preserving all earlier scientific charges and
uncertainty. The Part 5 real-task comparison remains unexecuted.


The [WIND source increment](implementation-plans/part-5-wind-source-increment.md)
adds a conditional, read-only range reader restricted to 2007-2011. One HEAD and
14 GETs inspected 2007 source metadata using 917,504 body bytes. Exact range hashes
and opaque ETag consistency pins are preserved, without claiming a full-object
hash. Captured ranges reproduce the metadata offline with no new HTTP requests.
No weather dataset values were indexed, but adjacent raw 2007 bytes may be present
in those ranges, so the exposure register records their acquisition. No reserved
year, model, fitting, scoring or LLM provider was accessed. Nineteen optional HDF5/range
tests passed; base checks passed 56 with one expected h5py skip. Actual point
extraction needs a new profile for the observed 2 MB chunks and qualified grid,
time, fill/scaling and direction semantics. The provider documents a 2014 physics
change, which remains a comparability blocker. No task or independent protocol was
admitted, and all 224 core and 315 frozen guest source files remain unchanged.


One actual 2007 WIND development point is now acquired through a separately pinned
large-read profile. A geographic-only scan of all 2,488,136 coordinates selected a
cell about 283.79 m from the proposed point, before either weather stage started.
The three stages used 175 requests and 137,311,517 body bytes. All 8,760 hourly
speed/direction rows pass the predeclared raw-fill/domain checks. The [point evidence](../examples/utility/verification-wind-point-2007-v1/README.md)
contains the compact public raw/decoded data and request/accounting metadata.
Neighbouring raw chunks remain in the local acquisition cache and are recorded as
exposed. Full cached-source replay reproduces geography and every point array;
a separate compact guarded reader verifies decoding/calendar/accounting without
HDF5 or the raw cache. Thirty-nine HDF5/range/controller tests passed. No model,
fitting, scoring, LLM, install or reserved-year access ran. Direction semantics,
physical binding, other years, protected scoring and independent admission remain
open. Frozen core/guest sources and task thresholds remain unchanged.


The [2007 hourly wind development check](../examples/utility/verification-wind-hourly-2007-v1/README.md) completed two wake calls
and one curve-reference call. Direct/wrapped scalar outputs agree, including
30.107811267852263 GWh for the fixed square baseline. The explicit 80 m hardware
uses all hourly pairs. Raw wind-from semantics and hourly integration remain
recorded development assumptions. No candidate improvement or private/independent
admission follows. The guarded reader checks saved parity and costs without
models. Thirty-six focused tests, 108 broader regression tests and 19 documentation
checks passed, with six optional-runtime skips in the regression. Frozen 224 core
and 315 guest sources remain unchanged. Other years, source comparability, raw
direction evidence, independent exposure and protected confirmation remain open.


The 2007 hourly wind profile now runs through the shared supervised scientific
executor and engineering study controller. One baseline and four frozen Sobol
trials completed with five charged, stopped observations and no pending work.
The baseline matched standalone parity at 30.107811267852263 GWh. The best trial
returned 30.068129320901953 GWh, so saved application of the frozen acceptance
rule retained the baseline. The 40 m corner domain is a development qualification
domain, not the final conventional recipe. Original completed replay added no work.
A guarded archive reader verifies hashes, inputs, five saved process/watchdog
receipts, outcomes and retention without models or current process inspection.
Eighty-nine related tests passed with one optional wind-runtime skip. Core 224
and guest 315 sources remain unchanged. Private execution, raw direction semantics,
other years, source comparability, independent exposure and the full Part 5 study
remain open. No task status, independent partition or absolute margin was admitted.

[Shared-controller wind evidence](../examples/utility/verification-wind-hourly-study-v1/README.md).


A source-pinned solar CSV parser now feeds the existing interval, custody and
reader path. It requires declared headers, clocks, durations, availability, units
and quality codes. Role claims commit before source access. The authored canary
case preserves reserved separation and consumed failures. Thirty-nine focused
parser tests and 93 related solar tests passed. A guarded public reader opens
neither raw CSV nor reserved artifacts. No site observations, model, fitting,
scoring, provider or dependency installation ran. Site clock/equipment facts,
independent exposure and task admission remain unresolved. Frozen core/guest
sources remain unchanged. Current inventory: `examples/utility/source-inventory-solar-csv.json`.

[CSV preparation evidence](../examples/utility/verification-solar-csv-v1/README.md).


The authored solar CSV workflow now has a bundled module example and a separately
verified 231-Python-file wheel. It prepared inputs and ran public/trusted-reserved
readers outside the checkout, with source fallback rejected. Source access followed
both role claims. The terminal guard refused an explicit reserved read in the public
phase. The CLI also completed. The 95-test regression passed. Dependencies were
inherited from native macOS; no fresh-environment, Linux, guest/private or full
installed-workflow qualification follows. Task admission and the independent study
remain open. Current inventory: `examples/utility/source-inventory-solar-csv-installed.json`.

[Installed CSV evidence](../examples/utility/verification-solar-csv-installed-v1/README.md).


New operating-scenario preparation now seals a private draw before selection and
requires the complete barrier for trusted private reading. A suite-level claim
prevents replacement draws through new output scopes. Committed private completion
can recover public publication without new entropy. The authored actual control
generated 24 input rows, refused early access and later verified private derivation;
no model output or scoring ran. Only public commitments and the authored barrier
are archived. The guarded reader requests no private source or entropy. Fifty-six
related tests passed. The original grid proposal remains unchanged and unevaluated.
The alternative source proposal is not task admission or protected execution.
Actual data hashes still need final execution-grant binding before selection.
Frozen core/guest sources and all full Part 5 gates retain their prior limits.

[Operating-source preparation evidence](../examples/utility/verification-engineering-generated-scenarios-v1/README.md).


Exact generated-source hashes now seal into a caller-pinned engineering binding
before selection. The existing scorer digest binds that record without a grant
schema change. Private opening requires the active reservation and access receipt,
then a permanent source-read intent. The authored service control read once and
replayed its constant fixture score without reopening or rescoring. One callback
start remains charged; zero model/solver calls ran. The guarded reader reconstructs
public binding/access/score identities without private data. Seventy-five related
tests passed. The fixture's scorer identifier is not a qualified native code closure.
Protected coupled-model scoring, physical checks, complete costs and real admission
remain open. Core/guest sources and the original grid proposal are unchanged.

[Exact source-binding evidence](../examples/utility/verification-engineering-source-binding-v1/README.md).


The coupled scoring kernel now evaluated a fixed 0.05 A design across 24 previously
exposed control cases. All required checks passed. The run retained 24 model starts,
390 nonlinear iterations, 6,360 component calls and 1,950 component-linearization
calls. The initial derivative-counter description was corrected from source
inspection without changing raw evidence or rerunning models. Fourteen new kernel
tests and 44 related tests passed. Metadata-only cold verification imports no
scientific runtime and reads no private inputs or outputs. This is not the complete
registered protected callback, independent confirmation or a task/gain admission.
OS deadline/RSS, full cost, installed/Linux and full Part 5 limits remain open.

[Coupled scoring evidence](../examples/utility/verification-engineering-load-scoring-v1/README.md).


The engineering load callback now connects the sealed source to the existing
confirmation service. It validates the selected model/current and reserves 24
inner model starts plus 2,400 solver iterations before source access. The actual
development control used fresh generated cases and an authored selected state.
All 24 native solves passed required physical checks, with 395 nonlinear
iterations, 6,440 component calls and 1,975 component-linearization calls. Saved
receipt replay opened no source and ran no solve. A fresh guarded reader verified
public source, receipt and work commitments without private inputs or model
execution. These cases are now recorded as exposed. Protected runtime, full cost,
real task/gain admission, installed/Linux and full Part 5 gates remain open.

[Coupled callback evidence](../examples/utility/verification-engineering-load-callback-v1/README.md).


The engineering work-cost reader now projects caller-pinned native callback
receipts into existing `CostRecord` entries. It verifies the charged grant,
selection, source binding, policy and score. Missing proof keeps costs unknown;
failed cases retain completed counters without inventing total work. Stable
physical IDs reject duplicate charging. Durable work survives a missing suite
score commit without rescoring. An installed macOS reader outside the checkout
reconstructed the preceding 24-solve counters under an active public-only guard
and rejected modified evidence. No new native solve ran. Generic process cost,
common-report ingestion, CPU/RSS, human/setup costs and all scientific admission
gates remain open. The frozen core/guest sources remain unchanged.

[Installed work-cost evidence](../examples/utility/verification-engineering-load-costs-v1/README.md).


The successor guest input package now binds 225 current core and 316 declared
Python sources. It preserves v5 non-code package data explicitly, including the
historical blocked task dossiers, and leaves the original v5 inputs unchanged.
A local installed reader reconstructs common reports with examples/frameworks
denied. The offline image context reuses the existing 49-archive cache. A guarded
reader verified a relocated context and refused a changed payload. A fresh bounded
build request is prepared, with no Docker dispatch, new model or private access.
Image dispatch waits for the active full default run. New image/runtime controls,
independent task admission and full Part 5 completion remain open.

[Successor wheel and context](../examples/utility/verification-guest-wheel-v6/README.md).


The current-source default attempt finished with 4,047 passed, 122 skipped and one
bare-python PATH failure. Exactly that case passed with the project interpreter
on child PATH and fresh bytecode lookup. All 11,997 source/configuration pins and
both core/test source sets remained unchanged. This is passing evidence for 4,048
unique non-skipped cases across two executions, not a clean single full-suite run.
The original failed JUnit/log and corrected one-case recheck remain separate.

The v6 base image and explicit-environment derivative now built from the
source-aligned 316-source wheel. One metadata container observed isolated Linux
x86-64 CPython 3.12.13 and the expected identity-module bytes, then cleanup recorded
its exact CID absent. Saved build/derivative/identity records replay with live
operations denied. The derivative and identity proofs also replay after relocation.
No scientific, fitting, scoring, private-label or provider operation ran in this
image increment. The new image remains an unqualified candidate under local
ARM64-hosted emulation. Historical controls were not transferred to it.

The cumulative explicit runtime register now lists 31 creations and 25 starts.
BuildKit internals remain excluded. Older unknown inference and synthetic-label
quantities remain unknown. Current-image resource/inference/lifecycle/private
qualification, independent task admission and the full Part 5 study remain open.

[Default checkpoint](../examples/utility/verification-current-base-v6/README.md),
[current image evidence](../examples/utility/verification-guest-image-v6/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v8.json).


Six fresh resource probes now passed against the v6 image. The observations were
OOMKilled at 1 GiB, EAGAIN at process count 16, ENOSPC at 128 MiB, EROFS for root,
ENETUNREACH for network and ENOENT for the unmounted host canary. Each original
container was confirmed absent. No scientific model, fitting, scoring, private
label, provider, image pull or host mount was used. Related tests passed 136 cases.
A guarded reader verified relocated evidence and rejected altered cleanup data.

The cumulative explicit runtime register now records 37 creations and 31 starts.
Older unknown work remains unknown. Historical controls remain bound to their
original image. The v6 inference, lifecycle and private-scoring matrix, independent
physical host qualification, task admission and full Part 5 study remain open.

[Current resource evidence](../examples/utility/verification-guest-resources-v6/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v9.json).


The v6 image now completed one frozen learned-routing inference and a same-fit
native reference. All four physical checks passed. All seven outputs agreed at
the unchanged tolerances, with maximum absolute difference about 2.13e-14. The
original container was confirmed absent. A fresh guarded reader recovered the
relocated 98-file public proof. A separate reader recomputed saved numerical
parity without model execution. Both used inherited dependencies.

A separate current-source authored fixture required one fit (27 routing rollouts,
2,160 days, cap 120) and one baseline evaluation. The baseline's physical start
quantity remains unknown. A post-fit diagnostic error recovered metadata without
refitting. The old source-bound fixture remains intact and now refuses against
the mismatched wheel before creating output or copying drivers. Neither inference
ran fitting or scoring. All inputs are exposed synthetic development fixtures.

Cumulative explicit runtime accounting now lists 38 creations, 32 starts and two
native references. Older unknown quantities remain unknown. Scoring and parent
confirmation are unattempted for the v6 run. The v6 lifecycle/private matrix,
independent physical host qualification, task admission and Part 5 remain open.

[Current inference evidence](../examples/utility/verification-guest-inference-v6/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v10.json).


Five fresh v6 lifecycle controls passed: two unstarted cancellations, cancellation
of an actually running guest before input transfer, and two producer-side lost
acknowledgments after real successful CREATE/START responses. Five containers
were created and two started. All original containers were confirmed absent.
Both starts remain charged with unknown model work/time and no observed model
result. Parent reservations remain unfinished. No new fitting or scoring ran.

Three public proof archives passed fresh relocated replay with model imports
blocked. After initialization, guards denied runtime activity, arrays, clocks,
writes and outside content reads. The archive helper's missing source snapshot
was repaired using its already pinned digest, without rerunning any control.
The related tests passed 27 cases. Runtime code did not change.

The cumulative runtime register now lists 43 creations and 34 starts, including
12 charged inference starts and two native references. Five started attempts have
no observed model result. Earlier unknown quantities remain unknown. The v6
owner/watchdog process-loss and private-scoring controls, cancellation during
model computation, independent task admission and Part 5 completion remain open.

[Current lifecycle evidence](../examples/utility/verification-guest-lifecycle-v6/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v11.json).


Four actual v6 owner/watchdog process-loss controls passed. Three exact owned owner
handles were killed with SIGKILL. A fourth owner killed its own ready watchdog
handle before START. Four containers were created and two started. Every original
container and all three recorded watchdog PIDs were confirmed absent. One result
captured before owner death replayed without a model or container restart. The
other started guest has no model capture. Both lifecycle durations remain unknown.

A 351-file public proof passed fresh relocated replay with model imports blocked
and, after initialization, processes, network, arrays, clocks, writes and outside
content reads denied. A separate changed-owner-PID proof was rejected. The focused
regression passed 73 tests. Runtime code, the existing fit and frozen criteria did
not change. No new fitting or scoring ran.

Cumulative explicit runtime accounting now lists 47 creations and 36 starts,
including 14 charged inference starts and two native references. Known model
inference starts have lower bound eight, with total work still unknown. Six
started attempts have no observed model result. The v6 private-scoring and full
matrix gates, independent physical host qualification, task admission and Part 5
completion remain open. Interruption during model computation is not qualified.

[Current process-loss evidence](../examples/utility/verification-guest-owner-loss-v6/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v12.json).


A fresh current-v6 composite completed one guest inference and one separate fixed
scorer over exposed authored inputs and synthetic labels. Both original containers
were observed absent. The score matched independent public-vector arithmetic.
Saved confirm/recover reused the original receipt. No new fitting, real observation,
provider call or retry ran. The new two-start reservation completed; older unfinished
or uncertain reservations remain unchanged and charged.

A 103-file public proof excludes the private label blob and root path. A fresh
isolated process outside the checkout used the existing installed 225-source
core-only wheel. Every installed Python payload matched current source. Before
its first suite replay, guards denied new imports, models, execution, network,
clocks, array loading, writes and outside content reads. The original receipt,
score and both stages' costs reconstructed exactly. Dependencies were inherited.
This is native macOS offline-reader evidence, with Linux amd64 inference under
local ARM64 emulation and a separate pinned Linux ARM64 scorer. No runtime or
private-boundary admission follows from this successful synthetic chain.

Cumulative explicit runtime accounting now lists 49 creations and 38 starts,
including 15 charged inference starts and two scoring starts. Known model inference
starts have lower bound nine; total work remains unknown. Six started attempts
lack a model result. The private adverse-case matrix, independent physical host
qualification, task admission and full Part 5 study remain open.

[Current composite evidence](../examples/utility/verification-guest-composite-v6/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v13.json).


A separate supplied-scenario native recipe now supports up to 24 circuit cases
without requiring a combined worst corner. It chooses the case requiring the
largest source current at the common voltage threshold, retains native coupled
SLSQP/derivatives and checks every supplied case freshly. The passive-circuit
monotonicity reduction and actual diode-option check are documented. The older
combined-corner recipe is unchanged. Exact scientific acceptance stays separate.

An authored 24-case supervised job used 35 inner solves within a 40-call cap.
Twenty-four separately reserved scientific processes then passed all original
checks. The batch retained 25 physical reservations. Saved native/scenario recovery
launched nothing and added no reservations. An isolated installed core-only
base reader verified relocated native and parent receipts, reconstructed costs
and the saved scenario mean, with models/runtime/original roots denied. The
optional environment passed 22 tests. Base/documentation checks passed 33 tests
with eight expected optional skips. No core source changed.

These cases were exposed synthetic development inputs. No proposed final grid
or private generated source was opened. The new recipe is not installed/platform
qualified and is outside the frozen v6 inference image. Task admission, protected
engineering scoring and the actual comparative study remain open.

[Robust native engineering evidence](../examples/utility/verification-engineering-robust-native-v1/README.md).


The robust supplied-load recipe now has selected-source installed execution
outside the checkout on macOS ARM64, Python 3.12.16 and inherited OpenMDAO 3.41.0.
The wheel contains all 225 core modules, seven domain modules and the exposed
24-case authored fixture. Installed and staged payloads match the wheel. A startup
hook denies original checkout content while allowing inherited dependencies.
This is a diagnostic harness, not a private execution boundary.

One native process used 35 inner solves within a 40-call cap. Twenty-four fresh
scientific processes passed strict checks. The current and mean power matched
checkout results at tolerances frozen before execution. All 25 reservations have
verified stopped receipts. Saved native/scenario recovery launched nothing.
A separate installed core-only base reader verified 385 relocated evidence files,
reconstructed costs and matched the aggregate to all committed scenario scores
with models/runtime/original roots denied after initialization.

The fixture is now bundled and explicitly known exposed in the draft exposure
register. Earlier unknown history and all blocked task admissions remain unchanged.
No independent or proposed final scenario source was opened. Linux, private
engineering scoring, a full release and the actual comparative study remain open.
The frozen v6 inference image and its separate accounting register are unchanged.

[Installed robust engineering evidence](../examples/utility/verification-engineering-robust-installed-v1/README.md).


A separate coupled-engineering dependency image now contains seven checksum-pinned
PyPI wheels on the exact v6 filesystem. Linux dependency requirements were checked
before acquisition. The bounded stage used 14 GETs, 14,243,480 archive bytes and one
local offline build. The base routing image and project wheel are unchanged.

One isolated Linux amd64 container under local ARM64 emulation evaluated 24 exposed
authored cases at the macOS control's fixed current. All powers/voltages matched
that reference in this observation, and strict voltage/residual checks passed.
Effective memory/PID/CPU/tmpfs and isolation settings were observed. The original
controller nevertheless exited nonzero because its cleanup helper tried to parse
an empty DELETE response as JSON. A separate read-only exact-CID check confirmed
absence. No DELETE, model or container was repeated. The original failure remains.

A caller-pinned stdlib-only reader verified 87 relocated original receipt/source
files, reconstructed public comparisons and rejected altered cleanup semantics.
It imported no models and contacted no runtime. This is metadata/provenance replay,
not independent OS attestation. The new environment still lacks a fixed private
packet worker, sealed-source/container callback integration and the full resource/
interruption matrix. Private admission and the independent study remain open.

Cumulative explicit runtime counts are 50 creations and 39 starts. The known
fixed-model forward-start lower bound is 33, including 24 coupled evaluations
nested in the new container. Total work and older unknowns remain unknown.

[Engineering container stage](../examples/utility/verification-engineering-container-stage-v1/README.md),
[cumulative register](../examples/utility/guest-qualification-accounting-v14.json).


A separate coupled-load worker now validates a hash-pinned, strictly bounded
24-case packet and invokes only the existing engineering kernel. A POSIX child
shares one hard-limited 16 KiB file for stdout/stderr. Only score and aggregate
work counts are exported. Invalid or truncated output yields no result. Packet
source-binding hashes do not themselves authorize source access.

Final interoperability checks passed 36 tests, including 24 exposed authored
OpenMDAO solves. An earlier 24-case development check also ran. These 48 model
starts are recorded separately from the unchanged v14 guest accounting scope.
No new containers ran, and no real or proposed confirmation sources were opened.
The frozen v6 wheel and dependency image do not contain this new worker.

Sealed-source access, a registered container entrypoint, versioned runtime/cost
receipts, deadlines, owner-loss cleanup and Linux resource qualification remain
open. Private admission and the full Part 5 study remain incomplete.

[Worker evidence](../examples/utility/verification-engineering-load-worker-v1/README.md).


The engineering worker now has a fixed Linux stdin entrypoint in a separate
immutable source-overlay image. It verifies its own/source hashes and effective
resource settings before reading the bounded packet. The command binds the
expected packet hash. Child numerical libraries receive only fixed single-thread
settings after the inherited environment is cleared.

One actual isolated Linux amd64 container under local ARM64 emulation completed
24 exposed authored cases. Its 0.27174569156641054 W score matched the saved macOS
reference within the frozen tolerance. The response exported no case identifiers
or forcing arrays. Exact-container cleanup succeeded. A controller binding error
before any daemon call was retained and corrected before the single start.

The copied 67-file proof passed a relocated stdlib replay with model imports,
processes, network, clocks, writes and outside file reads denied. Altered cleanup
semantics were rejected even with a recomputed test manifest. Base and related
checks passed 80 tests with one optional skip. Full lint passed. The full default
suite was not rerun.

The v15 runtime register has 51 creations, 40 starts and a known forward-model
start lower bound of 57, including 48 coupled evaluations nested in two public
control containers. Older unknown work remains unknown. Source authorization,
versioned runtime/cost registration and the worker's resource/owner-loss matrix
remain open. No sealed source was read. Private admission and Part 5 completion
remain false. The frozen v6 routing image and wheel are unchanged.

[Fixed Linux worker evidence](../examples/utility/verification-engineering-fixed-worker-stage-v1/README.md), [v15 register](../examples/utility/guest-qualification-accounting-v15.json).


The coupled-container callback and core metadata path now have versioned source,
runtime and work bindings. A registered runtime must pass preflight before the
one authorized source read. The packet binds the original grant, selected model,
source, kernel and current. Offline costs verify the sanitized worker output and
container execution against the committed score. Existing native formats retain
their cost IDs and behavior. Recovery uses the original completion pin and never
refreshes changed work bytes, reopens cases or calls runtime preflight.

The current callback also persists preflight intent, completion or refusal before
private reading. A daemon identity refusal records only validated expected and
observed digests. Other failures retain a fixed unclassified reason without
exception text. Refusal consumes the original attempt and does not make actual
cost quantities zero. A [later development attempt](reviews/part-5-engineering-preflight-refusal.md)
stopped because the daemon profile changed. It retained charges and was not
rerun after this reporting repair. Historical daemon-specific execution evidence
does not automatically qualify the changed daemon.

The focused suite passed 133 tests and full lint passed. An installed core-only
226-module wheel reproduced CLI report/verify and JSON/Markdown accounting under
model/example import and runtime/file-access guards. The integration runtime was
an authored double. No new physical model or container ran, and the v15 register
is unchanged. These checks do not qualify actual runtime enforcement. A reusable
live owner still needs to connect the new callback to the saved Linux worker.

Current core source now differs from the frozen images: load_costs.py changed and
load_container_costs.py is new. Those image/wheel bytes are preserved. Source and
runtime admission, resource/owner-loss qualification and the independent utility
study remain open. Full cost evidence and Part 5 completion remain false.

[Container callback evidence](../examples/utility/verification-engineering-container-callback-v1/README.md).


The generated-source coupled callback now uses a reusable explicit local container
owner. A versioned transport pin covers the CLI, Unix endpoint, daemon profile and
helper sources. The owner checks the fixed image before source access, sends the
bounded packet through stdin and requires exact-container cleanup. It does not
save a plaintext packet file. Ordinary lifecycle work shares a 60-second deadline.
Owner-loss supervision remains unqualified.

One actual Linux container under local ARM64 emulation evaluated 24 fresh cases
sealed before authored selection. The fixed 0.05 A current produced a feasible
0.24701566460811183 W aggregate, with 388 solver iterations, 6,328 component calls
and 1,940 component linearizations. A prespecified score-publication fault was
recovered from the original pin with further runtime/source access blocked.
Saved replay added no events. The source is now exposed and excluded from
independent confirmation. This was not optimization or a comparative utility test.

The focused suite passed 115 tests and full lint passed. An installed 226-module
core-only wheel reconstructed the actual report/verify and cost data under guards.
The public archive excludes generated forcing rows and seed. Original execution
receipt joins passed outside the checkout, and altered cleanup was rejected.
The v16 register has 52 creations, 41 starts and a known forward-model-start lower
bound of 81, including 72 coupled evaluations. Older unknown work stays unknown.

Resource/owner-loss qualification, independent host coverage, real task admission
and the independent study remain open. Full cost evidence and private admission
remain false. Frozen image/core snapshots were preserved. The full default suite
was not rerun for this increment.

[Live coupled confirmation evidence](../examples/utility/verification-engineering-container-live-v1/README.md), [v16 register](../examples/utility/guest-qualification-accounting-v16.json).


The coupled owner now arms an independent owner-pipe watchdog after container
acknowledgment and before START. Cleanup checks exact original ownership, uses a
separate lock and has no creation, start or model operation. Normal completion
also requires the watchdog's own absence observation.

Two actual SIGKILL controls passed after readiness: unstarted, and running before
input. In both, the watchdog removed the original container and exited. Exact
container and recorded watchdog PID absence were separately observed. No packet
or source was submitted. The focused suite passed 74 tests and full lint passed.
The v17 register has 54 creations, 42 starts and the unchanged known model-start
lower bound of 81. Unknown work remains unknown.

Pre-acknowledgment creation loss, loss during computation, watchdog loss and the
full resource matrix remain unverified for this owner. The earlier live source
confirmation used the preceding owner implementation. These controls establish
no new scientific result or complete runtime qualification. Private admission
and the full Part 5 study remain open.

[Coupled owner-pipe evidence](../examples/utility/verification-engineering-owner-loss-v1/README.md), [v17 register](../examples/utility/guest-qualification-accounting-v17.json).


The coupled owner now monitors watchdog liveness before dispatch, during transport
and process-exit waiting, and after client completion. A lost supervisor revokes
result authority. Valid output cannot be published after watchdog loss, and the
owner still cleans the exact original container.

Two actual watchdog SIGKILL controls passed with the owner alive: ready before
START, and running before input. The owners detected loss, refused result
publication, removed the original containers and rejected watchdog completion.
Exact container and recorded watchdog PID absence were separately observed. No
packet or source was submitted, and no model result was observed.

The focused suite passed 77 tests and full lint passed. The v18 register has
56 creations and 43 starts. The known model-start lower bound remains 81, with
72 coupled evaluations. Unknown work stays unknown. Core and frozen image bytes
were preserved. The full default suite was not rerun.

Loss during computation, pre-acknowledgment creation loss and the full resource/
interruption matrix remain unverified. Earlier controls retain their original
helper versions. Runtime/private admission and the independent study remain open.

[Watchdog-loss evidence](../examples/utility/verification-engineering-watchdog-loss-v1/README.md), [v18 register](../examples/utility/guest-qualification-accounting-v18.json).


The current supervised coupled owner now has a complete live development
confirmation using a fresh generated source sealed before authored selection.
One source read and one container produced 24 feasible model evaluations at the
fixed 0.05 A current. The aggregate was 0.24921646466397246 W, with 390 solver
iterations, 6,360 component calls and 1,950 component linearizations.

Parent cleanup and normal watchdog disarm were both observed. The watchdog
independently confirmed absence and exited without a second DELETE. A
prespecified score-publication fault was recovered from the original pin with
further source/runtime access blocked. Saved replay added no events. The source
is exposed and excluded from independent confirmation, and its result is not a
utility comparison with earlier generated draws.

A 68-file public archive excludes forcing rows, seed and packet. Receipt joins
passed outside the checkout and rejected altered normal disarm. The existing
226-module installed core reconstructed report/verify and cost data under guards
without another build or installation. Current code/tests match the preceding
77-test checkpoint by hash. No full default suite was rerun.

The v19 register has 57 creations, 44 starts and a known model-start lower bound
of 105, including 96 coupled evaluations. Unknown work stays unknown. Creation
acknowledgment loss, interruption during computation and the full resource matrix
remain unverified. Independent host coverage, real task admission and the
independent study remain open. Full cost evidence and private admission are false.

[Current supervised confirmation](../examples/utility/verification-engineering-supervised-confirmation-v1/README.md), [v19 register](../examples/utility/guest-qualification-accounting-v19.json).


The coupled watchdog now arms for the original prospective name before CREATE.
The owner must publish the acknowledged CID and receive a verified watchdog
binding before START. Existing known-CID plans retain their earlier schema.
An intent without an observed object stays unverified.

Four live controls passed their prespecified outcomes: owner loss before CREATE,
owner loss after daemon creation before CID binding, intent-only uncertainty and
normal CID binding/disarm. Two containers were created, none started. Three exact
owner PIDs were killed. Both observed CIDs and all four watchdog PIDs were
separately observed absent. No packet or source was submitted. The intent-only
watcher correctly refused to call current absence a confirmed creation outcome.

The focused suite passed 82 tests and full lint passed. The v20 register records
59 creations, 44 starts and the unchanged known model-start lower bound of 105,
including 96 coupled evaluations. Unknown work stays unknown. Core and frozen
image bytes were preserved, and the full default suite was not rerun.

Unbounded daemon delay, interruption during computation and the full resource
matrix remain unqualified. Earlier scientific controls retain their original
helper versions. Runtime/private admission and the independent study remain open.

[Prospective creation supervision](../examples/utility/verification-engineering-creation-watchdog-v1/README.md), [v20 register](../examples/utility/guest-qualification-accounting-v20.json).


Eight fresh fixed diagnostics now passed on the exact coupled image, with owner
code and production catalogues unchanged. Memory reached OOMKilled/exit 137 at
1 GiB, process creation reached EAGAIN at 16 PIDs, and scratch reached ENOSPC at
128 MiB. Root, network and the unmounted host canary returned EROFS, ENETUNREACH
and ENOENT. Two fixed-worker probes also observed the shared 16 KiB stdout/stderr
cap, including SIGXFSZ on overrun. No child bytes became a score.

All eight original containers were confirmed absent. No scientific packet,
source read, model evaluation, image build or installation was involved. These
were fixed diagnostic entrypoints on the exact image, not the scientific scoring
path. Effective CPU quota was observed, but CPU saturation and model RSS were
not measured. Existing source/test checkpoints were preserved.

The v21 register has 67 creations and 52 starts. The known model-start lower bound
remains 105, including 96 coupled evaluations. Older unknown work stays unknown.
Scientific-owner interruption/resource qualification, independent physical host
coverage, task admission and the independent utility study remain open.

[Exact-image resource/output evidence](../examples/utility/verification-engineering-image-resources-v1/README.md), [v21 register](../examples/utility/guest-qualification-accounting-v21.json).
