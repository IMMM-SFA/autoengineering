# Solar equipment hypotheses and replacement decision

The user authorized reasonable equipment hypotheses, development checks and a
replacement example if those failed. This supersedes the requirement to wait
for a provider-confirmed mapping at PVDAQ 2107. All measurements used here are
development data. No proposed confirmation period was used for calibration.

## PVDAQ 2107: bounded attempt failed

The fixed candidate set used the documented ABB 27.6 kW inverter type and 80,
120, 160 or 200 Hyundai 310 W modules. Models used Faiman temperature and PVWatts
power with a declared generic -0.004/C coefficient. January-March 2019 selected
parameters; April-June provided a development check. Four nominal cases and
twelve calibrated capacity/time-shift cases were compared. Loss multipliers
were bounded to 0.8-1.05 and driver shifts to -15, 0 or +15 minutes.

| Model | Check RMSE, kW | Check bias | Check correlation |
| --- | ---: | ---: | ---: |
| Initial 120-panel guess | 9.471 | +28.10% | 0.491 |
| Fit-selected 120 panels, scale 0.8903, zero shift | 9.049 | +16.61% | 0.459 |

Both fail the predeclared screen: RMSE at most 20% of AC rating, absolute bias
at most 10%, correlation at least 0.85 and at least 1,000 daylight check rows.
This does not prove the equipment identity is wrong. Outages, shading, sensor
errors or other omitted behavior could explain poor prediction. It establishes
that these bounded hypotheses do not give a suitable simple baseline.

The source starts in November 2017, earlier than the saved metadata indicates.
The first 80 MiB prefix ended in January 2019. Its complete rows were retained;
a bounded continuation verified 256 overlapping bytes and reached June 2019.
The DNS refusal and range-limit failure preceded modeling. The three final CSV
prefixes stop before July 2019. The proposed 2022 reserve was not reached.
Acquisition receipts retain original URLs, hashes and request quantities.

## Replacement: PVDAQ 1278

Selected through [NatLabRockies/pvdaq_access](https://github.com/NatLabRockies/pvdaq_access)
and the [openEDI data documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md).
Solar Data Tools was also considered; its power-only analysis is less direct for
the requested measured-POA-to-AC comparison. Site 9068 remains an exposed existing
example, so 1278 provides a different site with explicit module/inverter links.

The saved metadata assigns 357 Sharp NU-U240F1 modules to inverter 1255 (100 kW)
and another 357 to inverter 1256 (50 kW). Total nameplate DC is 171.36 kW and AC
is 150 kW. Manufacturer details for the inverters remain unknown; use a declared
generic efficiency model rather than claiming a manufacturer-specific model.
The aggregate AC channel removes the need to guess individual sensor joins.

Daily source files contain aggregate AC, POA, ambient temperature, wind and
individual inverter power. Aggregate AC in W agrees with the sum of the two
hardware channels interpreted in hundreds of watts to numerical precision
(RMSE below 4e-15 kW). This supports the unit interpretation; it is not a
calibration certificate. Temperature F and wind mph follow channel names.

October 1-7, 2011 was used for fitting; October 8-14 was used for checking.
The nominal baseline and a multiplier restricted to 0.8-1.05 failed the bias
screen. The fitted multiplier reached the lower bound. One explicit development
amendment broadened effective DC derating to 0.5-1.05, leaving screening limits
unchanged. Eleven bounded scalar objective evaluations used only the fitting
week. One final prediction pass evaluated the selected 0.701558 multiplier.

| Refined model | Daylight rows | RMSE, kW | Bias | Correlation |
| --- | ---: | ---: | ---: | ---: |
| Fit week | 247 | 16.686 | -0.83% | 0.886 |
| Check week | 280 | 11.280 | +7.50% | 0.951 |

The check passes the development screen (20% of 150 kW, 10% bias, correlation
0.85, at least 200 daylight rows). Its period was reused after the development
amendment, so it is not an untouched independent validation result. The 0.702
factor is an effective parameter absorbing model/site discrepancies, not proof
that the site loses exactly 29.8% or has different physical equipment.

Both result schemas call the equal-weight daylight power-sum ratio
`daylight_energy_bias`. Treat it here as a bias proxy, not certified integrated
energy: source clocks and irregular intervals have not been fully qualified.
For 1278, most intervals are 900 seconds, with a few irregular intervals and a
gap retained in `alternative_result.json`. No UTC/DST correction was fitted.
This short October check supports conditional power modeling, not annual energy,
forecasting, seasonal robustness or scientific superiority of an agent route.

## Reuse and scope

The two executable development scripts are
[2107 screening](../../solar_mapping_development.py) and
[1278 baseline](../../solar_1278_development.py). The preserved
`refine_alternative.py.txt` records the one amendment and its executed fit.
Raw CSVs remain in the ignored local `outputs/solar-mapping-development-v1/`.
`decision.json` identifies their hashes and exposure. Acquisition scripts and
all three outcomes are retained here without another wheel or runtime archive.

Use 1278 as the replacement development task. The measured-input model can
compare supplied thermal/electrical choices and calibration over the same pool.
Freeze any future reserve and parameter bounds before confirmation. 2013 is an
unread candidate period, not yet an admitted or personally attested reserve.
The user's prior-use answer concerned 2107 and does not automatically cover 1278.
Full four-domain execution, future source coverage and independent confirmation
remain separate work; provider clarification of 2107 is no longer a prerequisite.

Verification: the three development guard/model tests and 19 documentation tests
passed in the existing interoperability environment (22 passed). Ruff passed for
the two new scripts and test module. Local links and the saved result summary
were checked, and raw-output exclusion was verified. No dependency installation,
full regression suite, commit or push was performed for this increment.
