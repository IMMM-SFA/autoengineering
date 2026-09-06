# Workflow roadmap

Autoengineering is a work in progress. The package can describe systems, evaluate supplied models,
test replacements, and optimize declared configurations. The next work is to connect those pieces
and test a broader range of model improvements. This roadmap defines intended outcomes, not a
release promise or authorization to run experiments.

## Current boundary

Whole-system BO has passing Release A evidence. Full-observability function-network BO has a
passing research gate. Partial-observability BO remains experimental after adverse comparisons,
including the common terminal utility experiment. Its replacement matrix was not permitted after
the development gate failed. The final research comparison remains blocked. See
[BO status](bayesian-optimization-status.md) for the evidence.

A passing gate in one layer does not complete the workflow. The following packages address the
remaining gaps.

## 1. Integrate the model DAG

The repository already has a `System` graph and an immutable function-network representation.
We need a common model DAG that connects those records to research candidates, data, model
implementations, and experiment lineage.

The design should identify nodes and model versions, parameter domains, ports, units, time support,
training and evaluation data, observation availability, costs, and terminal objectives. It should
also make hidden arithmetic between components explicit where practical. Feedback and coupled time
stepping need an explicit boundary because current function-network execution requires a DAG.

Complete this package when one example can move from research candidate to execution and BO using
consistent identities and dependencies. Check round trips, incompatible ports, missing observations,
and cycles. Avoid adding a second graph that disagrees with the first.

## 2. Define the harness interface

Use the existing runnable and evaluator contracts as starting points. Define how a model adapter
is prepared, validated, executed, and inspected. Include seed handling, data splits, resource
estimates, artifacts, progress, errors, and interruption behavior. Separate model training from
inference when the model needs both.

The same harness should serve scripts, the CLI, and the web app. Its implementation may be a
service used by the app, with its controls presented as an experiment workspace. That choice is
still open.

Complete this package when the same example produces equivalent scientific records through a
script and the public interface. Include an interrupted run, an incompatible adapter, and a model
failure. Preserve the existing BO recovery contract and explicit failure states.

## 3. Add model improvement choices

Implement adapters and experiment paths for parameter changes, alternative parameterizations,
simple statistical models, basic ML, and full surrogate deep learning models. Start with methods
that have suitable data and an affordable comparison. Support component replacements and system
emulators as distinct roles.

Use the [proposed criteria](model-improvement.md) to assess data, compute, and potential gain.
Persist each assessment and its uncertainty. Do not make automatic method selection a public
claim until the criteria have been tested against measured outcomes.

Complete an initial version when representative cases show why a method was eligible, what it
cost, and whether its system gain justified it. Include a case where a simpler method wins and a
case where missing data prevents a learned model. Preserve the evaluation split during selection.

## 4. Build the interactive web app

We want an eye-catching dynamic app that makes the workflow understandable and useful. Its central
view should be an interactive model DAG linked to an experiment workspace and result views.
Use a restrained dark theme, earth tones, readable labels, and accessible status indicators.

The intended flow is to open a system, inspect a component, compare researched alternatives,
configure a bounded experiment, follow progress, and inspect results. Selecting a graph node or a
trial should update the relevant plots, sources, cost, and evidence. Keep animation purposeful,
such as showing execution progress or a selected path through the graph.

The app needs visible run controls, experiment lineage, before-and-after results, uncertainty,
constraint failures, and cost comparisons. Preserve failed and reverted trials in those views.
Export the configuration and underlying data with every shared result. The harness may be exposed
inside this workspace, but the app should use the same execution contract as the CLI.

Complete the first app slice when a user can run and inspect one checked example through that full
flow, recover from a failed invocation, and export reproducible evidence. Browser and CLI results
must agree. The web app is planned and is not shipped in this revision.

## 5. Expand examples and visualizations

Additional examples are being developed in another session. Integrate them after their code, data,
and evidence are available. The [current index](../examples/README.md) lists only checked examples.

Coverage should include different graph shapes, real and synthetic data, parameterization swaps,
statistical and ML replacements, a deep surrogate, missing observations, and an adverse result.
Each example should state its data source, purpose, baseline, run command, expected artifacts,
compute needs, and limits. A demonstration on fitted data must not be presented as forecast skill.

Add linked time series, residual views, parameter and objective traces, experiment trees, cost and
accuracy comparisons, and uncertainty where the run produces it. Keep empty or unavailable views
explicit. Use static exports for reports and interactive views for exploration.

Complete each example when it runs from a clean checkout with documented requirements and its
plots reproduce the recorded values. The initial app should reuse those artifacts.

## Order and stop conditions

Settle DAG identities and the harness contract before wiring app execution or automatic method
selection. Example development and read-only result views can proceed alongside that design.
Broader ML and surrogate work depends on the data and comparison criteria, not on app completion.

Do not relax failed BO gates to unblock unrelated roadmap work. Preserve frozen protocols and
negative results. Stop any new pilot at its declared budget or when its prerequisites fail. Record
what remains blocked, deferred, or untested before choosing the next experiment.
