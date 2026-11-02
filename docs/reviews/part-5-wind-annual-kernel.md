# Annual wind scoring kernel

The [annual kernel](../../examples/utility/wind_annual_scoring.py) now evaluates
one frozen layout across a complete declared annual plan. It returns the
existing `PublicScore` type and an `AnnualWindRun` suitable for the
[annual comparison helper](part-5-wind-annual-comparison.md).
It opens no weather source and does not fit, search or select a layout.

The caller supplies authorized in-memory drivers. Their normalized point
manifest binds the object identity, year, UTC axis and little-endian float64
speed/direction bytes. Complete chronological hours, joint finite support and
source domains are required. Copied driver arrays cannot be made writable.
The plan binds these manifest identities, source versions, geometry, model
closure and interpretation. All inputs and the selected layout are validated
before backend entry. The public development reader still rejects reserved years.

The kernel uses the existing PyWake 2.6.20 NOJ backend with the same V80 power/CT
curve at 80 m, four turbines, 80 m diameter and paired hourly speed/direction.
Each annual call must preserve the requested time axis and height. Returned
turbine power must be finite, nonnegative, aligned and within the 2 MW rating.
Annual energy retains actual leap-year duration and the primary mean weights
years equally. A source interpretation remains an explicit unadmitted assumption.

A fresh owner-private work directory is consumed by a durable intent. An annual
start is saved before backend construction and invocation. Model failures,
timeouts, missing dependencies and invalid physical output have distinct terminal
statuses. Later years remain `not_attempted`. Unsuccessful attempts retain unknown
inner work. No exception text, weather vector or power array is written to the
journal or returned result. Journal publication failure propagates and the
nonempty work scope refuses re-execution. No retry or recovery by model replay
is provided.

The [actual authored control](../../examples/utility/verification-wind-annual-kernel-v1/actual-result.json)
ran one 2007-shaped constant-driver kernel call and one existing hourly-profile
reference. Both returned 41.6509656927988 GWh with zero difference under the
predeclared 1e-10 relative and 1e-12 GWh absolute tolerances. There were exactly
two completed local model starts, no fitting and no acquired or reserved weather.
The supplied object identity is explicitly an authored fixture identity, not a
verified public HDF5 identity. This is numerical parity, not a utility gain or
independent confirmation. Its 8.43 second interval covers both calls and local
overhead. CPU, RSS and inner solver work were not measured.

The final focused regression passed 124 tests with zero skips, errors or failures.
It includes multi-year execution with leap years, source/policy/geometry refusal,
annual physics violations, failure states, durable publication loss and no retry.
Repository lint passed. The
[verification archive](../../examples/utility/verification-wind-annual-kernel-v1/README.md)
pins the code, request and test evidence. The full default suite was not rerun
for this example increment.

This is a kernel for application-owned trusted execution. It does not enforce
the suite selection barrier, grant private-source access, provide OS deadlines
or resource containment, qualify dependency bytes, register a scorer, integrate
costs or prove dataset rights/exposure. The source-binding callback and protected
runtime must still connect and qualify this kernel before independent use.
The earlier guest register retains its original scope. These two local wind
model starts are separately charged in this archive and are not container starts.
Four-task admission and the independent comparison remain incomplete.
