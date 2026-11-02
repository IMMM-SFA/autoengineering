# Installed wind archive reader

A local wheel installed into a temporary Python 3.12 venv reconstructed the two
wind-scenario-v2 evaluations from a copied archive outside the checkout. The
reader ran with `-I` from that temporary directory. During replay, guards denied
original checkout access, scientific imports, subprocesses and network sockets.
All 183 archived sources, original process stops, job/result bindings and physical
checks verified. Both modeled energies remain 37.06343379120568 GWh.

`offline-reader.json` and `reader.log` record the result. `check-reader.py` takes
archive, forbidden checkout and output arguments. The archive preserves original
absolute path strings as provenance without reopening those locations. It contains
the original batch and already bound archived-sources, excluding captured inputs.

`build.log` retains an initial failure: no installed `build.__main__` was available.
`build-setuptools.log` records the successful local setuptools wheel build.
`install.log` records installation with `--no-deps --no-index`. The venv uses base
environment dependencies through system site packages, with the installed package
origin checked explicitly. This does not establish a minimal-dependency install.

Only the saved wind archive reader is qualified. Installed wind execution, Linux,
another actual host, independent weather and utility confirmation remain unrun.
No model or provider was invoked by this check. The temporary venv is disposable;
the script, wheel hash, result and source inventory preserve the check's identity.
