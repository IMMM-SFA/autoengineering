# Legacy CAMELS forcing review and NoData rejection

The original [Newman et al. methods](https://doi.org/10.5194/hess-19-209-2015)
describe area-weighted daily meteorology and USGS daily discharge. The inspected
methods do not define an exact forcing interval or document the legacy leap-day
transformation. The NCAR repository root lists only a README, so that snapshot
supplies no processing implementation to establish those details. This review
leaves timing admission open.

The [Daymet v2 guide](https://daacweb-prod.ornl.gov/DAYMET/guides/Daymet_mosaics.html)
also documents 365 values annually, retaining February 29 and dropping December 31
in leap years. That convention therefore predates v4. It still does not prove
which upstream bytes or calendar transformation produced the proposed CAMELS
member. No offset, fill or date selection was chosen from performance.

The guide specifies -9999 as NoData. The CAMELS parser already rejected -999
forcing values, but a -9999 minimum temperature, or equal -9999 extrema, could
pass its finite/min-max checks. Four authored preparation regressions reproduced
this failure across both source schemas. The parser now rejects both sentinels
in every forcing variable before returning rows. Failed preparation retains only
its original claims. It neither publishes forcing nor computes a score. Flow
handling is unchanged: only its separately documented -999 sentinel maps to
missing. No valid forcing values or date/mask policies changed.

[Saved verification](../../examples/utility/verification-camels-timing-v1/README.md)
retains the four failing pre-fix tests, source snapshots and the passing focused
regression. It also pins the methods paper, guide and repository metadata.
The full PDF was downloaded, but only extracted text from PDF pages 2-5 was
inspected. That text includes aggregate basin statistics and figure captions.
This literature exposure is recorded separately from primary time-series access.
No forcing/discharge member, basin hydrograph or observation table was opened.
The earlier web PDF fetch timeout is preserved as a failed acquisition route.

Scientific admission still needs original source/interval provenance, actual
coverage and quality, causal initialization and prior-use history. The four
blocked dossiers and preparation proposal retain their original identities. This
source review and parser repair do not admit a task or qualify private execution.
