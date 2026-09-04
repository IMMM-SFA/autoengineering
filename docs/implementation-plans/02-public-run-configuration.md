# Item 2 implementation plan: public run configuration

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `8e4624c`_

## Outcome

The Python API and later CLI will load one strict YAML contract that combines a study, typed search
space, policy choice, evaluator factory, declared files, and invocation limits. Loading will preserve
declaration order and scalar types, resolve files relative to the run specification, and expose the
complete set of hashes passed to `OptimizationStudy` as input provenance.

## Public serialization contract

Add ordered `to_dict()`, strict `from_dict()`, `to_yaml()`, and `from_yaml()` methods to each
parameter type and `SearchSpace`. Parameter dictionaries will use an explicit `type` field.
Categorical parameters contain ordered scalar categories. Numeric parameters contain bounds,
scale, and ordered activation conditions. Every mapping has an exact key set. YAML uses safe load
and dump with key sorting disabled.

Add `OptimizationRunSpec` in `optimization/run_spec.py` with these immutable fields:

- `study` and `search_space`;
- policy name and frozen policy options;
- evaluator factory entry point in `module:callable` form;
- ordered, unique declared input paths;
- optional target value;
- optional maximum new evaluations for one invocation; and
- schema version.

Policy names are `random`, `sobol`, and `botorch`. Random and Sobol accept no options. BoTorch
accepts only the integer constructor options already exposed by `SystemBayesBackend`. Policy names
remain separate from `StudySpec.backend`, which continues to identify the system architecture.

## Paths, loading, and hashes

Declared input paths must be relative, normalized, nonempty paths without parent traversal. On
load, each path is resolved against the directory containing the run specification. Missing files,
directories, symlinks, and paths that escape that directory are rejected.

The evaluator entry point is imported with the run specification directory temporarily available
on `sys.path`. It must resolve to a callable. Its source file must be discoverable and readable.

Add a provenance method that resolves the explicitly supplied system YAML relative to the run
specification when needed and hashes exact bytes for:

- the system YAML;
- the run specification YAML;
- the evaluator entry-point module source file; and
- every declared input file.

Hash keys will identify the input role and declared path. The method will not inspect environment
variables, directories, imported dependencies, or undeclared files.

## Implementation sequence

1. Add parameter and search space serializers with exact schema validation.
2. Add frozen run specification construction and canonical YAML serialization.
3. Add policy option validation and scalar freezing.
4. Add safe relative path resolution and evaluator factory loading.
5. Add exact input hash collection for controller provenance.
6. Export the new public records from `autoengineering.optimization`.
7. Add focused tests for round trips, stable bytes, scalar types, invalid schemas, policy options,
   entry points, unsafe paths, missing files, and distinct hashes.

## Verification gate

Item 2 is complete only when:

- every parameter type and a mixed conditional search space round-trip through dictionaries and
  YAML without changing order or scalar types;
- the run specification has byte-stable repeated serialization and an equal fresh-process load;
- unknown keys, duplicate names, invalid options, invalid entry points, unsafe paths, symlinks, and
  missing files fail before controller construction;
- changing any semantic field or declared input changes the appropriate canonical or byte hash;
- two fresh processes produce the same canonical run specification and input hash mapping; and
- focused tests, the default suite, the Bayesian suite, lint, `git diff --check`, and Waterology
  constraints pass after the final edit.

The status document will be updated only after this evidence exists.
