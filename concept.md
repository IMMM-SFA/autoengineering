# Autoengineering concept

Bayesian optimization is experimental across all backends. It helps in some cases, but
the examples do not show consistent gains across problems, test prediction, and total runtime.
More testing is needed before broader recommendations. Passing a frozen benchmark gate does not
change this experimental status.

Autoengineering asks which change to a connected model system is worth testing next. A useful
change might improve accuracy, reduce runtime, satisfy a scientific constraint, or make an
experiment easier to reproduce. The objective and acceptable tradeoffs must be stated before the
search begins.

This workflow is a work in progress. The package supports system descriptions, validation,
component replacement experiments, and whole-system Bayesian optimization. Research code also
represents component functions and observations. These pieces still need a common model DAG,
harness, and interactive interface.

## Start with the system and the evidence

A component can fit its own observations better while making the complete system worse. Its inputs
may contain upstream error, and its output may matter little to the terminal objective. Component
validation helps locate questions. A controlled system comparison decides whether a change helps.

The workflow needs a baseline implementation, a description of component connections, input data,
and a declared objective. It also needs observations or reference outputs, an evaluation budget,
and a comparison design. Missing component observations should remain explicit. Matching a
reference simulator measures fidelity to that simulator, not accuracy against observations.

The current `System` stores components and ports in a directed graph. Feed-forward execution and
function-network BO require an acyclic graph. Time stepping and feedback may remain inside a model
wrapper. A general coupled-model scheduler is not implemented.

## Research, test, and optimize

Deep research investigates alternatives and records their sources, required inputs, assumptions,
and expected benefits. The result is a cited brief and, where implementations are ready, a
`candidates.yaml` file. Literature support is a reason to test a method, not evidence that it will
improve this system.

The replacement loop executes supplied candidates and records what was kept, reverted, or failed.
Whole-system BO instead selects parameter and architecture configurations within a declared search
space. These approaches can inform each other, but their automatic orchestration is unfinished.
See the [workflow guide](docs/workflow.md) for the implemented boundaries.

## Choose the scale of the change

We want to support parameter tuning and parameterization swaps, statistical corrections and
replacements, basic machine learning, and full surrogate deep learning models. A more complex model
must justify its data and compute requirements through a bounded comparison with simpler options.

The [model improvement criteria](docs/model-improvement.md) are a proposed decision process. They
weigh usable data, total computational cost, and plausible system gain. They also allow the decision
to collect better observations, revise an adapter, or keep the existing model. The package does not
yet select or train these model classes automatically.

## Choosing how to search

For parameter optimization, start with an affordable Sobol pilot and use the
observed target difficulty, evaluation cost and response predictability to choose
whether to continue Sobol or try BO. A typical pilot is 32 calls, counted within the
total budget. Reduce or skip it for extremely expensive objectives or a small
finite candidate list. Compare total time, retain failures and capped runs, and
keep final test data outside selection. This is the current working approach;
[the optimization guide](docs/optimization.md#choosing-a-search-method) specifies
its limits, recovery boundary and research TODO.

## The interface we want

A unified model DAG should show how data and model outputs reach the terminal objective. A harness
should expose the same execution and evidence contracts to scripts and a dynamic web app. The app
should make it easy to inspect the graph, compare candidates, run bounded experiments, and explore
results without losing the underlying records. The harness may appear as an experiment workspace
inside the app. Its placement and API are open design decisions.

More examples and visualizations are needed to test this design across systems. The
[roadmap](docs/roadmap.md) describes those gaps. Existing
[background research](background_research/README.md) records the concepts behind the workflow.
