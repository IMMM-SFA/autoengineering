# Strict fixed-scorer output validation

Live output and saved-result recovery now share strict validation. Duplicate JSON
fields, nonfinite values, invalid numeric types, unknown output/score fields and
inconsistent failure scores are refused. Success requires finite nonnegative
RMSE and Boolean feasibility. The fixed worker's infrastructure_failure and
insufficient_data outcomes retain null values and feasibility. Malformed evidence
is never converted into a penalty objective. Metadata JSON also rejects duplicate
fields and nonfinite numbers. Error text omits the rejected document.

The initial regression suite recorded 17 failures and four passes. The repaired
output/runtime/creation/archive/scorer/recovery/execution suite passed 131 tests
in 12.40 seconds. Ruff passed. These tests cover authored malformed responses and
rehashed saved projections. They do not claim that the fixed worker produced those
malformed responses in a real container.

One approved local synthetic confirmation on the changed runtime started one
container and one scoring child. It returned RMSE 1.0 W. The suite publication
was deliberately interrupted after score creation. All authored labels were
then deleted. Explicit recovery with daemon/new starts denied published the
original result and execution metadata, preserving the original reservation and
access history. Cleanup removed the original container and observed its absence.
No real confirmation data, provider call, image pull or remote job was used.

The wheel was built from an isolated local source copy without installation or
network access. All 199 packaged core Python files matched current source. An
isolated interpreter used extracted wheel contents to recover relocated original
evidence with socket creation, subprocesses and daemon API requests denied. The
same installed code rejected duplicate-key output even when its saved hash and
parsed projection matched. No label files were present. The first offline harness
failed during ssl import because its socket constructor guard was installed too
early. Its log/source are retained. The corrected harness imported ssl first and
passed without another container run.

Original synthetic execution metadata, source, harness texts, wheel digest and
checks are retained here. Earlier runtime controls and full-suite checkpoints
keep their original source scopes. This source change does not retroactively
qualify the new runtime against those controls. Complete resource, privacy,
interruption and result-commit qualification is still open for this runtime.
Independent task custody, thresholds, unmeasured costs and a frozen protocol are
also missing. Part 5 remains incomplete and private scoring remains unqualified.
