# Annual wind comparison contract

The new [annual metadata helper](../../examples/utility/wind_annual.py) retains
all proposed 2012-2014 years and makes the 2014 source-version change explicit.
No annual source was acquired or scored for this increment.

The [saved source listing](../../examples/utility/proposals/confirmation-v1/wind-source-versions.json)
identifies 2007-2013 under `conus/v1.0.0/`. The preserved
[source review](part-5-confirmation-proposal.md) identifies the 2014 `v1.1.0`
generator change. A difference across those years can reflect both weather and
generator physics. The helper labels the claim accordingly. It does not declare
the source versions scientifically interchangeable.

`AnnualWindPlan` binds the chronological annual sources, model, geometry and
interpretation identities. Every source binds its annual object and extracted
point manifest. `AnnualWindRun` binds one frozen configuration and must contain
exactly the plan's years and source identities. The source-key/version checks
cover this historical CONUS product only.

`compare_annual` pairs conventional and candidate outcomes within each source
year. It returns annual outcomes, separate source-version summaries and an
overall mean with equal year weights. The two `v1.0.0` years therefore have two
thirds of the proposed three-year mean. Versions are not weighted equally.
Leap years retain their actual duration. This is modeled annual energy for four
2 MW V80 turbines, not energy normalized to 365 days or measured turbine output.

The caller must supply the frozen annual degradation tolerance explicitly.
Every declared year must pass, so a positive mean cannot conceal a failed annual
constraint. A zero conventional annual energy uses the direct nondegradation
inequality without division. It cannot supply the required positive development
reference for a useful-gain margin.

Scientific infeasibility, model failure, timeout and infrastructure failure stay
visible. A failed year cannot supply an energy value, be replaced by zero or be
removed from the aggregate. Its overall and affected source-stratum aggregates
remain unavailable. An unaffected stratum can still be reported separately.
Missing, duplicate, reordered or substituted annual sources refuse comparison.

These are producer metadata contracts. Authoritative execution receipts must
support the values and identities. The helper opens no source, runs no model and
does not enforce access permissions. It must run only within the trusted scoring
or report boundary after the suite's full selection barrier. It does not register
a scorer, decide useful improvement, establish uncertainty or costs, or qualify
rights, raw direction, exposure, version comparability or task admission.
Protected annual inference/scoring integration remains required. The existing
development reader still refuses reserved years and has not been broadened.

The [focused tests](../../tests/test_utility_wind_annual.py) exercise the weighting,
unpaired-source refusals, annual constraint veto, explicit failures, leap-year
duration and no-dispatch boundary using authored metadata. Together with proposal
and documentation checks, 65 tests passed. The final adjacent wind/proposal/docs
regression passed 105 tests with no skips, failures or errors, and repository
lint passed. The [verification record](../../examples/utility/verification-wind-annual-v1/summary.json)
pins the source and JUnit evidence. No production core changed and no full
default suite or real wind evaluation was run for this increment.
