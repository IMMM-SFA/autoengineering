# Item 2 run configuration review

_Review date: 2026-09-04_

_Base revision: `8e4624c`_

_Reviewed state: live uncommitted item 2 diff in the isolated implementation worktree_

Review result: no implementation defect remains in the item 2 scope. Six provenance and input
validation defects found during review were corrected and covered by regressions. The broad
completion gates still need evidence from the final saved state.

## Must fix

No implementation findings remain.

Before item 2 is marked complete, refresh the broad checks required by
`docs/implementation-plans/02-public-run-configuration.md:67-79`. The final focused tests, lint, and
whitespace check pass, but the default suite, Bayesian suite, and Waterology constraints have not
been run after the last review fix. This is a verification blocker, not a code finding.

## Should fix

No findings remain.

## Looks good

- Parameter and search-space schemas preserve declaration order and scalar category types. Exact
  field sets, schema versions, parameter kinds, and duplicate parameter names are validated in
  `src/autoengineering/optimization/space.py:120-346`.
- The shared loader in `src/autoengineering/optimization/yaml_utils.py:10-38` rejects duplicate YAML
  mapping keys at every nesting level instead of silently accepting the last value.
- `OptimizationRunSpec` freezes policy options and input paths, separates policy choice from the
  study architecture, and validates the complete public schema and policy-specific options in
  `src/autoengineering/optimization/run_spec.py:170-280`.
- Declared inputs are normalized, confined to the resolved run-specification directory, checked for
  symlink components, and required to be regular files in `run_spec.py:59-102`.
- Local evaluator modules execute their current source bytes. The loader rejects symlinked source
  paths, isolates same-named local dependencies across run directories, and hashes the source module
  named by the entry point rather than a decorator wrapper (`run_spec.py:104-167` and 319-366).
- Exact provenance covers the system YAML, matching run-specification bytes, evaluator entry-module
  source, and each declared input. A specification file that does not equal the in-memory contract
  is rejected before hashes are returned (`run_spec.py:368-397`). Undeclared files are excluded.
- The base optimization import remains free of Torch, BoTorch, GPyTorch, and SMAC. A direct import
  probe returned an empty imported-module list.
- `pixi run python -m pytest tests/test_optimization_spec.py
  tests/test_optimization_run_spec.py -q -p no:cacheprovider` passed all 69 tests.
- `pixi run lint` and `git diff --check` passed.
- Direct adversarial probes confirmed rejection of duplicate YAML and evaluator symlink escapes,
  current-source reloads, cross-directory dependency isolation, decorated entry-module hashing, and
  rejection of a run-specification file for a different in-memory contract.

## Suggestions

- Evaluator imports can execute module-level code during configuration loading. Keep evaluator
  modules free of side effects and declare every local file that can affect evaluator behavior in
  `input_files`.
- Fresh-process stability is covered within the locked project environment. Byte stability across a
  future PyYAML version or another platform remains outside this focused review.
