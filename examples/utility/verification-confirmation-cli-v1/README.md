# Confirmation CLI through trusted registrations

The utility CLI now exposes confirm WORKDIR GRANT --registration PROFILE.
--recover publishes only a verified result from an original charged attempt.
The command delegates to ConfirmationService for selection sealing, reservation,
access, scoring, acknowledgement and recovery. It does not create another
scientific runner or ledger.

Applications construct the same command with explicit trusted Python
ConfirmationRegistration objects. Each binds one suite, partition, scorer/outcome
identity and qualification-evidence digest. Admission is an application assertion,
not automatic proof of isolation. No import string, user JSON, environment variable
or CLI flag can register a scorer. The distributed command has no admitted private
scorer. The candidate container and independent tasks remain unadmitted.

Before service dispatch, the command checks the sealed grant and current scorer
identity and pins public registration metadata under control. The pin cannot
reserve work, grant access or supply a score. A changed qualification pin refuses
the original grant. Unknown/unadmitted registrations, drift, stale/incomplete
selections, duplicate/unknown input fields, symlinks and uncertain original
attempts stop without new callbacks. Errors omit private payloads.

The first regression recorded nine failures for the absent command/module.
The expanded run recorded 97 passes and three test-fixture assertion failures:
the assertions incorrectly assumed that selection had created no prior attempts.
They were corrected to verify that rejected requests leave the journal head
unchanged. The final CLI/confirmation/recovery/cost/report suite passed 100 tests
in 21.53 seconds. Ruff passed. Raw failure logs are preserved.

A wheel built from isolated local sources matched all 200 core Python files.
Four separate isolated CLI processes used an explicitly authored fixture
registration: interrupt after score creation, refuse automatic retry, recover the
original result, then replay it. Exactly one authored callback and one recovery
occurred. The original reservation/access remained unchanged. The wrapper denied
network sockets and child processes and imported no optional scientific framework.
The failure canary was absent from public output. This fixture has no real labels,
model execution, container, provider call or private-runtime qualification.

The existing runtime and both worker sources are unchanged. Their actual control
receipts remain scoped to those payloads. The earlier 680-pass utility checkpoint
predates this CLI increment. Full default/Bayes suites were not rerun. Complete
private profiles, independent task custody, thresholds, protocol, platforms and
actual second-host conformance remain open. Part 5 remains incomplete.
