# Solar source metadata review

The reviewer binds the exact metadata hash and selected system/channel. It resolves
the documented `sensor_name` CSV header, average-kW semantics and explicit primary
keys. Duplicate IDs/headers, changed bytes, unsupported conversions/calculations,
offline channels and boolean IDs refuse. Missing channel/inverter or module/inverter
links remain blockers. Names, order and similar labels never repair them.

The pinned site-2107 metadata resolves the header but has no explicit equipment
closure. `review.json` contains only metadata and named blockers. A complete join
alone would still not qualify equipment parameters, timestamp support, availability,
quality, exposure, a model or private execution. The review remains `not_admitted`.

The official DOE walkthrough repeats the missing links and explains the CSV header
mapping. Its page 22 also exposed four public example rows from November 2017.
The exposure register records that fact without their values. No observation CSV or
proposed 2019-2022 observations were accessed. The browser text is cited separately
from the pinned JSON. No claim of a verified full PDF byte hash is made.
