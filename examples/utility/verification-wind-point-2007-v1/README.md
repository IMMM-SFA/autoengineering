# Actual 2007 WIND point extraction

A prepared request selected the cell nearest latitude 41.5, longitude -70.5 by
spherical great-circle distance over all 2,488,136 source coordinates. It committed
the geographic choice before reading wind values. The selected cell is about
283.79 m away and has the provider's offshore code 1. It was chosen from geography,
not resource quality or turbine performance.

Three separately capped stages used 175 conditional range requests and 137,311,517
response body bytes, within 384 requests and 192 MiB. All 8,760 UTC hours have valid
speed and direction under predeclared fill and domain checks. Raw uint16 values,
decoded inputs, masks and dates are preserved in the 105,291-byte point artifact.
No model, optimization, fitting, scoring, provider inference or reserve-year access
was performed. Missing data are never converted to zero. Source directions remain
uninterpreted source degrees. Scientific quality and physical binding are not admitted.

The new direct-large-read profile supports up to 4 MiB contiguous reads while
sharing conditional identity checks, reservations, failure consumption and deadlines
with the small-read path. The preceding metadata profile stays unchanged. Each
stage has a cap of 128 requests and 64 MiB. Socket and application elapsed checks
are not OS deadline or RSS guarantees. Full-object cryptographic verification is
not inferred from an opaque multipart ETag and individually hashed byte ranges.

All 175 captured source bodies were hash checked. Full local replay used the
retained ranges with sockets/process construction denied. It recomputed the nearest
cell from every coordinate and reproduced all point arrays without HTTP requests.
The 137 MB raw range cache, including adjacent grid columns, remains in the local
acquisition output and is not bundled here. Its offsets and hashes are indexed.
Full nearest-grid/source replay needs that cache or the pinned public source.

The compact public reader uses only NumPy and the copied public files. It checks
archive size/type/shape bounds before array loading, source/output identities,
calendar, raw-to-decoded values, masks, recorded distance and cost totals. After
initialization it denies unrelated reads, writes, new imports, processes, sockets
and clocks. It neither loads HDF5 nor recomputes global nearest-site selection.
Both replay scopes are reported separately. This is checkout-based verification,
not an installed-wheel or protected-runtime qualification.

Thirty-nine HDF5/range/geographic/controller tests passed in the existing utility
environment. Initial base checks passed 37 with two expected optional-runtime skips.
The frozen 224 core and 315 guest sources remain unchanged. Source/development
exposure is recorded, including neighbouring chunks. Rights remain in NOTICE.md.

Other development/selection years, source directional conventions, resource-bin and
hardware/height bindings, source-version comparability, exposure, protected scoring
and independent task admission remain open. No task status or frozen threshold
changed. The full Part 5 objective remains incomplete.

The final base regression passed 75 tests with two expected optional HDF5 skips.
Nineteen documentation checks, repository lint and whitespace checks also passed.
