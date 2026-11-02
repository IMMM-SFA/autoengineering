# Solar equipment source review

The current public metadata paths do not resolve the selected site 2107 equipment
join. The original prize metadata still has a null selected-AC `source_id`, null
module-to-inverter links and empty string topology. The trusted reviewer continues
to return named blockers. No mapping was inferred from names, ordering or matching
interval codes.

The pinned provider dictionary names legacy metadata paths. Those prefixes now
return empty listings. A bounded bucket-root inspection located the current
`pvdaq/parquet/` branches. Their inverter and module tables contain 165 and 166
records respectively, with zero site 2107 rows. They therefore cannot repair this
prize site's joins. The attempted regular CSV site record and regular site-specific
metrics object returned 404. These results apply to the exact inspected snapshots,
not every possible source or future update.

The [provider change log](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/change_log_2023_Solar_Data_Prize_20250227.pdf)
documents a correction to inverter 15's header: the duplicate `i` in
`inv_15_ac_power_iinv_149653` was removed in `2107_electrical_data_v1.csv`.
That is a header correction, not an equipment or clock attestation for selected
inverter 01. The latest listed
[prize change log](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/change_log_2023_Solar_Data_Prize_20260519.pdf)
adds 2025 data increments without stating an equipment/clock repair. No measurement
object was opened to compare old/new data bytes. Source versions must retain
separate identities until acquired bytes are checked. The CSV parser's exact
header and byte-hash checks remain in force.

[Saved evidence](../../examples/utility/verification-solar-equipment-v1/README.md)
retains all 17 top-level attempts: 15 successful responses and two 404s.
Successful bodies total 341,350 bytes. Wire traffic and total HTTP exchanges are
unknown. The first ten-key metrics listing was truncated and was not paginated.
No catalog enumeration or observation download followed. Existing DuckDB 1.5.5
read only the supplied local metadata tables with extension installation and
autoload disabled. No dependency or global configuration changed.

The six adjacent solar regressions passed 95 tests. They cover metadata refusal,
exact CSV identity, explicit clock/support policies, alignment, missingness and
partition custody on authored data. They do not establish actual site behavior.
The selected metadata hash, four task dossiers and proposal remain unchanged.

Solar admission still requires an explicit channel/device/module binding or an
independently justified model specification, electrical topology where required,
clock/DST and per-sensor support/availability evidence, actual coverage/quality,
source rights and prior-use history. The next admission action needs that evidence
or a separately reviewed task/source choice. Another guess at a device index or a
fixed timestamp offset cannot close this source boundary.
