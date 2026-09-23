# Item 6 review: Release A documentation and portability

_Review date: 2026-09-04_

_Candidate revision: `6661004`_

## Scope

This review covers the optimization guide, README and agent entry points, example index,
documentation contract tests, optional dependency boundary, Release A benchmark reconstruction,
and fresh macOS ARM and Linux x86-64 environments. Recovery correctness and benchmark fairness
also retain the detailed evidence in the item 1 and item 5 reviews.

## Documentation review

The first independent pass found inaccurate or incomplete imports, Python requirements, package
extras, path rules, floating-point wording, CLI examples, and example network labels. Each finding
was checked against code before correction. The final structural test now verifies:

- local Markdown targets;
- Click command names and optimize parameters;
- documented Python imports;
- the documented single-test node;
- Pixi tasks, Python version, and package extras;
- run fields, path rules, BoTorch defaults, recovery terms, and benchmark artifacts; and
- the checked example inventory and Leaf River cache files.

The final independent documentation pass found no remaining defect. The tests remain structural.
They do not execute every example, pip command, or CLI snippet, and they do not validate Markdown
anchors.

## Platform corrections

Fresh archive testing found two portability defects that were not visible on macOS:

1. `pixi.lock` selected Ruff 0.15.7 on macOS and 0.16.2 on Linux. The Linux version enabled a
   different default rule set. Commit `47fab5c` pins Ruff 0.15.7 on both platforms without changing
   the lint command.
2. Linux reconstruction of macOS benchmark records found 84 result mismatches at about 1e-16.
   These came from platform floating-point arithmetic. Commit `afc66b8` applies the same 1e-12
   absolute tolerance already used for derived benchmark fields while keeping structure, status,
   keys, and nonnumeric values exact. Its test accepts a 1e-15 perturbation and rejects 1e-8.
3. A POSIX race test inherited bean-box's group-writable umask and failed before reaching the race
   injection. The fixture now creates both competing directories with explicit owner-only
   permissions. The product permission check was unchanged.

The benchmark was rerun from the clean `afc66b8` revision. All 7,500 scientific records had the
same timing-excluded signature as the prior evidence, and every aggregate gate criterion was
unchanged. Commit `6661004` checks the refreshed raw records, summary, and gate.

## Exact final archive gate

Both platforms used a Git archive of signed revision `6661004`. Neither archive reused the source
worktree's `.pixi` environments.

| Check | macOS 26.5 ARM | Ubuntu 24.04 x86-64 |
| --- | --- | --- |
| Python | 3.12.13 | 3.12.13 |
| Ruff | 0.15.7 | 0.15.7 |
| BoTorch | 0.17.2 | 0.17.2 |
| SMAC | 2.3.1 | 2.3.1 |
| Torch | 2.13.0 | 2.13.0 |
| `pixi run lint` | Passed | Passed |
| `pixi run test` | 380 passed, 23 skipped | 380 passed, 23 skipped |
| `pixi run -e bayes test-bayes` | 402 passed, 1 skipped | 402 passed, 1 skipped |
| `pixi run -e bayes benchmark-release-a` | Passed | Passed |
| Base optimization import isolation | Passed | Passed |

The Bayesian suites emitted six upstream warnings in each fresh archive: two Torch JIT deprecation
warnings, one Pyro syntax warning, and three SMAC or ConfigSpace deprecation warnings. No project
warning or test failure was suppressed.

An independent portability review checked the signed revision, both lock-file selections, the
floating-point tolerance against the observed platform difference, all 7,500 timing-excluded
scientific records, benchmark provenance, the POSIX fixture correction, and the final test results.
It found no remaining completion defect.

## Result

The Release A documentation and portability gate passes at `6661004`. Whole-system optimization is
documented and verified. Function-network optimization remains outside Release A and can begin as
item 7.
