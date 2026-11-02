# Annual wind confirmation callback

The [development callback](../../examples/utility/wind_annual_callback.py) now
joins the sealed annual source to the wind kernel through the existing suite
confirmation service. It executes the exact frozen layout, publishes a pinned
annual work artifact before returning a score, and supports metadata-only recovery
after a suite score-publication failure.

The model snapshot contains code and the dependency lock, never private weather
payloads. Its declared source bytes must match the actual kernel, scientific
model closure, source helper and callback. The callback verifies the unchanged
source binding, selected model, geometry, outcome contract, grant and original
charged access. It requires exact annual model-start, source-read and source-byte
reservations plus declared active time. Unsupported layouts and fixed-total-cost
use refuse before source access. A PyWake version check also precedes access.
These checks do not qualify dependency bytes or enforce an OS deadline.

The callback creates one private work scope for the grant. The source helper
reads every annual payload once. The callback verifies the complete original
read metadata before entering the kernel. The kernel journals annual starts,
preserves failed and unattempted years, and returns the existing scalar
`PublicScore` plus the annual run. The callback checks the score, exact source
and configuration identities, failure sequence and model-start counts against
the kernel completion record.

A content-addressed `AnnualWindWork` artifact binds the grant, scorer, source,
policy, original source-read evidence and kernel record. A durable callback
completion pins that exact artifact before the score returns to the suite.
The work artifact contains annual outcome values and counters, not weather,
power arrays or exception text. A successful score establishes model feasibility,
not useful comparative improvement. Annual degradation, minimum useful gain,
uncertainty and the complete route comparison still need their frozen rules.

`recover` and `public_work` verify the original completion pin and public metadata.
They reopen no private driver and invoke neither the kernel nor the dependency
version check. Recovery still works after disposable authored driver files and
the private kernel journal are removed. Altered work bytes, changed read metadata,
a missing callback completion or incomplete publication refuse recovery. The
original attempt and reservations remain charged. Recovery never scans for a
replacement pin or repeats a model.

There is one outer scoring callback, with up to one nested model start per annual
source. These counts describe different scopes and must not be added. All annual
drivers are read before kernel execution, so a model failure in an early year can
still have the full declared source-read cost. Inner work in a failed annual
attempt remains unknown.
Even successful annual work does not measure inner wake operations, CPU or RSS.
The common callback measurement covers elapsed callback time when available.
Recovered receipts retain the existing measurement limits.

The [focused tests](../../tests/test_utility_wind_annual_callback.py) exercise the
actual suite/source/kernel/receipt code using authored drivers and a substituted
backend. They cover selected-layout use, successful and failed annual work,
unsupported inputs/budgets, source-code substitution, loss before suite score
commit, missing completion, tampered evidence and replay without new work. They
do not execute PyWake or qualify a private runtime. The final adjacent regression
passed 120 tests without skips, failures or errors, and repository lint passed.
The [verification record](../../examples/utility/verification-wind-annual-callback-v1/summary.json)
pins that checkpoint. No acquired weather, real model run, installation or
container was used in this increment. The full default suite was not rerun.

This is an application-owned development callback with no CLI registration or
OS isolation. Fixed-total-cost operation, private-runtime qualification,
owner-loss cleanup, installed execution and common cost/report integration remain
open. Source rights, raw interpretation, geographic provenance and prior exposure
remain unadmitted. All four dossiers retain their earlier blocked identities.
