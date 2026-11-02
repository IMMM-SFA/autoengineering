# Revised engineering task development reference

This [review](../../../../docs/reviews/part-5-engineering-development-reference.md)
explains the revised scope, actual run and admission limits.

`proposal.json` freezes the development question, source identities, public input
identity, physical checks, independent-reference tolerances and prospective
confirmation policy. `development-inputs.json` contains the already public 24-case
fixture. The original v2 reserve grid is not evaluated or rewritten. No private
seed or confirmation scenario was generated.

`prepare.py.txt` and `profile-baseline.py.txt` are historical producers. They must
not be rerun into their consumed proposal/output scopes. `evidence/` preserves
24 durable reservations, 24 successful observations and the final baseline receipt.
Each operation includes one OpenMDAO solve and one scalar bisection reference.
The 0.24974500426467053 W mean gives a proposed 5% gain threshold of
0.012487250213233526 W. These are development values only.

`development-reference.json` binds the actual receipt. `gain-reference.json`
binds it to this proposal, retaining `reference_bound_not_admitted`. Neither
artifact admits confirmation or applies to the original proposal/other draws.
Project source snapshots are under `source/`; the installed framework source hash
and environment versions are in the execution request.

Read saved evidence from the repository without scientific frameworks:

```sh
pixi run python -B -c 'import runpy; runpy.run_path("examples/utility/proposals/engineering-v3/verify-reference.py.txt", run_name="__main__")'
```

`verify-reference.py.txt` uses core batch replay and archived metadata. It denies
model/example imports, network, processes, private reads and archive writes. It
reconstructs values from receipts without rerunning OpenMDAO or bisection.
`reader-verification.json` records successful relocated replay and rejection of
a wrong v2 target. An initial reader field-name failure is preserved separately.
`installed-reader-verification.json` records the same replay through the existing
core-only wheel outside the checkout. Its installed payloads were rechecked. No
wheel build, dependency install or numerical solve was repeated.

Final scenario custody, complete route/matrix/budget freeze, protected runtime,
analysis and the independent four-family study remain incomplete.
