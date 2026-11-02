# WIND development-source metadata

One HEAD and 14 conditional range GETs inspected the 2007 hourly CONUS development
object. They transferred 917,504 body bytes from a 1,536,888,915,822-byte source.
Every GET uses the fixed source URL, Range, If-Match and identity encoding. Full
object responses, redirects, changed identities and invalid lengths refuse.
Unknown attempts retain their reservation and disable automatic retry.

`wind_range.py` is a read-only file object for optional h5py. Its fixed source
catalogue permits 2007-2011 and rejects all proposed 2012-2014 reserve years. Request,
response-byte, read-size and cache limits are explicit. Socket timeouts and elapsed
checks do not establish an OS-enforced deadline or RSS limit. ETag consistency and
per-range SHA-256 do not establish a cryptographic hash of the complete source.

The source has 2,488,136 sites and 8,760 hourly rows. Speed/direction at 80 m are
uint16 with scale_factor 100 and fill_value 65535. Metadata says UTC and coordinate
order (latitude, longitude). These are extracted declarations, not qualified
scaling, direction conventions, time-series coverage or scientific inputs.
Uncompressed variable chunks contain 336 x 2,976 entries, nearly 2 MB. A full point
read therefore needs a new bounded profile beyond this 1 MiB logical-read cap.
`next-point-plan.json` gives concrete proposed acquisition caps without dispatch.

Captured ranges and hashes reproduce the metadata offline. The replay recovered
all attributes with sockets and process construction denied and made zero HTTP
requests. Neither inspection indexes weather dataset values. Raw captured blocks
may include adjacent development-data bytes; the exposure register records that
access. No proposed reserved object, model, fitting, scorer or LLM provider was used.

The existing utility environment supplied Python 3.12.16, h5py 3.16.0, HDF5 2.0.0
and NumPy 2.5.4. Nineteen range/HDF5 tests passed there. Base checks passed 56 with
one expected h5py skip. No environment, dependency or lock changed. The initial
write-refusal unit failure is preserved separately.

The provider documents updated WRF and boundary-layer physics for the 2014 product.
That requires a source-comparability decision before the final study is frozen.
No reserved-year values were opened to assess the change. Full source/time/grid,
weather-to-resource and physical bindings, protected scoring and independent task
admission remain open. This increment does not complete Part 5.

Data attribution and license remain in `NOTICE.md`. The exact acquisition/replay
scripts, request limits, raw captured ranges and source metadata are preserved.
