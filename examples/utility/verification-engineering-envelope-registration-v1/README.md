# Engineering envelope registration checks

This archive records the [registered recipe and limits](../../../docs/reviews/part-5-engineering-envelope-registration.md).
It contains public development metadata and no confirmation source.

- `public/` holds the typed result and observed work from the direct OpenMDAO test.
- `tests-initial.xml` retains the mistaken source-deletion recovery test failure.
- `tests-corrected.xml` records the corrected supervised regression.
- `tests-openmdao.xml` records the separate actual model check and warning.
- `tests-adjacent.xml` and `tests-reader-final.xml` record the controller/report
  regression and final common-reader checks. These runs overlap.
- `build-install.py.txt` and its logs record an offline core-only wheel build.
- `read-installed.py.txt`, `check-reader.py.txt` and `reader-verification.json`
  record relocated replay with model imports and external execution denied.
- `source-pins.json` and `wheel-input-pins.json` pin the checked code.

The direct model check used an authored fixture job and 35 additional root calls,
with 26 Problems and returned cleanups. It is not an original supervised
scientific job receipt. The synthetic worker test separately exercises v3
supervision and recovery. The typed result preserves the false optimizer-buffer
flag. Original physical checks passed without changing their threshold.

The historical producers require new output directories and must not be rerun
to repair or replay these records. Reader replay runs no model. The wheel uses
existing base dependencies and qualifies only the recorded local reader scope.
