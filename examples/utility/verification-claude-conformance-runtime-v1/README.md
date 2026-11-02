# Claude conformance runtime verification

Runtime schema 1.1 implements text, all four roles, timeout, cancellation and
malformed-output repair through BatchClaudeHost. The Codex protocol/runtime 1.0
remains separate. Claude evidence readers verify original Anthropic fixed-worker
policy, exact API send intent and completed-response receipts. They bind the
prepared model, lease identifier and path. Recovery reads no key and sends no
request. Local stopping never proves remote completion. Missing token fields
remain unknown instead of taking SDK zeroes or estimated dollar values.

Owner loss remains unimplemented. Ordered execution completes the first four
cases, then stops before owner loss. Inspection remains execution_ready false.
Reports remain incomplete and live_conformance_complete false. The malformed
handler is checked in isolation by inserting an explicit unit-only owner verdict
in the test. This supplies no ownership result. Missing implementations prevent
a complete verdict even if fixture case verdicts all say passed. Unit provider
attestations also remain unacceptable as actual live evidence.

Final source passed 134 conformance, original Anthropic worker/upstream and
documentation tests in 147.27 seconds. Ruff and whitespace checks passed. This
includes legacy Codex execution, Claude's four-case prefix and original replay,
malformed rejection/repair with no science, verdict acknowledgement loss,
public offline status and original API proof rejection controls. Every altered
receipt test first verifies its unaltered baseline. Tests reject foreign API
versions/routes, retries, request hashes, scopes, changed response metadata and
unknown local stop evidence. Original source hashes remained unchanged during
the final run. Source copies, hashes, logs and JUnit records are saved here.

Two initial fault tests used a nonexistent finish_case keyword. They were corrected
to the existing BatchStore.fault hook. A subsequent proof fixture omitted its
artifacts parent. The parent is now created, and negative controls verify their
positive baseline before mutation. Initial failures remain in initial-tests.log
and focused.log. No production boundary or recovery rule was relaxed.

All tests use authored qualification/native peers and explicit provider proof
stubs. API receipt controls stub lower-level process recovery. The existing fixed
worker/upstream tests supply their separate lower-level scope. These are software
checks, not actual OS qualification, provider conformance or cost/utility evidence.
No real key, external provider, private data or independent confirmation was used.
No full default/Bayes suite, installed runtime or scientific matrix rerun is claimed.
Source changes have a new host identity; old receipts keep their original pins.
Actual qualification, owner loss, complete live authority and the remaining Part 5
requirements stay open.
