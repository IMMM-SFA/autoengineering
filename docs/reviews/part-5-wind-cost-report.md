# Wind work in common cost reports

The new core [wind cost reader](../../src/autoengineering/utility/wind_costs.py)
joins original native annual work to accounting and comparative exports without
importing example/model code or opening weather. The versioned cost-input decoder
now accepts `utility-cost-inputs-v2` with separate load and wind callback entries.
Load-input version 1 retains its serialization and prior load-reader behavior.

Wind registration fixes the source binding, callback/kernel code, expected model
and geometry. The reader verifies the immutable task/partition, original claim,
selected model's code closure and configuration, charged grant/access, work pin,
annual failure sequence and source-read metadata. It also joins a committed score
when present. A work proof can survive an uncommitted score but cannot publish a
score or authorize retry. Wrong-role bindings refuse before their bodies open.

The reader preserves reservations, attempts, verified completions and actual
starts as distinct quantities. After an uncertain last attempt, total actual
starts stay unknown and known completions remain visible. Missing work leaves
actual quantities unknown even after successful scoring. Original reservations
are never refunded. Stable receipt IDs use grant/resource identities, so later
proof acquisition or score publication cannot create a second physical charge.

The native saved control reconstructs three model starts, three verified payload
reads and 420,864 bytes. CPU, peak RSS and inner wake calls stay unknown. The
recovered confirmation receipt also retains an unknown original callback duration.
No new model, weather read or source acquisition was needed for this join.
These are producer records, not OS attestation or complete study costs.

The [tests](../../tests/test_utility_wind_costs.py) cover actual archived native
work, missing/altered proofs, source/selection substitution, rehashed inconsistent
work, failed and uncertain callbacks, exact domain coverage, duplicate charging,
CLI report/verify and comparative export reconstruction. Comparative tests use
authored data and retain their missing-route denominator and inconclusive result.
The final cost/report/documentation regression passed 122 tests with no skips,
failures or errors. Repository lint is recorded in the verification summary.

A core-only 0.2.0 wheel contains 227 Python modules and no example modules.
All 239 selected source inputs and installed nonmetadata payloads match their
recorded hashes. It was built in a temporary source mirror and installed offline
to a separate target, without changing the checkout or installing dependencies.
An isolated process outside the checkout, with example/model imports, processes
and network blocked, reconstructed accounting JSON/Markdown and CLI report/verify.
The default accounting bytes were unchanged. Base dependencies were inherited.

The [verification archive](../../examples/utility/verification-wind-cost-report-v1/README.md)
preserves the wheel, input pins, reader and metadata outputs. This qualifies that
local installed reader only. Earlier guest images/wheels retain their original
source scope. No native/private runtime or Linux claim transfers to this new
wheel. The netCDF4 warning from the earlier native control remains recorded.
The full default suite was not rerun for this bounded core reader change.

Common wind work accounting is implemented. Full preparation/CPU/RSS/provider/
human-cost closure, qualified private execution, real task admission and the
independent four-family utility study remain open. All four dossier and proposal
pins are unchanged.
