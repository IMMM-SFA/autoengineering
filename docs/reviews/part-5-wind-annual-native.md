# Native annual wind callback control

The annual callback now has one native PyWake control on macOS ARM64. It used
authored constant drivers, an authored selection fixture and the existing full
suite selection barrier. It did not acquire weather or evaluate an independent
task. The [native request and result](../../examples/utility/verification-wind-annual-native-v1/README.md)
preserve the scope and resource reservations.

One outer scoring callback opened three normalized payloads, verified 420,864
bytes and made three PyWake evaluations. It used the frozen layout, including
the authored 10 m offset of the first turbine. Annual modeled energies were
41.76507792757359, 41.6509656927988 and 41.6509656927988 GWh. Their mean was
41.689003104390395 GWh. The leap-year ratio matched the actual hour counts at the
predeclared tolerance. Identical authored drivers gave equal energies for the
two ordinary years. This does not establish comparability of real 2013/2014
source products or show a useful gain.

The prespecified fault occurred after the suite score artifact was created but
before its journal commit. Automatic confirmation retry refused. Recovery then
used the original callback work pin with private source access, model invocation
and dependency-version checks explicitly denied. Saved confirm/recover calls
added no events. The recovered receipt retains an unknown original callback
measurement. Its score and source/model identities remain pinned.

The execution-and-fault interval was 8.54 seconds. It includes callback work and
local overhead, not source preparation or the complete study. CPU, RSS and inner
wake operations remain unknown. The three native evaluations are separate from
the earlier two-call kernel parity control and outside the v21 guest register's
listed scope. They are not container starts or additional outer scoring grants.

The optional native test passed with one warning in Python 3.12.14, PyWake 2.6.20,
NumPy 2.5.2 and SciPy 1.18.0. The warning reported a possible NumPy binary
incompatibility. Import-only diagnostics reproduced it in `netCDF4._netCDF4`
through PyWake's import path. The warning is retained, not suppressed or treated
as a passing general environment check. No package or global configuration was
changed. This checkpoint does not qualify NetCDF/WRF I/O, the full environment,
other platforms or a private runtime. The initial negative import probes are
retained too. NumPy's installed warning filter explains why a filter applied
before its import did not expose the warning.

A metadata-only replay passed in the default environment with optional model
imports, processes, networking, kernel execution and private driver opening
blocked. The public archive contains no private binary drivers or private kernel
journal. This is a producer-metadata verification, not OS attestation or an
installed-package qualification. The default adjacent regression passed 120 tests
with one expected optional-native skip. The native test was run once separately,
and repository lint passed. No full default suite was rerun.

The first temporary-copy replay failed on macOS's `/var` alias. Resolving the
owned temporary path corrected that reader issue without weakening the store's
symlink checks. The initial failure remains recorded. The later relocated reader
passed and rejected a modified work artifact even with refreshed archive checksums.

Qualified private runtime/owner-loss handling, common cost/report integration,
installed execution, real source admission and the four-family independent study
remain open. All four task dossier identities are unchanged.
