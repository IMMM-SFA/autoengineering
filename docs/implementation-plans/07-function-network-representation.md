# Item 7 implementation plan: function-network representation

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `87611ab`_

## Outcome

Add an immutable optimization description for component functions, local parameters, couplings,
scalar observations, costs, terminal outcomes, and permitted evaluation scopes. Keep this contract
outside the mutable core `System` classes. Validate it against a `System`, evaluate it through the
existing runner, and reconstruct component training tables from the ledger and verified NPZ
artifacts without importing Bayesian packages.

## Current state

`System` records components, ports, and directed connections. Runnable entry points and parameters
live in component metadata. `EvaluationAction` already distinguishes system and component scopes,
and the evaluator publishes arrays as NPZ artifacts with SHA-256 digests. The ledger stores only
scalar mappings and artifact references. It verifies file digests when appending and reading, but
there is no immutable function-network schema or component training-table reconstruction.

## Representation contract

Add `optimization/function_network.py` with frozen records for:

- component ports, including name, direction, optional data type, and optional units;
- component functions, including the matching `System` component name and runnable entry point;
- component-owned categorical, integer, and continuous parameters using the existing parameter
  records with local names;
- component input and output ports;
- scalar surrogate outputs, their source ports, deterministic reducer, and observable scopes;
- expected component cost and its unit;
- directed coupling bindings between named component ports;
- one terminal objective and zero or more terminal constraints, each bound to a declared scalar
  output; and
- network-wide and component-specific system or component evaluation scopes.

Use tuples and frozen mappings throughout. Serialize exact ordered fields to compact JSON and safe,
stable YAML. Reject unknown or missing keys when reading. Require schema version `1.0`.

Support `mean`, `sum`, `minimum`, `maximum`, and `last` scalar reducers. Each reducer must return a
finite float. Use qualified ledger names such as `routing.peak_flow` for intermediate scalar
observations so they cannot collide with terminal outcome names.

## Validation against `System`

`FunctionNetworkSpec.validate(system)` will return the deterministic topological component order
after checking all contracts. Validation will require:

1. exactly one representation record for every `System` component and no unknown component;
2. unique component names, local parameter names, port names, surrogate-output names, terminal
   outcome names, and global parameter ownership;
3. a matching runnable entry point for executable components and no entry point for source-only
   components;
4. representation ports that match the corresponding `System` port direction, data type, and units
   whenever those values are declared;
5. exactly one representation coupling for every `System` connection, with matching source and
   target ports;
6. compatible source and target types and units whenever both ends declare them;
7. no dangling, duplicated, or multiply bound coupling input;
8. an acyclic graph whose topological order agrees with the `System` graph;
9. valid parameter ownership and runnable parameter bindings;
10. observable scopes that are permitted by both the network and component; and
11. terminal objectives and constraints that reference system-observable scalar outputs.

Do not modify `System`, `Component`, or `Port` to satisfy this gate. Differences must produce a
specific validation error rather than being repaired silently.

## Evaluation and artifact contract

Add `optimization/function_network_evaluator.py` as a base-dependency module. A
`FunctionNetworkEvaluator` will validate the network once, check every action scope, and delegate
array execution and safe artifact publication to `research.runner.execute_action`.

For a system action, augment the configured terminal outcome functions with every scalar output
declared observable at system scope. For a component action, calculate only scalar outputs declared
observable for that component scope. Preserve terminal outcomes only for complete system actions.
The resulting `EvaluationResult` will contain scalar observations, measured cost, artifact IDs,
paths, and hashes. Arrays remain solely in NPZ artifacts.

Reject component actions when component scope is not declared, required parent artifact IDs are
absent, or no component output is observable. Keep existing evaluator failure classification and
artifact publication behavior unchanged.

## Verified replay and training tables

Implement a bounded NPZ reader that:

- reads a regular file once;
- checks the declared SHA-256 digest before loading;
- rejects non-NPY members, paths, duplicate logical names, object arrays, unsupported headers,
  excessive member counts, and excessive compressed or expanded sizes; and
- loads with `allow_pickle=False`.

Reconstruct one immutable component training row for each successful action and observable
component. A row will contain the action ID, component, scope, local parameter values, upstream
coupling scalar features, declared scalar outputs, artifact IDs and hashes, measured cost, and cost
unit. For replicated actions, reduce each artifact separately and average the scalar values into one
row, matching the scalar ledger observation.

Build parent-artifact lookup only from earlier verified ledger entries. Reject unknown, duplicate,
future, missing, or changed parent artifacts. Compare reconstructed scalar outputs with the ledger
values at a documented numerical tolerance. Sort tables by ledger order and component topological
order so repeated reconstruction is equal and byte-stable when serialized.

## Public surface and example

Export the immutable records, evaluator, training-row type, and reconstruction function from the
base `autoengineering.optimization` package. Do not import Torch, BoTorch, GPyTorch, or SMAC from
either new module.

Add `examples/function_network/` with a two-stage synthetic chain, a `System`, a matching function
network specification, deterministic source arrays, one system evaluation, and replay of both
component training tables. The example must use only the default environment and write run
artifacts only beneath its requested output directory.

## Tests

Add focused tests that:

- round-trip the full representation through canonical JSON and YAML;
- prove records and nested collections are immutable;
- validate the checked synthetic network and its stable topological order;
- reject duplicate components, ports, parameters, surrogate outputs, and coupling ownership;
- reject unknown components, missing components, cycles, dangling ports, missing or extra
  couplings, incompatible types or units, invalid observation scopes, and invalid terminal bindings;
- evaluate system and permitted component actions while keeping arrays out of JSONL;
- verify artifact identifiers and hashes before training reconstruction;
- reconstruct identical component tables from a fresh ledger reader;
- reject changed, unsafe, missing, unknown, duplicate, and future parent artifacts;
- execute the checked example twice and compare its scientific tables; and
- import the representation and evaluator in a subprocess that blocks Bayesian modules.

## Ordered implementation

1. Implement the frozen schema, strict serialization, reducers, and `System` validation.
2. Add schema and validation tests, then run the default suite.
3. Implement the evaluator adapter and bounded verified NPZ reader.
4. Implement immutable training rows and deterministic reconstruction.
5. Add evaluation, corruption, replay, and optional-dependency isolation tests.
6. Add and run the synthetic example twice in clean temporary output directories.
7. Update the optimization guide, example index, parent-plan evidence, and status record.
8. Run lint, default tests, Bayesian tests, scoped Waterology checks, and whitespace checks.
9. Review the exact signed candidate from a fresh Git archive. Record commands, environment,
   evidence paths, and unresolved limitations in an item 7 review.

Commit schema, evaluator, tests, example, documentation, and review evidence as separate signed
checkpoints where practical. Do not begin Item 8 until Item 7 passes its completion gate.

## Completion gate

Item 7 is complete only when the checked function network validates and round-trips, both action
scopes produce verified NPZ-backed observations, fresh ledger readers reconstruct equal component
training tables, all required rejection tests pass, base imports remain free of Bayesian
dependencies, the example replays deterministically, and the full repository gates pass at one
signed revision.

If representation semantics cannot be recovered from the durable ledger and artifacts, keep the
item in progress. Do not embed arrays in JSONL, infer undeclared couplings, weaken artifact checks,
or alter the core `System` schema to pass this gate.
