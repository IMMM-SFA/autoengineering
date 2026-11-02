# WIND source access and point preparation

Status: bounded range transport, development-source metadata and one 2007 point
acquisition verified. Other years, physical binding and independent task admission
remain open.
This increment implements the data-preparation work in the full
[Part 5 plan](part-5-utility-confirmation.md), without replacing its real-task gates.

`examples/utility/wind_range.py` permits only the fixed annual CONUS v1.0.0
2007-2011 development/selection URLs. Proposed 2012-2014 reserve years refuse at
record construction. Each request carries Range, If-Match and identity encoding.
The transport refuses redirects, whole-object responses and inconsistent range,
ETag, length or encoding. Request and worst-case response-byte reservations precede
network access. Unknown responses consume the reader and cannot silently retry.
The reader is read-only and checks bounded reads, cache size and elapsed time.
Socket-operation timeouts and elapsed checks are not OS deadline or RSS guarantees.

The [source evidence](../../examples/utility/verification-wind-source-metadata-v1/README.md)
records one anonymous HEAD and 14 conditional GETs against the 2007 development
object. Only 917,504 body bytes were transferred from the 1.54 TB object. The
multipart ETag pins consistency, while individual captured ranges have SHA-256
hashes. No complete-object checksum or data admission is inferred. License and
attribution remain separate from package code in the evidence NOTICE.

The metadata identifies 8,760 rows and 2,488,136 sites. The 80 m speed/direction
arrays are uint16 with declared scale_factor 100 and fill_value 65535. It identifies
UTC and (latitude, longitude) coordinates. These attributes still need source-specific
interpretation before decoding. Weather dataset values were never indexed. Raw
ranges can contain adjacent 2007 development-data bytes, now recorded as exposed.
No reserved-year object was accessed.

Uncompressed weather chunks contain 336 x 2,976 entries, nearly 2 MB each. This
exceeds the current 1 MiB logical-read cap. A single point can require 27 chunks
for each variable. `next-point-plan.json` records a proposed 2007-only acquisition
with three stages, each capped at 128 requests and 64 MiB response bytes. It is
not executable under the current reader. Implement a separately pinned large-read
profile, nearest-grid calculation, fill-before-scaling checks, direction conventions,
UTC support and quality rules before that acquisition. Do not enlarge the consumed
metadata request or assume that a small result implies small transfer cost.

The [provider's format/version description](https://nrel.sitefinity.cloud/hpc/wind-dataset)
identifies updated WRF and boundary-layer physics for 2014 v1.1.0. Comparability
with earlier years requires a predeclared decision. No candidate performance or
2014 values were inspected to choose a favorable period. The current proposal,
blocked dossier and null frozen scientific thresholds remain unchanged.

Offline replay of captured ranges reproduces the metadata and all attributes
with sockets and process construction denied and zero new HTTP requests. The
existing utility environment supplied h5py 3.16.0 and HDF5 2.0.0. Nineteen range/HDF5
tests passed there. Base checks passed 56 tests and skipped the optional h5py case.
No dependency, lock, model, fitting, scorer or LLM provider invocation changed. Current
source pins are in `examples/utility/source-inventory-wind-source-metadata.json`.
The 224 core and 315 frozen guest sources remain unchanged. Point/resource and
physical bindings, protected confirmation, exposure and the full Part 5 comparison
remain incomplete.


## 2007 development point extraction

The [point evidence](../../examples/utility/verification-wind-point-2007-v1/README.md)
records a separately prepared direct-large-read profile. The metadata-only reader
and consumed metadata request remain unchanged. Three stages each reserve 128
requests and 64 MiB with a 4 MiB maximum logical read. Large reads share the small
read path's counters, conditional object identity and consumed-failure behavior.
No model or private-source capability is added.

The geographic stage checked all 2,488,136 coordinate rows with a frozen spherical
great-circle metric and lowest-index tie rule. It selected cell 2,411,465, about
283.79 m from the proposed point, and committed that choice before wind data reads.
The coordinate and site metadata agree within the predeclared tolerance. The source
offshore field is 1. No source quality or candidate performance chose the cell.

The acquisition used 175 GETs and 137,311,517 body bytes, within 384 requests and
192 MiB. Every one of the 8,760 UTC 2007 hours has non-fill speed and direction
within the predeclared source domains. Raw uint16 values, source-decoded values,
masks and dates remain separate. Fill is masked before division by 100. The
[provider's resource format](https://natlabrockies.github.io/rex/misc/examples.nlr_data.html)
defines this division convention. Directional from/to and north-reference semantics
remain unqualified, and no wind resource bins or modeled energy were produced.

The 105,291-byte public point artifact has a separate data NOTICE. All 175 local
captured ranges were hash checked. Their 137 MB neighbouring-source cache remains
outside bundled public example data. Full local replay recomputed geography and
all point arrays with sockets/process creation denied. A separate guarded compact
reader needs neither HDF5 nor the source cache. It validates input types/shapes,
calendar, raw/decoded consistency, masks, identities, recorded distance and costs.
It does not independently recompute global nearest-site selection. Neither check
is installed-wheel or OS privacy qualification.

Thirty-nine HDF5/range/geographic/controller tests passed. The later base regression
and documentation checks are recorded in the point archive. No model, optimization,
fitting, scoring, LLM call, installation or reserved-year access occurred. The
exposure register covers decoded 2007 data and neighbouring raw chunks. Frozen
224 core and 315 guest sources remain unchanged. Current source successor:
`examples/utility/source-inventory-wind-point-extraction.json`.

Next, establish source directional conventions, bind actual hub height/hardware,
freeze resource aggregation and missingness rules, and qualify direct/wrapped
physical execution. Acquire other development/selection years with their own
reviewed source/time policies. Keep source-version comparability, independent
exposure and protected confirmation separate. The wind dossier remains a blocked
draft, its absolute useful-gain margin remains null, and the full Part 5 objective
is incomplete.


## Hourly development physical check


A separate hourly development profile now binds the acquired 2007 80 m wind fields
to an explicit 80 m turbine using PyWake's V80 linear curves. It retains all 8,760
paired hourly inputs, rejects incomplete joint support and introduces no resource
bins. Wind-from angles and one-hour integration are recorded assumptions. Raw HDF5
direction semantics remain unqualified. Two actual wake calls produced identical
direct/wrapped scalar outputs, including 30.107811267852263 GWh for the fixed square
layout. One separately charged curve-reference call returned 30.61557908 GWh. These
are development baseline values, with no candidate or independent utility claim.
The request is consumed; all three calls have durable intents and complete receipts.
Application elapsed checks do not qualify OS deadline or aggregate RSS enforcement.
A guarded public reader verifies saved scalar parity, point/profile identity and
charges without models, processes, sockets or unrelated reads. It does not recompute
physical power. Thirty-six focused tests and 108 broader regression tests passed,
with six expected optional-runtime skips. All 224 core and 315 frozen guest sources
remain unchanged. Dossiers, independent partitions and absolute useful-gain margins
remain unadmitted. Source-version comparability, raw direction evidence, other
development years, protected scoring and full Part 5 confirmation remain open.

[Evidence](../../examples/utility/verification-wind-hourly-2007-v1/README.md).

The next source inventory is `examples/utility/source-inventory-wind-hourly.json`.


The 2007 hourly wind profile now runs through the shared supervised scientific
executor and engineering study controller. One baseline and four frozen Sobol
trials completed with five charged, stopped observations and no pending work.
The baseline matched standalone parity at 30.107811267852263 GWh. The best trial
returned 30.068129320901953 GWh, so saved application of the frozen acceptance
rule retained the baseline. The 40 m corner domain is a development qualification
domain, not the final conventional recipe. Original completed replay added no work.
A guarded archive reader verifies hashes, inputs, five saved process/watchdog
receipts, outcomes and retention without models or current process inspection.
Eighty-nine related tests passed with one optional wind-runtime skip. Core 224
and guest 315 sources remain unchanged. Private execution, raw direction semantics,
other years, source comparability, independent exposure and the full Part 5 study
remain open. No task status, independent partition or absolute margin was admitted.

[Shared-controller wind evidence](../../examples/utility/verification-wind-hourly-study-v1/README.md).


The [bounded direction-source review](../reviews/part-5-wind-direction-source-review.md)
did not establish the raw HDF5 angle convention. No model or data-object access
followed. The prior development assumption and all admission limits remain.
