# Solar interval-code source review

The [provider dictionary](https://github.com/openEDI/documentation/blob/7affccd25972e92c4de855ee98a20c0e85577b59/pvdaq.md)
resolves `L`, `C` and `R` as left, center and right alignment within an acquisition
interval. The review pins the document commit and SHA-256. No observation file was
requested.

The saved site-2107 metadata has 24 inverter, one meter and one other-instrument
record with `L`. The selected AC metric is an inverter average with null `source_id`.
Matching interval codes do not establish that missing join. The reported 5-15 minute
support and `PST8PDT` code still need a qualified clock/support/availability contract.
Equipment topology, quality, rights and exposure remain unresolved.

Two bounded public listings covered the selected site's root and metadata prefixes.
Neither was truncated. The metadata prefix contains only the already reviewed system
JSON and its empty directory marker. No additional mapping file was found there.
This does not exclude documentation elsewhere.

[Evidence](../../examples/utility/verification-solar-interval-source-v1/source-review.json)
and [listing metadata](../../examples/utility/verification-solar-interval-source-v1/metadata-listings.json)
preserve the scope. The original proposal, task dossier and metadata review remain
unchanged. Solar admission remains blocked.
