# Engineering envelope native registration

The revised engineering recipe now has a supplied executable registration:
`examples.utility.engineering_load_envelope_native:execute`. It returns a typed
native result that the existing supervised driver and campaign reader accept.
This connects the development recipe to the controller interface. It does not
freeze or run the four-family comparison.

The registration accepts the declared ground/load envelope, linear source-current
domain [0.01, 0.1] A, 20 SLSQP iterations and at most 24 supplied scenarios.
Its total model-call allowance must cover optimization, one fresh corner check
and all fresh scenario checks, and cannot exceed 64. Unsupported rules, domains,
forcing, duplicate identities and support/scenario identity collisions refuse.

The optimizer target remains 0.62001 V. Final native physical checks retain
0.62 V, finite outputs, residual at most 1e-10 A and at most 100 solver iterations.
The controller's authoritative candidate evaluation remains required. Its
all-case power and useful-gain checks do not come from a driver success flag.

The previous result schemas could not represent a fresh support solve outside
the scored population with its correct counter scope. New result v3 adds
`support_solves` and `optimizer_target_met`. Support work counts toward the same
inner-call ceiling and has separate cost records. Shared driver snapshots remain
cumulative. Final driver counters, scored-scenario counters and support counters
remain separate. Old v1/v2 records and resource exports are unchanged.

One new direct registration test on the same 24 public development cases used
35 root model calls and constructed 26 OpenMDAO Problems. All 26 cleanup calls
returned. Native physical checks passed. The exact buffered optimizer-target
flag remained false. OpenMDAO's atomic nonlinear-group relevance warning was
retained. These 35 calls are a separate registration regression, additional to
the earlier conventional profiles' 46 calls. Those profiles were not rerun.

A supplied fixture result passed actual worker supervision, original receipt
verification and recovery with new worker launch denied. This tests the v3
wire/recovery path. The actual OpenMDAO registration test ran directly in the
optional environment. Complete source-closed supervision of that actual recipe,
protected private execution, CPU/RSS qualification and independent confirmation
remain open. The public test uses an authored fixture job identity.

The [verification archive](../../examples/utility/verification-engineering-envelope-registration-v1/README.md)
retains the initial failed recovery test and its correction. The test incorrectly
deleted a frozen source, which recovery correctly refused. The corrected test
keeps source verification and forbids another worker launch.

The focused corrected regression passed 58 tests with two optional skips.
The OpenMDAO environment passed 13 tests, including the direct registration
check. Adjacent controller, callback, report and documentation checks passed
65 tests with one optional skip. Final common-reader, decoding and documentation
checks passed 51 tests with one optional skip. These runs overlap.
A core-only wheel built and installed offline. Its relocated reader
decoded the saved result outside the checkout with model imports and external
execution denied, and rejected removed support work. This is local reader
qualification. The full default suite and other platforms were not rerun here.

The subsequent [actual source-closed controller check](part-5-engineering-envelope-supervision.md)
passed supervision and fresh scoring with the same public recipe. Its separate
49 process receipts and 83 root model calls close that local supervision gap.
Protected private execution and independent confirmation remain open.
