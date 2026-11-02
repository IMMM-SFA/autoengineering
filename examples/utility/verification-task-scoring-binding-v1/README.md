# Separate selection acceptance and confirmation outcome identities

The engineering and mixed coordinators validate the task's legacy outcome_digest
against its campaign acceptance rules. Confirmation validates an OutcomeSpec
instead. These are distinct records with different digests. Requiring one field
to mean both made an executed task incompatible with confirmation.

ScoredTaskSpec, tagged utility-task-scoring-v2, now preserves outcome_digest for
selection acceptance and adds scoring_outcome_digest for the registered
confirmation outcome. TaskSpec deserialization explicitly recognizes this nested
version. Untagged tasks retain their original serialized fields, digest and direct
outcome binding. Unknown versions, an untagged extra scoring field and a missing
v2 scoring field refuse. Changing the scoring contract changes suite identity and
blocks compatible resume of an old run.

The confirmation service checks the separate scoring identity before reservation
or access. Execution validators still check the original acceptance identity.
No campaign AcceptanceSpec, engineering acceptance rule, grant or receipt was
reinterpreted. This record does not admit data, a scorer or a runtime.

The initial tests recorded four failures and one pass for the missing versioned
binding. The first focused checkpoint passed 74 tests. An actual supervised
selection using a bounded authored engineering fixture then reached a registered
primary-outcome confirmation callback without relabeling its acceptance digest.
That confirmation score is authored, not an independent-data result. The final
contract/baseline/scoring/confirmation/CLI/report/preparation suite passed 79 tests
in 14.46 seconds. Ruff passed.

A wheel built from isolated local sources matched all 201 core Python files.
Four separate installed CLI processes exercised publication interruption, refused
retry, original recovery and committed replay with the versioned task. One
authored callback and one recovery occurred. Original reservation/access stayed
unchanged. The wrapper denied sockets/child processes and imported no optional
scientific framework. No private data, container or provider was used.

An isolated installed reader reconstructed both relocated suites: the authored
CLI suite and the actually executed engineering fixture. It verified distinct
selection-acceptance and scoring-outcome digests, one public confirmation receipt,
no accounting evidence blockers and unchanged journals. Original fixture roots,
sockets and process starts were denied. A saved legacy suite retained its exact
canonical bytes/digest. Neither fixture qualifies real physics, independent
confirmation or a private execution boundary.

The earlier 711-pass/26-skip full utility checkpoint predates this increment.
Full default, Bayes and complete utility suites were not rerun. The runtime and
worker payloads remain unchanged. Selection-stage reference caching is still
unfinished: this binding defect was fixed before changing that execution path.
Independent data custody, scientific thresholds, private profiles, the final
protocol, platforms/hosts and independent results remain open. Part 5 is incomplete.


The final archive-inclusive lint scan initially found an unused Path import in the
immutable executed scenario_fixture.py copied from the authored test fixture.
Its bytes were preserved. A local .ruff.toml extends the project configuration
and excludes only executed-engineering-suite from development lint. The unchanged
core, tests and other examples pass the normal Ruff command. The failed log and
provisional terminal metadata are retained. The corrected terminal record binds
the successful archive-lint-verified.log instead of assuming a pass from a later
shell command. No scientific gate or executed source was changed.
