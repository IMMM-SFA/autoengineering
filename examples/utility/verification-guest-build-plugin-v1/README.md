# Buildx discovery failure and correction

The approved v1 request ran two client commands. Docker's daemon version read
succeeded. Buildx discovery failed with `docker: unknown command: docker buildx`.
The fresh configuration hid the installed plugin directory.
[Original evidence](failed-attempt.json) binds copied request, source, intents,
results and logs. No base pull, package installation or image build ran. The
original work remains consumed. No retry was attempted.

The preparer now requires an explicit Buildx executable and emits request v2.
It stages a bounded, hash-verified private copy. The configuration stays empty.
Every command verifies original and copied bytes. Drift stops further commands.
Saved readers check the copy without the original executable. Legacy v1 request
and completion reconstruction retains its original bytes and behavior.

The related image, context, archive, build and documentation regression passed
101 tests. Repository lint passed. Tests cover plugin availability before the
first command, drift before and during execution, copied-byte tampering, offline
reconstruction and legacy replay. They use authored Docker responses.
An additional [actual installed-plugin help probe](actual-plugin-help.json)
passed with a fresh private configuration and absent daemon endpoint. Its
[output](actual-plugin-help.log) establishes local plugin discovery only.

The administrative helper and its tests changed. The 224 core files and frozen
guest inputs did not change. The preceding full default result of 3,415 passes
and 120 skips predates this fix and was not rerun. The
[corrected request](../prepared-guest-build-v2/README.md) is unexecuted and awaits
approval. Runtime/privacy, Linux inference, live-host and independent scientific
qualification remain open.
