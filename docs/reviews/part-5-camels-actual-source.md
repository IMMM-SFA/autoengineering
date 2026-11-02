# Actual CAMELS archive and selected-source checks

The exact public CAMELS archive has been acquired and its published MD5 verified.
Trusted preparation checked the two basin 01491000 members against that archive
and validated 12,784 published daily records. No observation values, forcing
values, hydrographs, model predictions or scores were exported. The task remains
unadmitted because source timing and protected execution are separate requirements.

The [Zenodo record](https://zenodo.org/records/15529996) still declares version 1.2,
open access and CC BY 4.0. The archive is 3,406,626,583 bytes. Its published MD5 is
`8e9a466710e8270b58f01d332a87184f`; the computed SHA-256 is
`bb90fca29a5bab8f0b300787a5ab5a669a366f40ba95b6877b631a81133f7e5d`.
This replaces the earlier unknown full-archive checksum with an actual receipt.
It does not erase the older DataCite access declaration or decide legal ownership
of every upstream product.

The original download stopped at its logical 900-second check after retaining
2,726,297,600 bytes. Its failure remains. One explicit Range continuation retained
and rehashed that prefix, downloaded the remaining 680,328,983 bytes, and verified
the complete published checksum. Three logical HTTP requests were dispatched,
including the metadata request. HTTP exchanges, total transfer overhead, CPU and
RSS remain unknown. The first interval was 902.79 seconds; the continuation
interval was 198.36 seconds. Prefix rehashing and other preparation are outside
the latter interval. These are not a complete total-cost measurement.

The first implementation checks elapsed time between buffered reads. Its socket
timeout is not a proven total bound on one buffered read, so the originally
declared 30-second overrun bound is not claimed. The continuation added a real-time
signal timer for its active HTTP operation. Neither control qualifies the private
scientific execution runtime.

The first trusted inspection froze hour zero from the supplied basin-mean README.
The actual member has hour 12 on every record. The existing parser refused that
mismatch before returning rows. The refusal is preserved. A separate declaration
then used the literal hour 12, already supported by the parser, with the same
published dates, source bytes, windows and A-only mask. No date or hour shift was
applied, and no physical interval was inferred. That inspection passed the
existing archive, schema, finite-value and complete-date checks.

| Frozen window | Published rows | Usable A-flag flow rows |
| --- | ---: | ---: |
| Warmup, 1980 | 366 | 366 |
| Fitting, 1981-1999 | 6,939 | 6,898 |
| Selection, 2000-2004 | 1,827 | 1,736 |
| Proposed reserve, 2005-2014 | 3,652 | 3,467 |

The proposed reserve has 93 estimated `A:e` entries and 92 missing `M` entries.
Both are excluded by the unchanged A-only mask. Counts are trusted preparation
metadata, not candidate diagnostics. No period was chosen or changed from those
counts. No missing driver, observation, date or flow value was filled.

The trusted programs necessarily received driver and label values to perform
those checks. Their [exposure record](../../examples/utility/verification-camels-acquisition-v1/trusted-preparation-exposure.json)
distinguishes that access from the metadata exported to the advisory context.
It must be reconciled with later custody admission. It does not claim that no
process accessed reserved values or that a protected runtime is qualified.

The hour conflict is now concrete source evidence. Complete published Gregorian
dates still do not prove the original Daymet v2 leap transformation or physical
daily support. Method searches found interpolation descriptions for newer
[CAMELS-SPAT Daymet v4 R1](https://hess.copernicus.org/articles/29/5791/2025/index.html)
and MACH products. Those methods were not transferred to this legacy source.
Only method search text was inspected; direct PMC access returned a browser-check
page. No figure or hydrograph was opened.

The [archive](../../examples/utility/verification-camels-acquisition-v1/README.md)
contains metadata receipts, source/plan hashes, both inspection definitions,
quality counts, original failures and guarded replay code. The 3.41 GB source
archive stays in an owner-private ignored output directory. It is not bundled
with public report inputs. No scientific model, fitting, confirmation score,
agent host or container ran. The adjacent source/preparation regression passed
86 tests. Current task dossiers and the original proposal remain unchanged.
