# Legacy forcing methods and NoData verification

The [review](../../../docs/reviews/part-5-camels-timing-review.md) records the
methods findings, parser repair and remaining source admission limits.

`request.json` pins one bounded PDF response. A preceding web fetch timed out;
`fetch.py.txt` records the separate successful acquisition without automatic
retry. `guide-requests.json` pins two bounded guide/repository responses. Saved
body counts exclude unmeasured web requests, headers and other network traffic.
No data-series archive or member was acquired.

The paper is Newman et al. (2015), DOI 10.5194/hess-19-209-2015, distributed under
CC BY 3.0. The source PDF is retained with its attribution and license. Only text
from PDF pages 2-5 was inspected using `pdftotext -f 2 -l 5 -layout`. It includes
aggregate statistics/captions. No individual basin hydrograph was inspected.
The guide and repository inventory are primary-source documentation snapshots.

`tests-before.xml` preserves four authored failures before the repair.
`tests.xml` records the final parser/archive/preparation/site regression.
`source/` pins the repaired parser and tests. Source acquisition, software checks
and scientific admission remain separate. Historical producer scripts must not
be rerun into this consumed evidence directory.
