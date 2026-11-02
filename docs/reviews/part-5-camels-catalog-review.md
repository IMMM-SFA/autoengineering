# Current CAMELS catalog and archive documentation

The current [Zenodo record](https://zenodo.org/records/15529996) declares version
1.2, open access and CC BY 4.0. It lists the proposed forcing/flow archive as
3,406,626,583 bytes with MD5 `8e9a466710e8270b58f01d332a87184f`.
Anonymous metadata and exact-range documentation requests succeeded. The older
[DataCite record](https://api.datacite.org/dois/10.5065/D6MW2F4D) still contains its
registration condition. Both declarations are preserved. The current repository
provides a concrete anonymous acquisition route with stated reuse terms. This
review does not erase the older condition or license other collections.

The [saved evidence](../../examples/utility/verification-camels-catalog-v1/README.md)
contains the catalog, terms, archive footer/directory, eight in-archive documents
and the standalone README. Ten top-level requests retained 2,886,194 final body bytes.
Total network traffic and HTTP exchanges remain unknown. No forcing or flow
member was requested. The 2.81 MB directory exceeded the first local 2 MiB guard.
Inspection resumed from the saved footer under a 3 MiB directory bound within the
original 4 MiB metadata budget, without repeating any request.

The directory lists both expected basin 01491000 members under HUC02 02. This
supports the versioned parser's path recipe. It does not prove their actual
contents or membership under a verified full-archive checksum. The full archive
was not downloaded, its catalog MD5 was not verified and no full SHA-256 is known.
The responses supplied no ETag. Exact ranges and documentation CRC checks provide
local consistency checks without cryptographically authenticating object identity
across responses.

The retrieved forcing README documents basin area in square metres. The flow
README documents cubic feet per second, missing flow as -999, and the flags `A`
(measured), `A:e` (estimated) and `M` (missing). Added authored regression checks
preserve `A:e` and exclude it unless the frozen plan explicitly allows it.
Missing values remain excluded even if `M` appears in the allowed list. This
exercises the existing parser and mask behavior without changing production
semantics or selecting a policy from observed performance.

The forcing README describes the hour field as a daily placeholder. It does not
establish the physical start/end of accumulations, and the previously pinned
hour-field issue remains unresolved. The dataset summary does not resolve the
legacy calendar. Modern Daymet v4 rules still cannot be substituted. These timing
requirements remain open before causal source admission.

The summary also describes aggregate quality/area counts and separate published
model calibration/validation spinups. That aggregate metadata exposure is
recorded. The proposed study does not inherit the published validation spinup or
model output. Those diagnostics do not establish actual coverage, quality or
independence for the selected basin and years. Prior personal exposure remains
unknown. Four task dossiers and the proposal retain their original identities.
