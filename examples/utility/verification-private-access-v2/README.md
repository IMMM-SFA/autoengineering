# Deferred private-label access verification

PrivateRMSEScorer previously read labels during construction. Reconstructing a
scorer to recover a saved result could read private bytes before another access
was charged. Version 2 now registers only opaque custodian artifact metadata.
It validates the public prediction schema, selection/model/partition and finite
numeric vector before touching labels. It then writes a durable private access
intent before the first label read. Interrupted access/preparation cannot be retried
through an existing attempt directory or the confirmation service.

The v2 identity includes parent scorer source, fixed worker source, custodian
artifact digests, outcome, partition, boundary and timeout. It does not silently
resume v1 attempts. Recovery verifies original access/job/worker bindings and the
checksummed completed owned process, including its original boundary command and
watchdog stop. It never reopens labels or launches another scoring worker. The
watchdog verifier can use process-observation helpers. Legacy saved public score
receipts keep their original identities and independent offline reader path.

Final tests passed 93 with two expected skips in 25.79 seconds. Ruff and whitespace
checks passed. Tests cover constructor access, public-input rejection, stale/legacy
grants, parent-source changes, write/start uncertainty, exactly-once suite charges,
access-before-read, copied-label deletion before saved recovery and corruption of
access/job/worker/process inputs. The outer suite reservation and confirmation
access event are checked before the one private read. The fixture's custodian
creates/hashes its synthetic inputs before that trace; this is not an acquisition
or real-data exposure measurement.

Positive worker tests deliberately replace the boundary and memory check with an
authored test stub. They run the fixed worker against synthetic labels only and
do not attest OS privacy or memory enforcement. The actual macOS profile still
refuses before any label read because its data-memory limit is unqualified. The
two production-profile scoring tests skip for that reason. Its separate synthetic
OS path-denial probe still runs. No real confirmation label, provider or independent
partition was accessed. Source snapshots and initial/intermediate logs remain.
No full default/Bayes, installed or frozen scientific matrix rerun is claimed.
Part 5, independent task admission and private scorer qualification remain open.
