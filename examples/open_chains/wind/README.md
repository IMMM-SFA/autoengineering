# PyWake and TOPFARM at Horns Rev

Based on DTU's [Horns Rev quickstart](https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/Quickstart.html)
and [TOPFARM](https://topfarm.pages.windenergy.dtu.dk/TopFarm2/). Both are MIT licensed.
Site distribution, V80 turbine curves and the 16-turbine subset ship with py-wake.

The baseline layout is unchanged. Two deterministic SLSQP runs get 5 and 20
iterations, independently starting at the baseline. All use the same NOJ wake
model, wind directions spaced by 30 degrees and speed bins 4 through 24 m/s.
A rectangle enclosing the original positions is the demonstration boundary, not
an asserted legal lease. Minimum spacing is four 80 m rotor diameters.
The final layout is screened independently for area, spacing and finite positions.

The objective is modeled annual energy in GWh. Wind probabilities outside the
chosen speed range are not claimed to be evaluated. The frozen selection is then
re-evaluated on a five-degree direction grid without reoptimization. This is a
quadrature sensitivity check, not field validation. No observed production gains
or improved wake-model accuracy are claimed.

Record inner function/gradient calls separately from outer candidate evaluations.
A feasible iterate at the iteration cap can be scored, but remains explicitly
not_converged. A large coarse-grid gain that disappears under the finer grid is
an adverse result that must remain visible. Smoke uses four corner turbines.
