# Four-task confirmation preparation

The [v2 preparation package](../../examples/utility/proposals/confirmation-v2/README.md)
now carries the existing scientific proposal as executable metadata. The helper
prepares choices and can bind proposed gain rules to explicit development-baseline
reference records without opening observations or running a model. It does not
admit tasks or freeze the independent protocol.

| Task | Proposed final test | Gain and secondary policies |
| --- | --- | --- |
| Hydrology | Choptank 01491000, Daymet, 2005-2014 discharge | RMSE gain at least 5% of fixed development-baseline RMSE. Absolute volume bias at most 10%, degradation at most 2 percentage points. Physical checks required. |
| Solar | PVDAQ 2107, channel `inv_01_ac_power_inv_149583`, 2022 | RMSE gain at least 5% of fixed development-baseline RMSE. Absolute daytime energy bias at most 5%, degradation at most 1 percentage point. Qualified interval integration and equipment limits required. |
| Engineering | 24 authored ground/resistance combinations | Mean source-power gain at least 5% of fixed development-baseline power. All cases require node 2 voltage at least 0.62 V to the external reference and residual at most 1e-10 A. Worst-case power degradation at most 1%. |
| Wind | Nearest WIND Toolkit point to (-70.5, 41.5), 80 m, 2012-2014 | Mean energy gain at least 1% of fixed development-baseline energy. Every year loses at most 2% versus conventional. Geometry/spacing required. |

These rules were already proposed in the [preserved study proposal](part-5-confirmation-proposal.md).
They are study judgments, not owner-supplied numeric reference values. Every
absolute gain remains null until a positive development reference is qualified.
`DevelopmentReference` rejects confirmation scope, a conventional-route reference,
wrong metrics/units, nonfinite/nonpositive values and underflow to zero. A bound
reference still requires verification against its authoritative execution receipt.
The helper's metadata declaration cannot perform that qualification by itself.

The four current dossiers now link to this proposal and carry explicit proposed
policies. They remain `blocked_draft`, with unknown exposure, no admitted partition
and null frozen thresholds. Their previous bytes are preserved in the package.
The proposed 560-cell/480-adaptive-cell matrix, 10 paired repetitions, two budget
regimes and seven routes remain unfrozen. Numeric caps, dependency-aware intervals,
rights and protected task/scorer bindings remain unresolved. No separate person
acting as custodian or pre-existing private dataset is required. Trusted preparation
and scoring must remain separated from advisory workers.

## Source-specific metadata findings

A single anonymous site-2107 metadata GET was bounded to 128 KiB, 10 seconds and
no redirects. It returned 64,652 bytes, with SHA-256 identical to the earlier saved
snapshot. No measurement CSV was requested. The selected AC metric has no source
ID. Inverter `inv_fss_1` is a name-correspondence candidate, not an explicit channel
join. Module records have no inverter mapping, and string topology is blank.
The metadata reports 5-15 minute support, `PST8PDT` and interval code `L`.
Those facts do not define a qualified interval or equipment contract.

The [metadata review](../../examples/utility/proposals/confirmation-v2/metadata-review.json)
records those blockers and the source hash. The official
[PVDAQ documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md)
describes system-dependent sampling. The official
[wind registry](https://registry.opendata.aws/nrel-pds-wtk/)
confirms anonymous CONUS HDF5 access. The solar submission page returned HTTP 429
in the browser tool, so its preceding pinned license record was preserved. No
new rights, coverage, source-version comparability or exposure conclusion follows.

## Remaining work

Resolve the source-specific timing, hardware, rights, bounded extraction and
exposure questions. Prepare separated development/reserved inputs through the
trusted path. Profile admitted development data and qualify the task/scorer
bindings before binding absolute gains and freezing numeric budgets or the full
protocol. Prior personal use outside the recorded project history remains unknown.
The factual exposure question remains distinct from permission to continue local
implementation.

The guest checkpoint's four adverse-output cases remain open. They are one part
of G5, alongside the complete protected inference/scoring chain. G1-G8, actual
host/platform limits, independent execution and final scientific reports retain
their original requirements. The final objective remains the full Part 5 plan.

Verification passed 38 preparation/documentation tests in 0.95 seconds, with zero
failures, errors or skips. Ruff and whitespace checks passed. All 224 core and
315 declared runtime Python sources remain unchanged. The incremental source
inventory and package summary preserve the exact scope. The full default suite
was not rerun for this metadata/example increment.


A commit-pinned provider dictionary now resolves the generic solar L/C/R alignment
codes. The saved site metadata has L on its 26 listed devices, while the
selected AC metric still lacks its device join. Two bounded listings found only
the existing system JSON in the selected metadata prefix. No observations were
requested. Clock/support/availability, hardware topology, quality, rights and
exposure still block admission. No frozen proposal, dossier or threshold changed.

[Solar source review](part-5-solar-interval-source-review.md).
