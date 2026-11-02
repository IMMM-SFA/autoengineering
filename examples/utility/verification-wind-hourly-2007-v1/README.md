# Hourly 2007 wind development parity

Two actual wake-model calls returned identical five-scalar outputs through direct
and Python adapter execution. The fixed four-turbine square produced 30.107811267852263
GWh under the declared hourly quadrature. A separate curve-only reference returned
30.61557908 GWh. These values describe one modeled development baseline. They do
not establish layout improvement, observed energy, uncertainty, runtime advantage
or independent scientific utility. Direct timing includes first framework import
and temporary Matplotlib font-cache construction; wrapped timing reuses the process.

The source is the previously acquired, hash-pinned 2007 80 m point, with all 8,760
hourly speed/direction pairs retained. No direction or speed bins are introduced.
The source UTC calendar is preserved. Every hour must have valid joint support;
missing values cause refusal. Each instantaneous source sample represents one hour
of power for this declared development integration rule. Leap years retain 8,784
hours rather than renormalizing to 8,760.

PyWake 2.6.20's bundled V80 has a 70 m default hub height. This new profile explicitly
uses its linear power/thrust curves on an authored turbine with 80 m hub height
and 80 m rotor diameter. It uses NOJ defaults and a flat UniformSite with TI 0.1,
no shear, and no source-dependent air-density or observed availability correction.
This is an explicit modeled configuration, not certification of installed hardware.
Installed source hashes and package versions are recorded in the request. The
[PyWake turbine guide](https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/WindTurbines.html)
describes custom hub heights and power/thrust functions. The installed 2.6.20 code,
rather than the guide's newer development version, defines this run.

Direction is assumed to mean wind-from, clockwise from north, with 360 wrapped to
zero for the model only. The [SAM WIND Toolkit CSV guide](https://samrepo.nlr.gov/help/weather_format_csv_wind.html)
supports that convention for a related distribution interface. This is an inference
for development, not proof of the raw HDF5 convention. The original decoded source
angles remain unchanged. No SAM local-time convention is applied to the source UTC
axis. Raw directional qualification, independent exposure, source-version
comparability and study admission remain open.

The prepared request allowed exactly two top-level wake invocations and one
curve-reference invocation, with durable intent before each. All three completed
in about 8.26 seconds. The scope is consumed and cannot retry. Counts do not represent
internal solver operations. The 120-second application checks do not enforce an OS
whole-process deadline or aggregate RSS bound. This run did not use the private guest,
scorer, optimizer, training workflow, reserved years or an LLM provider.

The public reader denies optional models, new imports, sockets, process creation,
writes, clocks and reads outside the public folder after initialization. It validates
artifact hashes, request and profile identity, the raw/decoded point/calendar/masks,
scalar bounds, saved parity and recorded charges. It starts no model. It does not
recompute physical power or establish that the receipts attest OS behavior. Actual
power arrays were not archived in this scalar-adapter check. Physical replay requires
the pinned wind runtime and a separately accounted scope.

The focused contracts passed 36 tests. The broader base regression passed 108 with
six expected optional-runtime skips. The frozen 224 core and 315 guest Python sources
remain unchanged. The point's source terms remain in [NOTICE.md](NOTICE.md).
This profile is outside the frozen guest wheel and is not qualified for private
inference. All task dossiers remain blocked drafts with no independent partitions
or absolute useful-gain margins admitted.
