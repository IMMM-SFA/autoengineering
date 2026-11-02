# Mixed execution verification

This directory retains development contract checks for the mixed prediction and
engineering execution plan. The fixtures are authored examples. They establish no
real-task, live-provider, independent confirmation or utility result.

- `utility.log` and `utility.xml`: initial broad check, 359 passed, 16 skipped and
  five mixed-preflight failures. Prediction snapshots were consumed as a generator
  during source verification. The final implementation materializes them once.
- `optional-execution.log` and XML: initial optional check, 19 passed and six failed.
  Five failures concern the same generator defect. The engineering CLI test also
  encountered source drift during verification. A recheck in its original
  interoperability environment rejected changed source closure before execution.
- `mixed-corrected.log` and XML: eight corrected mixed checks passed.
- `optional-corrected.log` and XML: eight mixed checks and the existing engineering
  CLI resume check passed in the interoperability environment.
- `guarded-reader.log` and XML: initial mixed manifest reconstruction with model
  imports and physical/network dispatch denied, plus a Path.read_bytes guard.
- `guarded-reader-final.log` and XML: the stronger check also denies original
  captured-source access through os.open, Python open and pathlib. The artifact
  reader uses os.open. Archive relocation was not tested.
- `mixed-final.log` and XML: eleven passed and one catalogue test failed before
  reaching the intended preflight check. Its changed task candidate pool still had
  the original route grant. The final test changes both identities and checks them
  against the supplied campaign. The initial command used `-x`, so its last corpus
  case was not run.
- `utility-final.log` and XML: fresh broad check after those corrections, including
  all thirteen mixed tests. Inspect its result separately from the earlier runs.
- `documentation.log` and XML: documentation contracts.
- `ruff.log`: repository Ruff check.

The broader and optional checks overlapped. Their durations are not performance
comparisons. No prior evidence directory or frozen scientific criterion changed.
The complete Part 5 plan remains unfinished. A real exposed mixed-task rehearsal,
wind execution, complete costs/effort, independent task admission and confirmation,
platform/host qualification, installed engineering execution and relocation remain
open.

The last reader change strengthens only the test guard. Production sources stayed
fixed during the final broad check. Its collected test uses the earlier guard; the
stronger guard has its own passing final check. `runtime-source.json` records the
source/test/configuration snapshot before that guard change.
