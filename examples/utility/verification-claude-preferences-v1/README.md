# Owned CFPreferences privacy diagnostic

The new script targets only one new random org.autoengineering.qualification
user-domain key. Its fixed CoreFoundation reader sees the synthetic value in a
control process with the native client's private HOME environment. Under the
current Claude policy it sees no value. The probe executable is substituted for
the actual client. This is one API-access observation, not complete preference,
workspace/shared-memory, actual-native-client or OS qualification.

The writer and clearer use public exact-domain APIs. Only the generated test key
is set or removed. No existing application domain is targeted. Apple documents
[exact-domain set/removal](https://developer.apple.com/documentation/corefoundation/cfpreferencessetvalue%28_%3A_%3A_%3A_%3A_%3A%29)
and [synchronization](https://developer.apple.com/documentation/corefoundation/cfpreferencessynchronize%28_%3A_%3A_%3A%29).
The compiled source, compiler output, policy, commands and owned process receipts
are preserved in probe-v1 through probe-v4 with per-archive SHA indexes. Original
absolute paths remain. These are not portable execution archives.

The first run removed the key but left an empty owned plist. That empty file was
removed after bounded content/type/owner/link/inode checks. Later current-source
runs observed asynchronous storage flush: the API key was absent while the disk
still briefly held the canary. Immediate cleanup and a five-second bounded wait
refused deletion. Both failed summaries remain. The wait accepts only the exact
owned canary as transient. Unexpected nonempty data, links and nonregular files
are never removed. No bound or policy was relaxed to make the run pass.

Cleanup-only reconciliation verifies the caller-pinned original scope, source,
all six stopped process receipts, exact commands and control observations. It
then removes only that domain's empty file, without another probe or preference
API call. The latest current-source receipt is probe-v4/cleanup-reconciliations/
000002.json. The original summary remains failed. Its successful cleanup was
recorded separately. Reconciliation replay was idempotent. Process-observation
helpers are used by the watchdog verifier. Receipt 000001's field named
new_process_starts meant probe starts and was too broad. The v1.1 receipt uses
new_probe_process_starts and states that observation helpers are used. No total
process or efficiency claim is based on the earlier field.

All four generated domains' keys were removed. final-storage-check.json confirms
their files are absent. The domain identifiers and markers are synthetic data.
There are no real credentials or provider calls. Current source requires this
additional owned-domain observation under Claude qualification version 1.1. Old
version 1.0 receipts and records missing that field are refused. Codex observation
requirements retain their shape. No actual Claude qualification is written.

Final profile/host/preparation, canary and documentation checks passed 135 tests
in 32.03 seconds. Ruff and whitespace checks passed. Initial restricted tests had
87 passes and one blocked owned shared-memory allocation. The permitted rerun
passed 88; later runs passed 131 and 134 before the final tests. All logs remain.
The final source snapshots match the executed test bytes. No full default/Bayes,
installed runtime, scientific matrix, independent confirmation or live conformance
is claimed. Remaining complete boundary, model/authentication, private scoring,
independent data and Part 5 requirements remain open.
