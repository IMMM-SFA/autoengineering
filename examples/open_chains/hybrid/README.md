# HOPP wind, solar and battery dispatch

Adapted from [HOPP example 03](https://github.com/NatLabRockies/HOPP/blob/v3.4.2/examples/inputs/03-wind-solar-battery.yaml).
HOPP is BSD-3-Clause. We use the tagged solar, wind and price files listed in
sources.json. The reference has 50 MW PV, ten 5 MW wind turbines, an 80 MWh /
20 MW battery and a 50 MW export limit. Resource year is 2012; the 2015 price
factors define a separate scenario, not coincident observed market conditions.

HOPP retains its coupled simulation internally. The autoengineering graph exposes
its PV, wind, battery, SOC, grid and price outputs, then computes hourly revenue.
It does not pretend that dispatch feedback is a feed-forward physical component
network. Gross energy revenue equals exported hourly kWh times price factors
times 0.04 USD/kWh. Capital costs, degradation charges and terminal energy value
are omitted. Initial SOC is 10 percent. Both policies have perfect knowledge of
the next 24 hours, and grid charging is disabled. This is a design scenario,
not a validation against measured plant behavior or evidence of economic optimality.

Candidates are the upstream one-cycle heuristic reference, simple CBC dispatch,
and CBC with a five-percentage-point upper dispatch SOC guard band. The guard-band
candidate was added after the first annual CBC run exceeded the already declared
SOC screen. It is an explicit additional hypothesis. Hardware, resource inputs
and physical screens remain fixed.

All outputs must be finite and share 8760 hourly steps (120 in smoke mode).
Screens retain the initial adapter tolerances: SOC 9-91 percent around the 10-90
operating targets, battery power within 20.1 MW, grid export <=50.001 MW, and
export no greater than generation plus battery power plus 1 kW. Grid import below
-1 kW is rejected. These are numerical/model tracking screens, not a certification
of strict 10-90 percent SOC compliance. Report actual minimum/maximum/final SOC.
An infeasible policy retains its raw arrays and revenue but cannot be selected.

The full simulation uses HOPP's physical battery output rather than assuming its
linear dispatch prediction is the realized SOC. CBC's superior short-run objective
does not exempt it from the annual screen. The five-day smoke mode is only an
execution check, and the remaining annual outputs are never scored in smoke mode.
