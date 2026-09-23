# Independent review: extended BMI comparison and target stopping

Reviewed `examples/local_models/convergence.py`, `CONVERGENCE_PROTOCOL.md`, `convergence-targets.json`, and `tests/test_local_convergence.py` against base `25f406b` on 2026-09-05. Read the relevant durable controller and backend paths. No implementation files were edited and no experiments or tests were executed in this read-only review.

## Must Fix

1. **P2: Unexpected evaluator exceptions cause undercounted attempts and missing time.** `convergence.py:69-79` appends timing only after normal execution or the two caught error types. `OptimizationStudy.run_result()` catches other exceptions and commits infrastructure-failure results, so those are real ledger attempts but absent from `model_times`. `convergence.py:100,122,138` then undercounts evaluations and may mislabel reaching the cap. Use committed ledger entries/new-evaluation counts for attempt accounting, record evaluator elapsed time in `finally`, and retain infrastructure failure as a distinct result category. Add a focused unexpected-exception test, since the current failure test covers only ValueError.
2. **P2: The first solar study includes a lazy import despite the stated timing boundary.** Solar BMI components import pvlib inside their timed `_step` calls. Unlike the original full driver, this target driver does not first execute a model-swap workflow. Random seed 3 therefore pays the first solar import in its model and study times, while later methods use the imported package. Import pvlib explicitly before the study timers, or report startup consistently rather than claiming imports are excluded. This does not require a model evaluation or modifying the scientific target.

## Should Fix

3. **P3: Fixed-study provenance and suite provenance differ.** `convergence.py:159-163` adds the new protocol and target hashes to the outer suite manifest, but fixed mode calls the original `study_run()` at line 190, which recomputes its own provenance without those two files. The suite is traceable as a whole, but an isolated fixed-study directory does not carry the convergence-protocol identity. Either pass the augmented hashes into that driver or state that the outer manifest is required with each study.
4. **P3: Source-hash validation is currently external to execution.** Main loads the target file but does not verify its listed source ledger hashes or recompute its minima. The checked target file is correct now (see below). A small read-only verifier before evaluation would make future reruns fail clearly on drift.

## Looks Good

- Independently recomputed SHA256 for all **27** historical source ledgers. All match the frozen target manifest. Read **324** successful validation outcomes, 108 in each domain. Recomputed minima and multiplication by 1.05 match the frozen values exactly: copper 0.2057744777270775, hydro 2.169295332362961, solar 183.83143789933789. No test outcomes were needed for this check.
- The stopping rule is a common observed validation-quality target, not plateau detection or a claim of mathematical convergence. Its historical/development basis is explicit.
- New seeds 3-7 are distinct from historical seeds 0-2. Matching seed labels across algorithms does not imply identical initial designs, and the protocol says so.
- The extension correctly identifies original seeds as paired extensions rather than new independent replications. Verification of the first 12 actions/objectives is required before interpreting 24-call results as paired.
- One-call `run_result(max_new_evaluations=1)` snapshots permit checking the best recommendation after each committed attempt. The first crossing stops further evaluation. Budget and application stop states remain separate, rather than rewriting a controller budget or silently resuming.
- Test rows are removed before optimization. Final recommendation is frozen before test scoring. Failure results have no target-satisfying outcomes. Inclusive finite target comparison is correct.
- Capped non-successes are explicitly censored, and successful-only medians require their denominator. Mean calls consumed is not presented as an efficiency ranking when success rates differ. Backend termination remains separate from cap censoring.
- The protocol distinguishes fixed and target experiment timing, includes recommendation-check/bookkeeping overhead, and excludes held-out evaluation. Rotating method order helps reduce order effects, though five seeds do not perfectly balance three method positions.
- Unit tests cover inclusive/finite targets, early success, cap exhaustion, unchanged stopping after perturbing test labels, and caught model-failure accounting. They were inspected but not rerun under this read-only/no-experiment assignment.

## Suggestions

Report backend-terminated runs separately from capped runs when computing any restricted cost summary. A run that stops early because the backend fails is not a cheap successful search. If presenting time-to-target curves, show non-successes as censored at their actual observation horizon and retain the termination reason.

The model-call reduction needed to offset optimizer overhead should be stated conditionally using measured call counts and overhead. The current local model timing does not by itself establish performance on expensive simulations.

# Follow-up review: accounting fixes and report generator

Read the revised runner, added infrastructure-exception test, and `scripts/summarize_local_convergence.py` without executing tests, models, or audit computations during the active timing experiment.

## Resolved

- Evaluator time is now recorded in `finally`, and iteration/cap counts use committed `result.entries`. This resolves undercounting of unexpected infrastructure failures. The additional test checks that failure class and ledger/trajectory accounting.
- `main()` imports pvlib before timers. Target experiment startup accounting now matches the stated exclusion.
- Historical ledger hashes are checked before new execution. The report generator also recomputes pooled minima and the 1.05 targets.
- Archived earlier fixed-driver/protocol files are accepted only when their hashes match the original suite manifest. This preserves the actual fixed-run implementation rather than pretending it used the subsequent target-driver fixes. Individual fixed studies still depend on the outer suite manifest for the extended protocol context.

## Must Fix in report logic

1. **P2: Require actual cap exhaustion before reporting >60 censoring.** `scripts/summarize_local_convergence.py:64-65` checks `len(ledger) <= cap` but then allows any no-hit run labeled `evaluation_cap`. It does not require that such a run consumed 60 calls. Later, line 146 prints `>60` for every non-success. Require no-hit `evaluation_cap` runs to have `len(ledger) == cap`. Handle other backend-termination reasons separately with their actual observation horizon, or fail clearly if the completed registered matrix unexpectedly contains those states. The protocol explicitly preserves backend termination as a separate outcome.
2. **P2: Preserve runs with no successful recommendation.** Summary and individual tables at lines 153 and 198-199 unconditionally access test/recommendation RMSE. An all-failure run has test=None and no RMSE, causing report generation to fail. Render unavailable values explicitly and report valid denominators for any median calculated from available scores. Do not silently discard failed runs from success fractions or call-consumption summaries.

## Looks Good

The generator verifies complete method/domain/seed inventory, application-result equality, ledger length, exact original 12-entry prefixes, earliest successful target crossing, and cumulative trajectory accounting. It separates success-only median calls from all-run costs and success fractions, preserves individual rows, and describes the hypothetical expensive-model formula as conditional. No changes to optimization or scientific target are needed to repair the reporting findings.

The claimed separate objective/held-out recomputation audits were not inspected or run in this follow-up. They remain a completion dependency before the final report claims that verification has passed.

# Final review: completed matrices and generated interpretation

Read the generated `results/CONVERGENCE_RESULTS.md`, corrected report logic, and new false-cap/backend-stop/missing-test tests. Performed only lightweight JSON/ledger inspections, with no model evaluations or test jobs.

## Prior report findings resolved

The report auditor now requires exact cap exhaustion for `evaluation_cap` and preserves earlier backend termination at its actual horizon. Target summaries/individual rows handle absent test values explicitly. Existing fixed-study tables still assume complete recommendations, which is satisfied by the completed fixed matrix. No unresolved must-fix issue was found in the generated report for these completed runs.

## Independently checked numerical evidence

- Fixed matrix: **27 studies, 648 calls**. All **27** first-12 ledger prefixes match their original development ledgers exactly.
- Target matrix: **45 studies, 745 calls**.
- Hydro BO reaches the target in **6, 6, 7, 6, 7 calls**, with **5/5 successes**. Random and Sobol each have **0/5 successes at 60 calls**. Median held-out RMSE is **2.8839228599** for BO, versus **2.7979279266** for random and **2.8194639046** for Sobol. The report correctly separates validation-search success from worse held-out performance.
- Hydro BO ledgers contain 20 initial Sobol actions and 12 adaptive `system:bayes` actions. This target result does exercise adaptive BO.
- Solar BO uses **3, 1, 4, 2, 4 calls**, identical to Sobol. All 14 BO-policy actions in these runs are labeled `system:sobol`. The report correctly states that the solar target never exercises adaptive BO.
- Copper BO uses **4, 1, 5, 1, 7 calls**, versus Sobol **4, 1, 5, 1, 12** and random **1, 8, 3, 7, 2**. Copper BO includes 14 Sobol actions and only 4 adaptive actions. The report's limited interpretation is appropriate for five seeds and these small differences.
- Listed target call counts, success fractions, and held-out medians agree with the stored JSON rows.

## Interpretation and remaining completion dependency

The generated report does not equate reaching the frozen validation threshold with global convergence, better test performance, or partial BO efficacy. Capped runs remain censored. The expensive-model expression is explicitly a conditional projection. Do not plug 60 into an exact eventual-success break-even calculation for the censored hydro baselines: their actual time to the target remains unknown.

Parent is separately running numeric objective/held-out audits and focused tests. This review does not claim those jobs have finished. Once those checks pass and their artifacts agree with the report's statement, no additional review finding blocks this deliverable.
