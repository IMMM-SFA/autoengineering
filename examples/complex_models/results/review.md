# Independent review: larger BMI models and longer budgets

Read-only review against base `1a01a6e`, 2026-09-05. Scope: `examples/complex_models/models.py`, `run.py`, `PROTOCOL.md`, `module.json`, both system YAML files, and `tests/test_complex_models.py`. No model, benchmark or test execution was performed during this review. Parent owns implementation changes.

## Must Fix

1. **P1: Relative CLI paths break target freezing/loading.** `run.py:196` computes `path.relative_to(ROOT.parents[1])`, but `fixed` comes directly from argparse and commonly remains relative. Target mode repeats the problem at `run.py:233` with `args.targets`. Calls with normal repository-relative `--fixed` or `--targets` will raise ValueError because the base is absolute. Resolve input paths before converting them to repository-relative provenance names. Add focused coverage using relative CLI paths.
2. **P2: Target freezing does not establish a completed 96-call matrix.** `run.py:183-204` verifies only row inventory, then pools matching globbed ledgers. A full row inventory can contain early backend stops, short/missing ledgers, or extra matching directories. This can silently freeze a target from a different amount of work than the registered complete 96-call matrix. Validate exact expected ledger paths, 96 committed attempts for each run, matching row counts/cap/status, and required checkpoint membership before freezing. Retain early termination as an explicit incomplete condition rather than silently treating it as a complete fixed matrix.

Both findings were sent to the parent immediately.

## Should Fix / interpretation limits

- **P2: Do not imply full reservoir spin-up.** At the minimum slow release fraction 0.001/day, reservoir memory is approximately 1000 days. The inherited 90-day warmup, or 273 days preceding validation, cannot guarantee equilibration across the registered space. Preserve the protocol and initial conditions, but describe the results as conditional on half-full initial soil and empty routing stores.
- **P3: State the exact CEC/De Soto distinction.** The pinned CEC module has `Adjust=-41.490582`, used by pvlib's CEC translation but not by the chosen `calcparams_desoto` call. The protocol correctly calls this De Soto using a representative CEC snapshot. Keep that wording and avoid implying reproduction of the full CEC model at nonreference temperatures.
- **P3: Add an independent solar scaling/reference check when practical.** Scalar BMI versus `diode_power()` array parity checks dispatch consistency, but both sides call the same function with the same constants. A direct module-reference/STC-to-plant scaling check would catch a shared watts/kilowatts or module-normalization error. No such error was found by dimensional inspection.

## Looks Good

### Water equations and coupling

PDM soil uses the inverse storage-capacity relationship to obtain the capacity coordinate, separates direct capacity overflow from distributed-store overflow, and limits actual evaporation to available water. Algebraically, rainfall equals excess plus evaporation plus the soil-store increment. The implementation's mean storage capacity `cmax/(1+beta)` and half-full initialization are consistent.

The routing component partitions excess into alpha fast flow and (1-alpha) slow flow, applies three fast reservoirs in series, and counts all remaining stores. With the declared same-step inflow/release scheme, the first unit-impulse outflow is `(1-alpha)*kslow + alpha*kfast**3`. This differs from the cited repository's release-before-inflow discretization, as the protocol explicitly allows. State is retained across daily BMI updates and validation/test boundaries. The cited PDM source supports the conceptual soil equations: [HYMOD source](https://raw.githubusercontent.com/jdherman/hymod/master/HyMod.cpp).

### Solar equations and source contracts

The complete graph supplies effective irradiance to temperature and diode components, measured air temperature to Ross, module temperature to the diode solver, and DC power to the existing inverter. All connected units are consistent. Effective irradiance also changing module temperature is an explicit model-chain assumption.

The factor `2369 / module_STC_W` converts simulated module watts to the chosen plant kilowatt scale. It is equivalent to multiplying by the effective module count and dividing by 1000. The 1910 kW inverter cap is inherited. Changed electrical parameters can change the equivalent module's STC output, so this remains a calibrated equivalent plant rather than fixed physical module identification, which the protocol states.

Read the installed CEC CSV without running a model: its SHA256 matches `module.json`; the FS-267 row exactly matches every recorded numeric parameter. The installed pvlib source and [pvlib De Soto documentation](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_desoto.html) confirm retaining CEC extraction values EgRef=1.121 and dEgdT=-0.0002677 even for this thin-film snapshot. The public stable page currently documents a newer pvlib version, so the installed pinned source was also checked.

### Runner and scientific comparison

- Existing model functions/spaces are reused. The five examples comprise three modeling domains and two additional model families, not five independent datasets.
- Only validation scores enter the optimizer. Frozen checkpoint recommendations are saved at 12/24/48/96 before held-out scoring, and test metrics are computed only after the complete fixed trajectory.
- Target mode checks each committed attempt, counts initialization and failures, records timing in `finally`, and keeps cap and backend termination distinct.
- Four versus eight initial points is an explicit, preregistered complexity-dependent setting. Results must retain initialization and adaptive-action labels, especially for easy targets.
- Original validation targets are carried forward unchanged. New-model targets use fixed-run validation outcomes, not test metrics, and are intended to freeze before new target seeds.
- Raw ledgers, source/data/protocol hashes, checkpoints, diagnostics and model/controller timings are recorded. Existing-model prefix comparisons and earliest-crossing/cap audits remain required completion checks.
- Inspected tests cover causal water balance, routing impulse/mass, solar scalar/vector parity, zero irradiance, inverter ceiling, held-out-label isolation and baseline search-space validity. They were not rerun by this reviewer.

## Completion boundary

Fix CLI path normalization and complete-matrix validation before freezing target values. Verify full prefix equality and run numerical audits before claiming results. No benchmark superiority, partial BO efficacy, or completion of the ongoing experiment is asserted by this review.

# Follow-up review: fixes, solver and component swaps

Read the revised runner, model implementation, protocol, workflow, and added tests during the fixed experiment. No benchmarks, models or tests were run by this reviewer.

## Resolved

- Relative CLI paths are resolved before provenance conversion. The original relative-versus-absolute failure is fixed for the registered repository-local artifact paths.
- Target freezing now verifies the exact 45-run inventory, source hashes, 96 ledger entries and reported attempts, evaluation-cap status, the four checkpoint counts, and matching application-result JSON. It enumerates only the nine expected ledgers for each new model instead of pooling wildcard matches. This resolves freezing a target from the previously accepted incomplete matrix. Full recommendation/checkpoint membership and numeric audits remain separate completion checks, as planned.
- Protocol now explicitly discloses slow-reservoir initialization dependence and the De Soto/CEC Adjust distinction.

## Solver correctness

`diode_power()` now uses pvlib `max_power_point(..., method="brentq")` on the same translated single-diode parameters and retains the same plant scaling. This computes the requested maximum-power quantity directly rather than all IV outputs. The added test compares it against the separate Lambert-W solution at three combinations spanning the registered series-resistance, saturation-current and diode-voltage scales, with irradiance and temperature variation. The comparison uses consistent reference parameters and loss scaling. No incorrect constant or parameter mapping was found. Passing runtime test evidence is supplied by the parent; it was not independently rerun during timing.

## Real graph swaps

`workflow.py` replaces the routing BMI class with SingleFastRoutingBmi and the diode BMI class with EmpiricalDcBmi through `swap_component`. It executes the resulting graph, validates terminal system output, selects on validation RMSE, writes the frozen selection/configuration, and only then computes test results. These are actual changes to executed model classes and routing structure, not descriptive metadata changes. The fixed configurations make this a component-swap diagnostic, not a matched-budget optimizer comparison.

No unresolved must-fix finding remains in this read-only follow-up. Final numerical audits, full prefix checks and source/checkpoint integrity verification remain necessary before reporting completed experimental results.

# Follow-up: numerical audit and report scripts

Read `scripts/audit_complex_models.py` and `scripts/summarize_complex_models.py` plus the backend's initialization logic. No numerical evaluations, benchmarks, tests, or heavy audits were executed during the active fixed matrix.

## Must Fix before claiming complete verification

1. **P2: Historical prefix checks silently skip missing evidence.** `summarize_complex_models.verify()` checks prefixes only inside `if history.exists()`. For the three original models, missing original files must be an error, not a smaller verified-prefix count. Require original histories for every registered original-model run, with 27 fixed prefixes and 45 target prefixes. New-model histories should remain explicitly absent/not applicable.
2. **P2: Audit can accept an empty recommendation despite successful eligible observations.** In `audit_complex_models.audit()`, the `rec['action_id'] is None` branch checks only that test is None. It should also require no successful observations in that checkpoint prefix. For nonempty recommendations, require the selected ledger result to be successful in addition to current configuration/outcome/minimum comparisons. Otherwise a malformed or missing recommendation can evade the stated recommendation audit.
3. **P2: Report audit claims are not bound to completed audit artifacts.** The report says every successful objective and checkpoint/final recommendation is checked but does not load numerical audit JSON. Require the expected audit outputs, matching current ledger hashes, counts, and audit-script source hash before producing that completion claim. Structural verification alone does not establish independent numeric recomputation. Alternatively keep the wording prospective until audits finish, but final delivery should bind the completed evidence.

## Should Fix

Show validation RMSE at all four fixed checkpoints as well as held-out RMSE. The current table shows test progression but only final validation. This prevents readers from assessing how optimization of its actual objective changed between 12, 24, 48, and 96 calls. A second compact validation table would preserve clarity.

## Looks Good

The solar oracle independently reconstructs temperature, De Soto translation and Lambert-W maximum power from arrays, with all seven calibration controls correctly mapped. Its watts-to-plant-kilowatts factor and inverter rating match the BMI path. Existing models use their vector kernels, and HYMOD uses a rerun plus water balance. The report accurately distinguishes those levels of independence.

Successful objectives are recomputed against the validation slice. Non-successes are retained in a failure list rather than fabricated as valid outcomes. Checkpoint membership uses only the eligible prefix, minimum outcomes are checked, and test metrics are recomputed separately. The audit's recommendation counter includes both the final checkpoint and final recommendation, which may duplicate the same selected action; treat it as number of verified records rather than unique configurations.

The structural report checks full row inventory, application/frozen-file equality, trajectory count and cumulative timing, first target crossing, exact cap exhaustion, backend early termination, and checkpoint-file consistency. Censored runs are not rendered as successful convergence. Missing held-out scores are not silently dropped.

Adaptive action labels are counted directly. Fallback counting distinguishes Sobol initialization from later Sobol fallback after enough successful observations, matching the current unconstrained deterministic backend setup. The report retains failed-attempt counts, modeling units, conditional expensive-model interpretation, and the absence of partial-observation BO testing.

# Follow-up: audit binding and convergence exports

Read the updated scripts without running models, tests or audit jobs during timing.

All three previously identified structural fixes are present: historical evidence is mandatory for original models with exact 27/45 prefix counts, empty recommendations require zero eligible successes, and selected recommendations must point to successful results. Report generation now requires numerical audit JSON and verifies audit-script hash, exact ledger hashes, attempt count, and recalculated recommendation-record count. Validation is displayed at all four checkpoints with explicit missing-score handling. The trajectory CSV correctly exports incumbent validation error and cumulative measured times, distinguished by fixed/target experiment.

## Remaining P2: bind the audited score artifacts

The audit still does not hash the `results.json` containing the checkpoint/final test scores it recalculates. Ledger hashes and record counts do not change if those reported scores are edited later. Structural comparisons with application-result JSON would also pass if the corresponding score were changed there. Add the SHA256 of the exact audited results.json to the audit artifact and compare it before generating the report, or equivalently hash all audited application-result files. This closes the remaining stale-audit gap without touching benchmark sources or rerunning the active experiment.

No further numerical/reporting defect was identified in this read-only follow-up. The CSV's target column on fixed rows is the later reference target, not an active stopping rule for the fixed experiment; retain the experiment column whenever interpreting that export.

# Preliminary final review: complete fixed matrix

The remaining score-artifact binding is fixed: numerical audit JSON now records `results_sha256`, and report generation checks that hash against the current results.json. Together with script and ledger hashes and record counts, this resolves the previously identified stale-score audit gap for the intended immutable completed-results workflow.

Lightweight JSON inspection confirms **45 fixed studies and 4320 calls**. For the two new models, median outcomes at 96 calls are:

| Model | Method | Validation RMSE | Held-out RMSE |
| --- | --- | ---: | ---: |
| hymod | random | 1.416697 | 2.675835 |
| hymod | sobol | 1.324807 | 2.550501 |
| hymod | bo | 1.123847 | 2.573117 |
| solar_diode | random | 174.485710 | 128.431060 |
| solar_diode | sobol | 174.228174 | 124.651681 |
| solar_diode | bo | 173.874478 | 124.984974 |

BO has the lowest median validation RMSE for both new models at 96 calls, but Sobol has slightly lower median held-out RMSE. This supports a validation-search improvement, not a demonstrated generalization advantage. Solar Sobol and BO held-out medians worsen between 48 and 96 calls (121.332668 to 124.651681, and 122.922787 to 124.984974 respectively). HYMOD BO held-out performance also varies nonmonotonically over the checkpoints. The three-seed differences do not establish broad algorithm superiority.

No unresolved code-review finding remains at this preliminary stage. The target experiment is still running, and final numeric audits/tests have not been reviewed as complete. These observed JSON values are preliminary evidence pending independent objective/held-out recomputation. No model, test, or heavy audit jobs were executed by this reviewer.

# Completed-matrix interpretation review

Lightweight JSON/ledger checks confirm **45 fixed studies / 4320 calls** and **75 target studies / 4622 calls**, totaling **120 studies / 8942 primary calls**. Independently verified all **27 fixed** and **45 target** historical prefixes using actions, statuses and outcomes. Every target first crossing occurs on its final recorded attempt, every uncrossed target run consumes the 200-call cap, and there are **zero failed target attempts**.

Target outcomes, with calls in seed 3-7 order:

| Model | Method | Calls | Successes | Median held-out RMSE |
| --- | --- | --- | ---: | ---: |
| hydro | random | 161, 199, 168, 200, 89 | 4/5 | 2.851282 |
| hydro | sobol | 133, 200, 200, 200, 200 | 1/5 | 2.821831 |
| hydro | bo | 6, 6, 7, 6, 7 | 5/5 | 2.883923 |
| hymod | random | 200, 200, 200, 200, 200 | 0/5 | 2.387049 |
| hymod | sobol | 200, 200, 200, 200, 200 | 0/5 | 2.458617 |
| hymod | bo | 158, 62, 146, 67, 200 | 4/5 | 2.665978 |
| solar_diode | random | 3, 5, 8, 3, 13 | 5/5 | 137.132132 |
| solar_diode | sobol | 13, 9, 1, 5, 4 | 5/5 | 114.905412 |
| solar_diode | bo | 10, 10, 1, 5, 4 | 5/5 | 115.884125 |

HYMOD demonstrates materially better attainment of its frozen validation target by BO. It does not demonstrate a held-out advantage: BO's median test RMSE is worse than either baseline. Its observed median study time is also longer: 58.95 seconds versus random 30.20 and Sobol 24.92 seconds. These are observed costs under unequal target success rates, not matched-success runtime comparisons. Do not describe HYMOD BO as a local runtime win.

The simple solar target still stops entirely in BO's initial Sobol points. The new diode target produces just **4 adaptive BO actions** and **26 initialization actions** across all five BO runs. It is therefore limited evidence about adaptive search despite the more complex model. HYMOD BO does exercise sustained adaptive search: 593 adaptive actions plus 40 initialization actions. Copper remains a small difference with limited adaptive work.

Fixed-budget interpretation remains unchanged: BO has lowest median validation RMSE for both new models at 96 calls, but Sobol slightly lower median held-out RMSE. Capped baseline runs do not supply exact eventual time-to-target estimates. The results support useful validation optimization in some applications, not broad generalization or speed claims, and say nothing new about partial-observation BO.

No unresolved code-review finding remains. Final numerical recomputation audits and tests are running under the parent's control, after timed jobs finished. This review verifies stored evidence and interpretation, not completion of those pending audits. No model or test jobs were run by this reviewer.

# Late diagnostic correction and newly identified sensor failure

## Diagnostic copy correction is valid

Inspected `Component.to_dict()`/`from_dict()`: they retain the same metadata dictionary. The previous diagnostic constructed both candidate graphs after changing that shared dictionary, making both execute the simpler class. `copy.deepcopy(component)` correctly isolates replacement metadata.

Lightweight checks confirm exact original workflow.py hashes are preserved in both fixed/source and target/source. Report verification allows that specific archived diagnostic source, not arbitrary changed model/runner files. Primary `run.py` loads declared model YAML and does not call workflow.py, so this correction does not alter primary objective trajectories or require primary reruns.

Preserved initial diagnostic validation scores were identical for the two candidates. Corrected scores now differ:

| Model | Complex validation RMSE | Simpler swap validation RMSE | Selection |
| --- | ---: | ---: | --- |
| hymod | 2.145167 | 3.230686 | complex |
| solar_diode | 258.815273 | 217.719376 | simpler swap |

These power/flow diagnostic comparisons use actual different BMI classes after the correction.

## New P1: measured solar temperature diagnostics are invalid

The corrected result artifact exposed temperature RMSE around 3260 C. Direct inspection of `examples/local_models/data/solar.csv` confirms **all 639 module_c values equal 3276.7 C**, including 355 training, 93 validation and 191 test rows. This is not usable measured module temperature. Its exact origin as saturation/sentinel is not confirmed, so describe it as an invalid fixed sensor value rather than asserting a known missing-data encoding.

This supersedes earlier review statements accepting measured module temperature as observed intermediate truth. Finite-value and source-unit checks were insufficient to validate that sensor channel.

Required correction before final delivery:

- Mark temperature RMSE and the measured-temperature component ranking invalid/unavailable.
- Withdraw claims that this excerpt supplies usable measured intermediate temperature truth.
- Record the constant impossible value, counts and affected artifacts in post-run QA evidence.
- Preserve original data, splits and frozen results. Do not silently delete/repair rows or replace the sensor and imply the original experiment used it.

Primary power optimization remains separable: models use simulated temperature from irradiance and ambient temperature, and the objective returned to BO is AC-power RMSE. No module_c label drives prediction or parameter selection. The finite module-temperature filter retained all these constant-valued observations, so excluding that invalid diagnostic from interpretation does not require changing the primary row set or rerunning the primary studies. Air temperature (-11.9 to 12.8 C), irradiance (50.36 to 717.72 W/m2) and AC power (0 to 1259 kW) have plausible ranges in this cached subset; range plausibility is not an independent sensor calibration audit.

Both the initial workflow bug and invalid temperature channel must remain distinct from the preserved primary AC/flow optimization evidence. No model/test jobs were run in this late review.

# Final QA correction and provenance verification

Read the generated report, QA script/artifact, final workflow diagnostics, and prominent withdrawal notices in the original local-model README and historical results. The sensor finding is now handled explicitly: all 639 impossible temperature observations are unavailable, temperature-error/ranking and observed-intermediate-truth claims are withdrawn, and the AC-power comparison is distinguished from the invalid temperature diagnostic. The raw frozen evidence and original splits remain intact.

Lightweight independent checks passed:

- QA data and script SHA256 match current files.
- Final solar workflow validation/test records omit temperature_rmse and carry an explicit unavailable observation status.
- The only primary-manifest source mismatches are `examples/complex_models/README.md` and `workflow.py`; their exact recorded versions match the archived copies in both fixed/source and target/source. The verifier permits only those two exceptions.
- Fixed numerical-audit artifact binds current results.json and audit-script hashes and records **4320 attempts / 225 checkpoint-or-final recommendation records / zero failures**.
- Target numerical-audit artifact binds current results.json and audit-script hashes and records **4622 attempts / 75 recommendation records / zero failures**.
- Incorrect initial swaps, corrected pre-QA raw diagnostics, and final QA-qualified diagnostics remain separately preserved and clearly identified.

The sensor failure does not alter the AC objective's input dependencies: simulated temperature uses air temperature and irradiance, and optimization receives terminal AC RMSE. Therefore preserving the primary matrices while withdrawing temperature diagnostics is the correct scope of correction. Numerical reproduction of the earlier temperature RMSE does not restore its scientific meaning, and the final report correctly avoids that claim.

No unresolved must-fix finding remains in the final reviewed artifacts. Parent reports both numerical audits exited successfully; their completed artifacts and bindings were independently inspected here. The latest 51-test scope was still running when this final review was requested, so its eventual result remains for the parent to confirm. No model or test jobs were launched by this reviewer.
