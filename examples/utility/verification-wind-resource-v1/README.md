# Supplied wind resource implementation

The wind implementation now accepts an explicit joint direction/speed probability
table. It no longer requires the bundled Horns Rev climate for the new profile.
The legacy bundled-resource interfaces and serialized records retain their shapes.
All new resource tables used here are hand-authored synthetic fixtures. No real
weather, independent confirmation or private scoring was performed.

## Contract

`WindResource` binds uniform direction bins, increasing speeds in m/s, joint bin
mass, turbulence intensity and a fixed 8760-hour annualization. It rejects invalid
dimensions, nonfinite/negative values, nonunit mass and unsupported grids before
model imports. Limits are 72 direction bins, 64 speeds and 256 KiB per artifact.
There is no automatic normalization, bin interpolation or distribution fallback.

The model uses fixed NOJ/V80 with an XRSite P(wd,ws) table. It checks actual library
probabilities and compares AEP with power times supplied mass times 8760/1e9.
Coordinates and spacing/rectangle/hardware checks remain unchanged. This profile
does not admit general array ports. Primary API notes are in the
[PyWake site documentation](https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/Site).
The executed version is pinned locally to 2.6.20.

Speeds enter the model as ambient reference WS. This profile applies no shear,
height or air-density conversion. Observed-resource preparation needs a separately
frozen metadata, support, quality-mask and preprocessing contract.

Native specification and driver v2 require a resource digest and the registered
resource scenario evaluator. The original verified asset is used by TOPFARM and
fresh evaluation. Callback limits and wake/gradient entries stay separate. A native
layout remains an unscored proposal until a separate reserved physical evaluation
passes the existing required checks. Completed recovery performs no new work.

## Checks

- Base wind contracts: 62 passed, 9 optional skips in 19.33 seconds.
- Pinned wind environment: 71 passed, 4 warnings in 25.37 seconds. This includes
  legacy bundled-resource behavior, analytic weighting, calm wind, asymmetric mass,
  invalid-input preflight, native resource objectives, a separately reserved fresh
  evaluation and original-process replay. The NumPy ABI-size and existing
  TOPFARM/pyDOE2 deprecation warnings remain visible in the logs.
- The native callback energies match direct evaluation with the same resource.
  These verification calls are test controls, not a complete comparative-cost
  measurement. The process journals retain native and fresh reservations.
- The installed wheel matched 199 Python files: 190 core files and the wind example
  modules. It also included the new small synthetic fixture. The bundled demo ran
  outside the checkout with original opens and all sockets denied. Dependencies
  came from the cached wind environment without editable activation or a new solve.
  Font/cache writes used private temporary directories. Subprocess helpers were
  not denied by this model-demo guard.
- A separate base environment without PyWake/TOPFARM/OpenMDAO, Torch or provider
  packages reconstructed the caller-pinned NPZ/JSON output. It checked bounded
  archive/header shapes before loading arrays, verified explicit weighted energy
  and reproduced the summary with original opens, sockets and subprocesses denied.
  The result is a synthetic model demonstration, not an independent utility result.

The first process fixture attempted to rebind an existing execution journal and
was correctly refused. It now uses a fresh journal. Adding a real lock reference
also exposed an undeclared retained fixture lock file. The corrected fixture
declares it. Failed logs remain. No recovery, source or budget gate was relaxed.

The preceding full default suite passed 2127 tests with 106 skips before this wind
increment. These changed examples have the focused checks above. No new full
default, Bayes suite or frozen benchmark matrix is claimed here.

## Bundled example

With the optional wind environment:

```sh
pixi run -e wind python -m examples.utility.wind_resource --output outputs/wind-resource-demo
```

The directory must be absent. The command makes one synthetic evaluation and
writes its resource, prediction arrays and summary. It is not managed optimization
or private scoring. The installed reader source and caller pin are preserved as
installed-reader.py.txt and reader-pin.json. They are evidence artifacts, not
programs to execute while inspecting the archive.

Independent-resource acquisition, exposure/rights review, protected confirmation,
final task/protocol/budget admission, Linux and actual model-host conformance remain
open. The wind dossier is still blocked_draft. Public resource assets must not be
used as a way to publish private confirmation weather.
