# Part 5 consolidated audit and stopping rule

Latest [execution preparation](../../examples/utility/consolidated/README.md): CAMELS, solar and all wind
periods staged; numeric baseline gains bound; selection supervisor and common
engineering confirmation implemented. Final integration remains incomplete.
The saved live-host qualification artifact is missing. No confirmation score ran.

Latest qualification: [consolidated result](../../examples/utility/consolidated/qualification.json).
Four concrete TaskSpec definitions are bound and the user attested no prior
inspection or use of PVDAQ 1278 measurements from 2013. The single consolidated
pass completed 281 tests with no failures or skips. Dispatch qualification is
incomplete: source staging, executable suite/worker bindings and the baseline/
execution freeze remain. These are implementation gaps, not requests for
another exposure answer or another control matrix.

Latest decision: the user authorized a reasonable workaround and continuation.
The [selection-cost amendment](#selection-cost-amendment-and-continuation) below
supersedes the wind-related stopping decision. The legacy scorer remains strict;
the new opt-in profile separates matched selection cost from common confirmation
work. Preparation has advanced to an explicit 90-cell design.

Current execution outcome: the admission pass resumed with PVDAQ 1278 and reached
a different, concrete stop: the existing annual wind scorer rejects the required
fixed-total-cost regime. See the [resumed admission result](#resumed-admission-result-after-solar-replacement).
Solar equipment mapping is not the current reason for stopping. The 90-cell
protocol and its scientific execution have not been frozen or dispatched.

Status: the original admission pass ended blocked; the subsequent user-authorized
[equipment hypothesis and replacement check](../../examples/utility/development/solar-mapping-v1/README.md)
has selected PVDAQ 1278 as the replacement solar development task. Waiting for
provider-confirmed site 2107 joins is no longer a prerequisite. The 1278 screening
passed after one documented development calibration amendment; no full-suite or
independent-confirmation admission is implied. The original decision below is
retained as history, not an instruction to stop this authorized replacement.

The user's instruction to execute this plan resumed the admission review. Step 1
has reached its stopping condition. Steps 2-5 were not started. No frozen records,
acceptance criteria or historical results were changed. See the
[executed admission decision](#executed-admission-decision).

The implementation effort has overemphasized repeated runtime controls and
incremental archives. Those controls establish useful bounded facts, but cannot
substitute for four admitted scientific tasks and an executed comparison. The
next decision must be whether the four tasks can support a finite study. Further
runtime refinement is not the default next step.

This is the current decision summary. The older admission page and completion
audit retain chronological evidence, including superseded blocker statements.
The requirements below come from the [development plan, Part 5](../development-plan.md#5-establish-utility-across-real-examples)
and the [detailed plan](../implementation-plans/part-5-utility-confirmation.md).
Interpretations and proposed scope choices are identified explicitly.

## Requirements versus added caution

| Topic | Actual plan requirement | Consolidated decision |
| --- | --- | --- |
| Four domains | Sections 2 and 7.7 require observed hydrology, measured solar, coupled engineering and wind/hybrid. A missing family leaves the full study incomplete. | Indispensable. An incomplete or blocked report is an honest terminal deliverable, not completion of the four-domain experiment. |
| Comparisons | Section 3 requires baseline, conventional, single-agent and multi-agent routes, equal choices/information, paired stochastic runs and two budget regimes. | Indispensable. Scripted workers cannot supply evidence of actual agent utility. A negative or inconclusive result is acceptable. |
| Study size | Ten repetitions is explicitly a planning default. Smaller exploratory studies and a preselected ablation subset are allowed. | The proposed 480 adaptive cells are not a minimum. Choose a small matrix once, before confirmation. Do not expand it in response to results. |
| Optional arms | Learned hydrology is conditional on data/capabilities. Expert workflow is required only where practical. Discovery is separate and initially uses trusted supplied implementations. | Record unsupported learning and unavailable expert work. Defer generated-model discovery. These are not reasons to keep all four tasks waiting. |
| Custody | Sections 2 and 4 allow trusted preparation and scoring. Advisory workers must not obtain reserved labels or scenarios through their admitted boundary. | A separate human custodian and a previously existing private dataset are not required. Predeclared quality preparation does not by itself destroy independence. Record access and prevent feedback into selection. |
| Runtime recovery | G5 explicitly requires interruption, cancellation, owner-loss, tampering and leakage checks, with charged uncertain attempts and no automatic retries. | These are real requirements. Map existing tests to the exact chosen execution path. Test only a named uncovered contract or changed dependency. An unlimited matrix of fault combinations, every daemon timing possibility, or re-proving unrelated controls is added caution. |
| Platforms and hosts | G6 requires evidence for release claims, but expressly permits scientific reporting with macOS-only or one-host limits. | A second host and independent Linux qualification are deferred release scope, not prerequisites for a bounded one-host scientific report. Emulation is reported as emulation. |
| Cost | Sections 3 and 6 require bounded dispatch and honest accounting. CPU/RSS are reported where measured; unknown money prevents matched-money claims. Incomplete physical evidence prevents a complete-cost verdict. | Preserve old unknowns and failed charges. They do not invalidate a new scientific comparison merely by existing. Measure prospective study cost, separate historical integration effort, and withhold complete-cost, monetary-efficiency or amortization claims where unsupported. |
| Source semantics | Sections 2 and 7.3 require interpretable units, time/state handling, physical checks and direct/wrapped parity. | Establish semantics needed by the declared claim. Exhaustive upstream lineage is not an end in itself. A benchmark on published daily rows may state unresolved physical timing as a limitation; a subdaily physical-alignment claim cannot. Any changed task interpretation needs a successor dossier before selection. |
| Packaging | G6/G8 require installed offline reconstruction and traceable evidence. Section 8 says to rerun existing checks when affected. | Keep one final source inventory and evidence index. Reuse compatible installed-reader evidence. A new wheel, archive, tampering variant and full regression after every metadata update are not required. |
| Provenance | G7 requires clean source provenance under the new protocol. Existing development is dirty and remains traceable by inventories. | Prepare an isolated, immutable execution snapshot without altering the dirty worktree. Document how it satisfies the protocol; do not equate an uncommitted inventory with clean provenance or make commit/push authority implicit. |

No runtime admission flag is changed by this audit. Narrowing a threat model or
claim must be explicit and implemented before execution, not achieved by ignoring
an existing refusal. Agent processes remain unable to access confirmation files
even when all scientific implementations are trusted and supplied.

## Evidence that should be reused

- The [prior-use attestation](part-5-reserve-exposure-attestation.md) resolves the
  user's personal prior use of all three named reserves. Do not ask it again.
  Other actual exposures remain in the register; universal proof that nobody has
  ever seen a public dataset is not the scientific requirement.
- [CAMELS acquisition and preparation](part-5-camels-actual-source.md) establish
  archive/member identity, published rights metadata, coverage and the A-only
  quality counts. Actual records carry hour 12. Earlier claims that the archive
  has not been acquired or verified are obsolete.
- [Engineering development](part-5-engineering-development-reference.md),
  [conventional profiling](part-5-engineering-conventional-profile.md) and
  [controller supervision](part-5-engineering-envelope-supervision.md) establish
  the revised model question, baseline and executable native comparison.
  [Current-owner execution](part-5-engineering-current-owner.md) closes the normal
  scientific-path gap on its pinned runtime. It does not complete G5, and its
  fresh generated source is development evidence, not independent confirmation.
- [Wind direction evidence](part-5-wind-direction-source-review.md) supports the
  direction interpretation as an inference. The annual kernel, custody and cost
  readers are implemented. The [NetCDF experiment](part-5-wind-netcdf-environment.md)
  was not promoted. Rebuilding it repeatedly is not a scientific study prerequisite
  unless the selected executable path actually depends on the unresolved behavior.

These are findings from the existing records inspected for this audit. No model,
container, acquisition, failure injection or regression suite was run anew.

## Indispensable remaining facts and decisions

| Domain | Minimum remaining admission decision | Stop condition |
| --- | --- | --- |
| Hydrology | Freeze a published-date, no-shift/no-fill benchmark interpretation or substantiate a stronger interval claim. Bind warmup/state carryover, masks, units and conservation outputs; demonstrate the chosen adapter and conventional baseline on development rows. Bind a positive baseline loss to the useful-gain threshold. | If a scientifically defensible daily benchmark and physical accounting cannot be specified without guessing transformations, mark hydrology blocked. Do not keep searching for complete Daymet history merely to improve provenance detail. |
| Solar | Identify which measured AC channel and equipment the POA-driven model predicts, with units, rating/physical limits, timestamps, interval durations and daylight-saving handling. These are needed for RMSE and integrated-energy checks. Bind usable development/reserve files and source notices. | Site 2107 currently lacks the required joins and timing contract. Naming similarity is insufficient. If these cannot be established in the bounded admission pass, block solar. Do not silently substitute another site or use fabricated equipment. |
| Engineering | Adopt one successor definition based on the engineering-v3 domain and conventional recipe. Freeze the scenario generator/distribution, a genuinely unused reserve and actual native/solver caps. Decide the application of physical feasibility separately from the stricter optimizer buffer. | Block if the chosen driver, scoring path or custody contract cannot be qualified with existing evidence plus a bounded repair. Do not compare different generated cohorts as though they establish gain. |
| Wind | Bind the selected years' source bytes, point/height, units and direction convention to fixed geometry and hardware. Use the existing annual records to report source-version strata. Verify the chosen production reader on development data and establish its baseline and runtime estimate. | Block if the necessary source semantics, usable reader or protected scenario path cannot be established. Identical weather generators across all years are unnecessary for a clearly labeled scenario-robustness claim; homogeneous-climate claims would need more evidence. |

Across all four, still needed are a concrete shared candidate pool, the exact
host/profile for real agent routes, a complete cell matrix, numeric enforced caps,
selection/scoring bindings, and the predeclared uncertainty and failure policy.
There is no admitted `examples/utility/protocol.json` yet. General approval does
not fill these scientific fields, but it also does not require repeated approval
questions for ordinary local preparation.

Use the existing proposed gains as study-design choices, not as missing
owner-supplied facts: 5% of development-baseline loss/power for hydrology, solar
and engineering, and 1% of baseline energy for wind. Freeze absolute values from
the matching development receipts. The engineering-v3 reference already gives
0.012487250213233526 W. It must not be transplanted into another scenario definition.
Use the existing proposed secondary tolerances unless a documented scientific
defect requires a pre-confirmation amendment: hydrology 10% absolute volume bias
and 2 percentage points degradation; solar 5% daytime energy bias and 1 point
degradation; engineering all-case voltage/residual feasibility and 1% worst-case
power degradation; wind spacing/geometry and 2% annual energy degradation.
These are not yet executable frozen acceptance rules.

## Finite route to a terminal outcome

The following is the recommended continuation when the study is resumed. These
are workflow ceilings, not scientific-run authorization or invented runtime caps.
Write outcomes into this audit and the final protocol, rather than creating a new
archive series for each small check.

1. __One admission pass, at most four hours of active work.__ Review only the
   missing facts above against already saved evidence and, if resumed within
   authorized scope, specifically named source metadata. Produce one four-row
   admitted/blocked table and one requirement-to-evidence map for G2-G6. Do not
   rerun controls during this pass. If any required domain remains blocked, stop
   full-suite preparation and deliver the blocked outcome below. No open-ended
   source search, automatic task replacement or background controls.
2. __One protocol package.__ If all four definitions are defensible, freeze the
   supplied pool and a small exploratory design: three paired repetitions, both
   budget regimes and three adaptive primary routes across four tasks gives
   72 adaptive cells. Three engineering-only role ablations add 18 cells, for
   90 adaptive cells plus baseline references and confirmation work. The final
   matrix must enumerate all of those operations. Three repetitions support
   descriptive exploratory findings, not reliable equivalence or general
   superiority. Ablation conclusions apply only to engineering. Freeze the exact
   dependence-aware analysis and multiplicity policy before access; no adaptive
   increase in repetitions after confirmation.
3. __One consolidated development qualification pass.__ Reuse existing compatible
   evidence first. List every missing assertion with its plan clause, affected
   path and acceptance condition. Permit at most one rehearsal for each distinct
   admitted task path and one correction cycle for a demonstrated defect. Set
   numerical start/time/provider/storage ceilings before those rehearsals using
   existing profiles. If caps cannot be set, the route is blocked. Finish the
   requirement map and freeze the full study caps, including confirmation. A
   remaining G3-G5 defect after the correction cycle blocks execution. Do not
   manufacture a new source/grant to retry a consumed uncertain attempt.
4. __Execute the fixed matrix once.__ Only after resume and any genuinely missing
   live/paid/remote authority, run selections under the frozen caps, seal all
   cells including failures, and open confirmation once through the trusted
   scorer. No candidate, threshold, mask or analysis repair from confirmation
   feedback. Preserve terminal failures and charges; use saved evidence for
   permitted recovery. Do not replace a failed cell with an unplanned new one.
5. __One final delivery and verification pass.__ Produce the domain results,
   paired differences, feasibility/failure denominators, cost tables and plots
   from original receipts. Run applicable regressions once for the final changed
   implementation and one installed offline reconstruction. Reopen only a
   demonstrated defect that changes a reported conclusion or mandatory contract.
   Deliver supported, adverse, inconclusive and blocked findings separately.

This design reduces the unfrozen 480-adaptive-cell proposal to 90 while retaining
the four primary domains and both budget regimes. It is a proposed successor
protocol, not a retrospective change to any frozen experiment. Omitting a budget
regime, replacing measured solar with a synthetic case, or omitting actual agent
routes would change the central scope and must be reported as such.

__Current blocked outcome:__ no four-domain independent comparison exists.
Solar's channel/equipment and time-support facts are a concrete unresolved blocker.
Hydrology needs a defensible task interpretation, engineering needs final reserve
and execution admission, and wind needs exact source/execution bindings. G2-G5
have substantial scoped implementation evidence but no consolidated final study
qualification. G6 retains platform/host release limits. G7 has not run; G8 has no
four-domain results to reconstruct. No agent advantage or role-retention benefit
has been demonstrated by these controls.

If the admission pass or qualification pass stops, deliver this named blocked
outcome with the exact missing fact/contract and the evidence needed to reopen
it. Leave experiments stopped. Existing engineering and development results can
be reported under their original limits, but must not be renamed a completed
four-domain utility study. This is a finite, acceptable audit conclusion even
when the scientific plan remains incomplete.

## Executed admission decision

Reviewed against checkpoint `11815e3d44ee142562491cb9a3e5b8611915c55a`.
The four-hour allowance is a ceiling, not a minimum. The saved source evidence
is sufficient to reach a named blocker without spending that allowance on more
searches or controls. This pass inspected metadata, implementation test coverage
and existing execution records. It ran no scientific models, provider calls,
containers, acquisitions or fault controls and opened no private labels.

The solar metadata file was rehashed and matches the saved identity
`17e4f7f448fcb2bec43f7610b40c1f7f4fc794ccc185e41dcde0514afba73ae5`.
The [selected-channel record](../../examples/utility/verification-solar-equipment-v1/selected-ac-review.json)
has metric 149583, kW units, no inverter ID and no module IDs. The
[saved regular-table counts](../../examples/utility/verification-solar-equipment-v1/regular-table-counts.json)
contain zero site 2107 rows among 165 inverter and 166 module records.
The [interval review](../../examples/utility/verification-solar-interval-source-v1/source-review.json)
establishes left alignment, but neither individual interval duration nor DST
handling. These observations establish the saved metadata's limits, not that
no better metadata can exist elsewhere. No new authoritative mapping was supplied
or identified in the reviewed records. Repeating those same metadata requests is
not needed to make the present decision.

| Domain | Admission outcome | Decision and indispensable remaining evidence |
| --- | --- | --- |
| Hydrology | Blocked for execution; scientific interpretation selected | Use CAMELS on published daily dates and its literal hour field, without shifting or filling data. Restrict claims to that published product; reconstructing all legacy Daymet transformations is unnecessary. Reuse the [actual source checks](part-5-camels-actual-source.md) and personal attestation. A successor execution dossier still needs exact warmup/state carryover, conservation outputs and a matching basin 01491000 development baseline. These were not fabricated or executed after the solar stop. |
| Solar | Blocked; decisive full-suite stop | The measured-POA-to-AC question cannot bind the selected channel to a defensible model specification and physical rating, or integrate variable sampling under a known clock policy. Need an explicit channel/equipment association or independently documented equivalent model specification, plus timestamp/DST and interval-support metadata. Naming similarity and generic timezone/interval codes cannot supply those facts. |
| Engineering | Blocked for execution; development definition selected | Use the engineering-v3 envelope and registered native recipe, with physical voltage/residual feasibility distinct from the stricter optimizer buffer. Reuse the [actual controller comparison](part-5-engineering-envelope-supervision.md), its baseline and observed native work. Final reserve identity, suite caps and admitted scoring boundary are missing. No new reserve was generated; consumed development sources remain excluded. |
| Wind | Blocked for execution; scenario interpretation selected | Use annual modeled-energy robustness with fixed hardware/layout constraints and explicit source-version strata. Accept the [direction trace](part-5-wind-direction-source-review.md) as a documented inference, not direct provider attestation. Identical source generators and NetCDF rebuilding are not standalone requirements. Exact reserved-year source/point bindings, the production reader path, matching development reference and protected execution remain missing. |

These review decisions do not mutate the historical four `blocked_draft`
dossiers. Their null confirmation partitions were checked again. Their older
personal `unknown_exposure` entries are superseded by the recorded no-prior-use
answer for the three named reserves. That question is closed. No admitted
`examples/utility/protocol.json` exists.

### G2-G6 requirement-to-evidence map

Test sources below were inspected for coverage, not executed in this pass.
Execution records report their own historical runs and source identities. An old
passing run is not a claim that the current tree was retested. A domain admission
failure does not erase implemented software.

| Gate and mandatory contract | Existing evidence to reuse | Remaining acceptance condition and disposition |
| --- | --- | --- |
| G2: immutable matrix, parent budget and more than 32 cells | [Contracts](../../tests/test_utility_contracts.py) cover paired identities/caps; [store](../../tests/test_utility_store.py) covers permanent reservations and resumed identity; [controller](../../tests/test_utility_controller.py) contains the 40-cell dispatch and uncertain-start cases. The [baseline checkpoint](../../examples/utility/verification-baseline-selection-v1/README.md) records a 34-cell execution across the child boundary. | Scoped implementation evidence exists. Final matrix expansion and numeric budget reconciliation await four admitted tasks. No need to repeat generic boundary fixtures now. |
| G2: physical costs and recovery compatibility | [Cost tests](../../tests/test_utility_costs.py) cover shared receipts, missing quantities and changed evidence. Baseline records preserve reuse without fresh execution. [Wind cost integration](part-5-wind-cost-report.md) and engineering records preserve actual inner work separately. | Bind final host, native, training and scoring quantities to chosen study operations. Preserve old unknown costs separately; do not require reconstruction of every historical resource measurement. |
| G3: outcomes, parity, conventional comparator and physical vetoes | [Engineering supervision](part-5-engineering-envelope-supervision.md) records native selection and fresh physical checks. [Native annual wind](part-5-wind-annual-native.md) records authored-driver execution. Solar tests establish refusal behavior, not site validity. CAMELS preparation establishes schema checks, not a basin model comparison. | Engineering development is supported within its recorded scope. Solar semantics are blocked; hydrology/wind need admitted data and matching development paths. Full four-domain G3 is not satisfied. |
| G4: matched routes, ablations, pause/resume and capped proposal | [Route tests](../../tests/test_utility_routes.py) cover equal grants, omitted-role replacements, paired order and changed-host refusal. Controller/store coverage preserves charges and child results across interruption. | Select the actual host/profile and supply all frozen cells and numeric caps. The proposed 90 cells are not an executable protocol. No four-domain live rehearsal or agent comparison was established here. |
| G5: selection barrier, access-before-read and no rescoring | [Barrier tests](../../tests/test_utility_confirmation.py) cover complete selections, pending work, parameters and immutable artifacts. [Recovery tests](../../tests/test_utility_confirmation_recovery.py) preserve original results and uncertain charges. [Private-access evidence](../../examples/utility/verification-private-access-v2/README.md) distinguishes stubbed tests from OS protection. | Contracts have implementation evidence. The final scorer must bind admitted tasks, data and selected objects; generic tests do not admit a source/runtime pair. No need to rerun every barrier/recovery variant. |
| G5: privacy, interruption, cancellation and owner loss | [Current-owner control](part-5-engineering-current-owner.md) establishes normal execution, cleanup and saved-score recovery for one pinned path. Earlier owner-loss/resource records remain scoped to their identities. | A future qualification pass must name only uncovered contracts on the chosen production path. Current registration remains unqualified; this review does not override it. Defer qualification while solar blocks the suite. |
| G6: installed offline readers and platform/host scope | [Current-owner reader receipt](../../examples/utility/verification-engineering-current-owner-v1/reader-verification.json) records installed-core reconstruction with 235 payloads verified, no model/private-source calls and no rebuild. Earlier baseline records include installed fixture run/resume/freeze. | Reuse those reader facts. Final study reconstruction is prospective. Second-host and independent Linux release qualification are deferred, not blockers to one-host scoped scientific reporting. |

### Terminal disposition and reopening evidence

This disposition predates the user's explicit instruction to infer equipment
from development data and find a replacement if that fails. The linked 1278
replacement decision above supersedes the provider-metadata-only reopening rule.

Step 1 is complete with a blocked outcome. Steps 2-5 are `not_attempted` because
the full-suite admission condition failed. No protocol, archive series, runtime
patch, reserve draw or replacement task was created. Experiments are stopped
under the plan's explicit instruction: "If any required domain remains blocked,
stop full-suite preparation and deliver the blocked outcome below."

Reopen admission when source metadata establishes the selected solar channel's
equipment/model and clock/support contract, or a deliberate task amendment
selects a documented measured-solar source. The former needs metadata or file
paths, not private labels. A source amendment must preserve old evidence and
establish new exposure and scientific meaning before selection. Neither blanket
approval nor another container control supplies these facts.

After that blocker changes, the other three rows identify the remaining work;
they do not request repeated personal attestations or universal historical proof.
The 90-cell study stays prospective until admission and execution conditions are
met. No scientific gain, efficiency gain, role benefit or completed four-domain
confirmation is claimed.

## Resumed admission result after solar replacement

The user's latest execution instruction resumed the bounded admission pass using
the replacement solar example. This pass checked the four chosen definitions,
the available source metadata and the actual execution entrypoints. It did not
repeat development model runs or container controls. Existing uncommitted solar
work and earlier records were preserved.

### Source facts resolved

- A bounded, untruncated S3 listing contains 365 daily objects under
  `pvdaq/csv/pvdata/system_id=1278/year=2013/`. The objects' measurements were not
  requested. Object existence does not establish usable measurement coverage.
- Three HEAD requests returned HTTP 200 for WIND Toolkit 2012 and 2013 version
  `v1.0.0`, and 2014 version `v1.1.0`. Each source is approximately 1.54 TB.
  Full-object downloads are unnecessary; preparation needs bounded point
  extraction. Opaque ETags establish request consistency, not full-file hashes.
- CAMELS basin area 292.543553 km2, latitude 38.97, source/member hashes and
  published-date quality counts are already in the
  [saved inspection](../../examples/utility/verification-camels-acquisition-v1/inspection-v2/inspection-result.json).
  Neither another archive acquisition nor a source-lineage search is required.
- The new solar prior-use question concerns system 1278 in 2013, not the already
  answered system 2107 question. At this checkpoint its answer remains pending.
  This is separate from the decisive wind implementation gap below.

The four HTTP metadata requests and their results are recorded locally in
`outputs/consolidated-admission-v2/source-checks.json`; no new evidence archive,
private observation bundle or scientific result was created.

### Current four-task decisions

These concrete definitions replace ambiguity in the old admission narrative.
They are preparation decisions, not a dispatchable protocol or edits to the old
frozen dossier identities.

| Task | Definition accepted for further preparation | Execution admission still needed |
| --- | --- | --- |
| Hydrology | CAMELS 01491000, published daily dates and literal hour 12. Warmup 1980, fit 1981-1999, selection 2000-2004, reserve 2005-2014. A-only discharge mask; no filling or date shifts. Use the site-aware bucket/reservoir adapter with Hamon/Hargreaves PET, capacity 20-200 mm and recession 0.05-0.95. Initialize soil to half capacity and reservoir to zero, then run causally through warmup and subsequent forcing without using labels to update states. | Materialize separate development/reserve bundles through trusted preparation, bind conservation checks and measure the development baseline. The baseline is capacity 100 mm, recession 0.7 and Hamon PET. Learned-model admission is deferred rather than blocking the supplied-model study. |
| Solar | PVDAQ 1278 aggregate measured AC conditioned on measured POA, ambient temperature and wind. Use the documented two 357-module branches, 240 W modules, and 100/50 kW inverter limits. Retain the calibrated 0.701558 effective derating as a development choice, not recovered hardware. October 1-14, 2011 is exposed development; 2013 is the proposed reserve. Compare supplied thermal alternatives and bounded calibration. | Bind the new source/preparation/scorer path and its reserve exposure. Use a fixed, explicit interval mask before integrated-energy scoring. The existing 10% development screen is not the planned 5% energy-bias acceptance rule; that rule was not relaxed. The development power-bias proxy cannot certify it. |
| Engineering | Engineering-v3 source-current design, 0.01-0.1 A; ground voltage -0.02 to 0.02 V, R1 90-110 ohm, R2 9000-11000 ohm. Native SLSQP retains 20 iterations and independently counted support work. Physical minimum voltage remains 0.62 V and residual limit 1e-10 A; the 0.62001 V optimizer buffer remains a separate flag. Reuse the documented public baseline and 0.012487250213233526 W gain proposal. | Seal one unused 24-case draw under the chosen generator and original suite identity before selection. Bind final native/confirmation caps and the actual scoring runtime. Existing development draws are excluded. No new draw was made in this pass. |
| Wind | Four V80 turbines at 80 m, fixed NOJ model, 320 m minimum spacing and the declared 600 m square. Use the existing meteorological-from direction interpretation with its inference label. Compare paired annual modeled energy, retaining 2014's different source version. Reserve years remain 2012-2014 near (-70.5, 41.5). | Implement a bounded trusted reserve extractor and a registered annual execution path that supports both required regimes. Exact normalized point payloads must be sealed before selection. The existing development baseline is not a substitute for these source/runtime bindings. |

### Decisive implementation gap

This is an explicit executable restriction, not an inferred demand for more
security evidence. In
[`AnnualWindScorer._context`](../../examples/utility/wind_annual_callback.py),
the code requires `cell.regime == "fixed_evaluations"` and otherwise raises
`annual wind callback has no qualified fixed-total-cost boundary`.
The [callback tests](../../tests/test_utility_wind_annual_callback.py) include the
changed-regime refusal. Removing that guard would not implement a time budget.
The plan's mandatory second regime therefore cannot execute through this path.

Separately, [`WindObjectPin`](../../examples/utility/wind_range.py) accepts only
2007-2011 and constructs only `v1.0.0` development URLs. The
[annual source helper](../../examples/utility/wind_annual_source.py) receives
already normalized payloads; it does not acquire or decode reserved-year HDF5.
There is no basis to label the 2012-2014 extraction ready merely because HEAD
requests succeed. The old development guard must remain intact.

G2 evidence is unchanged. G3 retains the actual domain development evidence but
does not yet cover all final data bindings. G4/G5 cannot cover the complete
two-regime wind study through the current entrypoint. G6 retains its installed
reader evidence and deferred release scope. This narrows the earlier G2-G6 map
to specific source and runtime contracts instead of an open-ended control matrix.

### Stopping rule applied and finite reopening work

Under step 1, a required domain still lacks execution admission, so steps 2-5
remain `not_attempted`. No null-budget protocol or fabricated confirmation result
was created. The stop is not caused by missing provider confirmation for 2107,
the NetCDF warning alone, a second platform, or the pending solar answer alone.

The next implementation increment, if the plan is amended to permit repair
before full task admission, has two concrete deliverables:

1. A trusted reserve extractor with explicit year/version pins, byte/request
   caps and private output for the three annual wind payloads. Preserve the
   development-only extractor. Qualification can use authored/public inputs;
   do not inspect reserve values to select a favorable scenario.
2. A supervised annual wind scorer that reserves and enforces the fixed-total-
   cost wall-time budget, records terminal work and preserves original-result
   recovery. Reuse existing supervisor and cost contracts. Test the missing
   budget/interruption behavior once, with at most the audit's one correction
   cycle. Do not restart the historical container-control sequence.

After these are available, finish the four task bindings above, resolve the new
solar exposure answer, and prepare the single 90-cell protocol package. This
record identifies a finite software gap; it does not claim that a metadata
review executed the scientific study or that all four tasks are admitted.

## Selection-cost amendment and continuation

The user explicitly authorized a reasonable workaround, documentation and
continuation. Apply this prospective amendment rather than stopping on the
legacy annual callback's regime guard. No historical run is reclassified.

The second budget regime now asks: **what does each route achieve within the
same selection-time allowance?** Freeze every selection before scoring, then
give the selected results a common confirmation allocation. Report preparation,
selection, confirmation and unresolved quantities separately. The sum remains
visible, but the claim is equal selection cost, not equal end-to-end cost or
matched money. The legacy internal regime name `fixed_total_cost` is retained
for compatibility and must always be qualified by `selection_only` in this study.
This is a deliberate narrowing of the original plan's cost claim.

Implementation:

- [CommonConfirmationWindScorer](../../examples/utility/wind_common_confirmation.py)
  is a separately identified opt-in scorer. It accepts either selection regime,
  while retaining the complete selection barrier, immutable model/data bindings,
  access receipts, exact annual model/read reservations and saved-result recovery.
  Its identity includes the amended cost scope and a common 60-second active-time
  reservation. This reservation is accounting, not an OS-enforced deadline.
  Actual selection-time enforcement remains the selection controller's job.
- The legacy scorer retains its original regime refusal. The opt-in scorer
  cannot silently resume an old grant because its scorer identity differs.
  Scoring still exports false private-boundary/task-admission flags until the
  complete study bindings are qualified; accepting a selection regime does not
  invent physical resource enforcement.
- [Reserve extraction](../../examples/utility/wind_reserve_extract.py) uses a
  separate 2012-2014 pin type, with `v1.1.0` for 2014. The development extractor
  and its 2007-2011 restriction are unchanged. Each year has three stages, each
  capped at 128 range requests, 64 MiB of reserved responses and 120 seconds of
  logical elapsed time. It verifies complete UTC hours, geography, units,
  scaling and missingness, then writes normalized weather only to the trusted
  private directory. A consumed or incomplete directory cannot be retried.
  It does not download the approximately 1.54 TB source objects in full.

The [consolidated study design](../../examples/utility/consolidated-study.json)
now enumerates all 90 adaptive cells with paired seeds and randomized order:
72 primary cells and 18 engineering ablations. It records explicit planning
caps and the amended cost claim. It is deliberately marked preparation-only,
not a frozen dispatchable protocol. Existing interfaces and scientific grants
must be bound before execution; no null placeholder authorizes a start.

Do not restart the old metadata or container-control sequence. Continue with
the remaining task preparation and one consolidated qualification pass. Retain
the three-repetition exploratory scope, engineering-only role conclusions and
the unanswered new-site solar exposure item without asking the old site-2107
question again. Source preparation may inspect private drivers through trusted
code, but advisory workers receive only metadata and no weather values.

### Completed preparation and next boundary

The bounded extraction finished successfully for all three years: 8,784 hours
in 2012 and 8,760 hours in each of 2013 and 2014. It used 531 range requests
and received 412,328,247 bytes. All nine stages completed within their request
and response reservations. The [metadata receipt](../../examples/utility/wind-reserve-preparation.json)
records annual payload hashes and accounting. Private arrays remain in the
ignored preparation directory. Full source objects were not hashed, and total
preparation elapsed cost was not measured. No scientific wind score was run.

Focused wind tests passed (40 passed, 4 optional skips). The four reserve
extractor tests also passed in the environment with HDF5 support, including
the two fixture tests skipped in the wind environment. Ruff passed for the
changed wind source and test files. These checks establish extraction and
scorer behavior, not completion of the scientific study.

The finite continuation is to bind the prepared sources and four task adapters,
resolve the pending solar-1278 exposure fact, then freeze and qualify the
90-cell design once. Dispatch the 72 primary cells and 18 engineering ablations
as separate compatible suite manifests if the suite schema requires a full
task-route product. Run selection, close the common barrier, score confirmation,
and report every cell, including failures. A failed qualification gets at most
one correction cycle, followed by an explicit incomplete result identifying
the failed contract. Do not reopen equipment identification, equal end-to-end
cost enforcement, or the historical control sequence as prerequisites for the
narrowed claims.

## Consolidated task bindings and qualification

The [task bindings](../../examples/utility/consolidated/task-bindings.json)
contain four validated `TaskSpec` records. Each binds its model entry point,
source hashes, environment lock, candidate domain, partition and outcome rules.
The [builder](../../examples/utility/consolidated_bindings.py) rejects a saved
binding when its definition or source identity changes. These records are not
runtime registrations or execution grants.

The [exposure record](../../examples/utility/consolidated/exposure.json) records
the user's exact answer, "No prior inspection or use", for solar site 1278 in
2013. This resolves the personal exposure question. The metadata inventory lists
365 reserved source objects; their measurements have not been acquired or
validated by this pass.

The replacement solar definition uses measured POA and the frozen development
derating baseline. Its secondary measure is equal-weight power-sum bias, not
integrated energy. The 10 percent absolute limit follows the recorded replacement
screen, with at most one percentage point degradation. This is an explicit
prospective amendment to the old site's energy-based policy. It does not qualify
the reused development check as independent confirmation. Across domains, report
all paired repetitions and annual/scenario strata rather than treating time
samples as independent search repetitions.

One consolidated pass covered task identity changes, CAMELS parsing and basin
conservation, solar cutoff and output limits, engineering scenario custody and
coupled scoring, reserve extraction, annual wind scoring and confirmation
recovery. The interoperability environment passed 176 tests and the wind
environment passed 105. Logs and hashes are linked in the qualification result.
No live agent invocation or confirmation score was produced.

The execution decision is **incomplete**, for three concrete contracts:

1. Stage the actual sources under the final suite identity: CAMELS partitions,
   solar 2013 measurements, one new engineering draw and the prepared wind years.
2. Connect the four adapters/scorers to executable route registrations, protected
   grants and selection-budget enforcement. The new solar callable still needs
   its campaign input/mask/scoring wrapper; the historical solar wrapper is not
   interchangeable with it.
3. Bind verified development baseline references and absolute gains, then freeze
   the actual host, resource profiles and source snapshot in the two suite
   manifests (72 primary cells and 18 engineering ablations).

Do not rerun these 281 checks merely to produce another archive. Test only changes
needed to close those three contracts. Exact equipment recovery, certified solar
energy, complete end-to-end cost matching and another platform are outside the
narrowed claim and do not block this continuation.
