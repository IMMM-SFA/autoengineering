# Item 1 implementation plan: recovery and durable identity

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `262a984`_

_Baseline check: `pixi run pytest tests/test_optimization_system.py tests/test_optimization_ledger.py -q` (`64 passed, 21 skipped`)_

## Outcome

An optimization study will accept only a new empty directory or durable state that proves the same
study identity and one recognized ledger transition. Validation will occur while holding the study
lock and before reconciliation changes the ledger or control artifacts. The manifest will be the
last written artifact and therefore the commit marker.

## Durable contract

Add a frozen `RunIdentity` value with canonical serialization and hashing. It will bind the study
specification, search space and encoding, backend name and constructor configuration, ledger path,
committed ledger hash, declared input hashes, study seed, and original start timestamp. Backends
will expose `identity_dict()` separately from `state_dict()`, which may contain fitted diagnostics.

The manifest will contain the complete run identity and its hash. An action transition record will
contain the committed run identity hash, committed ledger hash, original start timestamp, action,
optional result, and optimizer timing. A bootstrap transition will protect initial artifact
creation. A control transition will protect a terminal stop reason and end timestamp. Each record
binds its source state and proposed change. Recovery will replay action suggestions and stop
conditions before accepting uncommitted transitions.

## Recovery state machine

The constructor will classify state before repair:

1. A new study has no control artifacts and an empty or absent in-directory ledger.
2. An interrupted bootstrap has an empty ledger and a valid bootstrap transition. Recovery writes
   the initial artifacts and manifest, then removes the transition.
3. A clean study has a valid manifest and replaceable artifacts whose identity and ledger binding
   match the invocation. Its current ledger bytes match the committed hash.
4. An interrupted evaluation has a valid pending action without a result and an unchanged committed
   ledger. Recovery records one infrastructure failure.
5. An interrupted result commit has a valid pending result. The ledger either still matches the
   committed hash or contains exactly that pending record as its sole byte extension.
6. An interrupted terminal update has a valid control transition and an unchanged ledger. Recovery
   replays its stop condition before committing the terminal metadata.
7. Any other combination is corrupt or incompatible and raises `StudyRecoveryError` without
   changing existing study artifacts or ledger bytes.

After a valid transition, write the backend snapshot, recommendation, and report. Write the
manifest last, then remove the now committed pending record. A crash at any point leaves either the
old manifest plus a provable transition, or the new manifest plus a removable transition record.

## Implementation sequence

1. Add canonical identity and strict JSON artifact readers in `optimization/provenance.py`.
2. Add stable `identity_dict()` implementations to the backend protocol, baseline policies, and
   `SystemBayesBackend`.
3. Bind `ObservationLedger.path` to the study directory and reject alternate, external, or symlinked
   paths.
4. Replace constructor recovery with locked classification, validation, and transition repair.
5. Change artifact writing so the manifest is written last and carries the identity hash.
6. Keep pending state until the new manifest commits the ledger snapshot.
7. Add focused regression tests for identity mismatches, malformed and missing artifacts, all crash
   boundaries, valid resume, byte preservation, replay, and failure atomicity.

## Verification gate

The item is complete only when all of the following pass after the final edit:

- focused recovery and ledger regression tests;
- the full default test task;
- the full Bayesian test task;
- lint and Waterology constraints on touched files;
- a replay check showing equal recommendation and canonical artifacts apart from an explicitly
  terminal end timestamp; and
- a failure atomicity check showing byte identical pre-existing artifacts after every rejected
  resume case.

The status document will be updated only after this evidence exists.
