# Item 1 recovery review

_Review date: 2026-09-04_

_Base revision: `262a984`_

_Reviewed state: live uncommitted item 1 diff in the isolated implementation worktree_

Review result: no implementation defect remains in the item 1 recovery and identity scope. The
final broad completion gates still need evidence from the saved post-review state.

## Must fix

No implementation findings remain.

The implementer refreshed the broad completion gates after the review. The results are recorded in
`docs/implementation-plans/01-recovery-and-identity.md` and
`docs/bayesian-optimization-status.md`.

## Should fix

No findings remain.

## Looks good

- `RunIdentity` binds the canonical study, search space and encoding, backend constructor identity,
  in-directory ledger path and exact byte hash, input hashes, seed, and original start timestamp.
- Recovery validates invocation identity, manifest structure, replaceable artifacts, ledger bytes,
  and transition source before durable reconciliation. Pending actions must also reproduce the exact
  deterministic backend suggestion from the committed ledger prefix.
- Bootstrap, action, and terminal transitions leave a durable proof across artifact writes, commit
  the manifest last, and safely remove committed residue on the next resume.
- Terminal reasons are replayed from committed state. A completed study remains terminal across
  resume, including when target configuration is omitted, and retains its original end timestamp.
- Ledger control-name and derived lock-name collisions are rejected before study creation. A new
  study durably creates an empty ledger, while a clean resume rejects a missing ledger.
- `ObservationLedger.snapshot()` returns validated entries and their exact bytes under one ledger
  lock. The recovery replay view supplies this public reader surface, its three training selectors,
  `entries()`, and canonical `record_bytes()` behavior.
- Focused default check: `pixi run pytest tests/test_optimization_recovery.py
  tests/test_optimization_ledger.py tests/test_optimization_system.py -q -p no:cacheprovider`
  passed with 119 tests and 21 optional-dependency skips.
- Focused Bayesian check: `pixi run -e bayes pytest tests/test_optimization_recovery.py
  tests/test_optimization_system.py -q -p no:cacheprovider` passed with 120 tests. Its two warnings
  are dependency deprecations from `torch.jit.script`.
- `pixi run lint` and `git diff --check` passed.
- Direct recovery probes also confirmed exactly-once interrupted SystemBayes recovery and valid
  recovery through a custom backend that reads `snapshot()`.

## Suggestions

- The exception-based fault injection covers each application write boundary, but it does not model
  an actual process kill or power loss during filesystem synchronization. Treat operating-system and
  filesystem durability guarantees as a residual integration risk.
- The replay contract is verified for the native Release A backends and for a custom backend using
  the declared read-only ledger interface. Backends that reach outside that protocol, such as by
  requiring a concrete ledger filesystem path, are intentionally not covered.
