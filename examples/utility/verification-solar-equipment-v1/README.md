# Solar equipment source evidence

The [review](../../../docs/reviews/part-5-solar-equipment-source-review.md) records
which metadata paths were inspected and why site 2107 remains unadmitted.

`requests.json` records 17 top-level attempts and exact response hashes. Fifteen
succeeded and two returned 404. Empty legacy-prefix listings, bounded current
listings, two small public equipment tables and provider change logs are retained.
The first metrics listing is truncated and was not paginated. Producer scripts
ran sequentially, append request receipts and must not be rerun in this consumed
directory. No AC, irradiance, weather or other observation object was requested.

`queries.sql.txt` reproduces the local metadata counts with existing DuckDB 1.5.5:

```sh
duckdb -init /dev/null -json < queries.sql.txt
```

Run from this directory. Extension installation/autoload are disabled in the SQL.
The query starts no scientific model and contacts no data endpoint. Its saved
result has zero site 2107 records in either regular metadata table. Missing joins
in the prize metadata therefore remain unresolved. `selected-ac-review.json`
preserves the trusted reviewer result for the original pinned metadata bytes.

`source-review.json` records request/body totals, source-version findings and
claim limits. `tests.xml` records 95 passing authored solar regression cases.
No real scientific study ran. `manifest.json` pins all saved files except itself.
The four task dossiers and proposal retain their original pins. Source rights,
clock support, exposure and scientific admission are not inferred from public
metadata availability or passing software tests.
