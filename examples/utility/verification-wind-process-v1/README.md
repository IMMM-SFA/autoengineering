# Wind native process verification

The separate wind profile reuses the native supervisor's permanent reservations,
owned process management, stop checks, cancellation callback and original-process
recovery. Existing circuit job/result schemas and worker selection remain the
default. Wind records contain bounded native proposals and wake/gradient callback
traces. They do not manufacture circuit residuals or counts of inner wake solves.

The fixed core bootstrap checks source bytes before importing the supplied wind
entrypoint. A successful native report remains an unscored proposal. Exact domain
violations, failed/budget results and unresolved callbacks yield no configuration.
Callback cost records distinguish attempts, completions, failures and unresolved
work. If a process returns no trace, those callback quantities remain unknown.

The real `development/wind-native-process-v1` probe ran two separately reserved
processes: the bounded original TOPFARM driver, then a fresh wind scenario check.
The driver converged after two completed wake callbacks and one completed gradient
callback. The fresh evaluation passed all required checks at
37.06343379120568 GWh, matching the prior baseline. Completed recovery added no
reservations. This is bundled development data, not independent weather evidence
or a demonstrated native gain.

The default reader verifies original report/job/binding bytes, process completion
and output hashes, the separately evaluated configuration and 188 archived source
files. After archiving, guards deny captured-source reads, physical/network dispatch
and PyWake/TOPFARM/OpenMDAO imports. Run it from the checkout with:

```sh
PYTHONPATH="$PWD" .pixi/envs/default/bin/python \
  examples/utility/verification-wind-process-v1/check-reader.py
```

`reader-qualified.log` and `offline-reader.json` record success. The first direct
script invocation lacked the examples package on its path. It is retained in
`reader.log`. A separate installed wheel reader is qualified in verification-wind-process-installed-v1.

`final.xml` records 28 passes and two optional skips before the added stdout-tamper
test. `wind.xml` records 37 passes and five dependency warnings with that test.
`contracts.xml` is the broader final-source engineering/study/cost/wind check.
It passed 110 tests with 12 optional skips in 329.89 seconds. Repository lint passed.

Earlier failed attempts remain visible. `initial` encountered sandbox-denied ps.
`owned` found the example worker unavailable under isolated startup. The fixed core
bootstrap replaces that worker. `bootstrap` found that the editable package's
PathFinder registration was unavailable even though its full source closure was
present. Core closure verification is retained; supplied example registrations
are checked separately. `boundary` passed six tests and failed one exception-type
assertion on artifact corruption. No scientific guard was relaxed.

`rehearsal.log` refused an existing wind-native-v1 directory before starting work.
That older evidence was preserved. `rehearsal-fresh.log` records the new absent
wind-native-process-v1 directory and both verified stops. No paid provider,
independent confirmation, public wind route or utility comparison ran here.

Final guarded readers also deny built-in scientific imports and assert those optional
modules were absent at startup. Both passed. No process remains active.
