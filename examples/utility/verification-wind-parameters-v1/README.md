# Wind parameter and supervised scenario checks

The new example profile keeps turbine coordinates as scalar parameters under fixed
hardware and an exact parameter rectangle. Geometry checks run before wake
execution. Model identity stays fixed across configurations. Context creation can
bind a caller's captured source directory.

Native proposal records preserve separate wake/gradient callback entries, failed
or unresolved callbacks and frozen limits. They admit only four turbines and the
30-degree native objective, with at most 128 combined callback entries. These are
not inferred inner wake-solve, derivative, CPU or coupled-residual counts. Every
proposal requires fresh evaluation. A physically tolerated point outside the exact
parameter domain retains its result and work trace but yields no configuration.

The final wind subset passed 26 tests with five warnings in 12.03 seconds. The
base subset passed 18 with four optional-runtime skips. Documentation passed 19
and Ruff passed. Earlier files retain intermediate checks. One captured-source
mutation test initially expected the digest error but correctly hit the size
mismatch first; only that test expectation changed.

The first real supervised probe produced a valid direct energy value but its
required finite check was unregistered. The unavailable check vetoed eligibility.
That one stopped process and its source/journal remain in wind-scenario-v1.
The finite check is now registered, with a positive required-check regression.

Fresh wind-scenario-v2 runs direct and wrapped evaluations of the four Horns Rev
corner turbines in two source-bound processes. Both return modeled annual energy
37.06343379120568 GWh. All required checks pass. Completed replay adds no physical
reservation. A base-environment reader verifies both original jobs, bindings,
process completions and results plus 183 archived source files. During that read,
scientific imports, process/network dispatch and original captured-source access
are denied. The source archive copies only bytes verified against original job
references, before installing those read guards.

This is bundled-distribution development, not independent weather confirmation.
The direction step is numerical configuration. The public wind route/native
process bridge, prelaunch geometry infeasibility classification, real task
admission, installed execution and relocation remain unqualified. Nothing here
supplies a comparative scientific utility result. The full Part 5 goal is active.
