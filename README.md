# Autoengineering

Autoengineering is a work in progress for improving systems of connected models. It combines
component validation, deep research into alternatives, bounded replacement experiments, and
Bayesian optimization (BO). The aim is to improve the system's measured performance while keeping
its data, assumptions, computational cost, and experiment history visible.

The Python package and command line workflow run today. We still need to connect the existing graph
and function-network code into a unified model DAG, define a harness interface, and build a dynamic
web app for running the workflow and exploring results. More examples, visualizations, and methods
for improving models are also needed.

## What works now

| Capability | Current scope |
| --- | --- |
| Describe a model system | YAML components, ports, connections, graph queries, and Mermaid diagrams. |
| Validate and prioritize | Array metrics and a heuristic ranking of component weaknesses. The ranking does not estimate the gain from replacing a component. |
| Deep research | Agent skills investigate alternatives and record citations, rationale, and executable candidates. The Python package makes no LLM calls. |
| Test replacements | `auto_improve` tries candidates in order, records failures and reversions, and retains changes that improve its fitness score. |
| Whole-system BO | The Release A workflow runs sequential, constrained optimization with durable records and resume. Random and Sobol search are available alongside optional BoTorch. |
| Function-network research | A component representation and full-observability BO backend have checked evidence. Partial-observability BO remains experimental after failed comparison gates. |

See [workflow and architecture](docs/workflow.md), [optimization](docs/optimization.md), and
[current BO evidence](docs/bayesian-optimization-status.md) for contracts and limits. Passing a
benchmark does not establish that the workflow is complete or that it will improve a new model.

## Try it

Run commands from the repository root. Pixi installs the package in editable mode with Python 3.12.

```sh
pixi install
pixi run python examples/signal_chain/run_workflow.py
pixi run python examples/leaf_river/run_auto_research.py
```

The signal example uses synthetic data. Leaf River uses checked observation files. The
[example index](examples/README.md) describes all six examples in this revision.

Start and resume the offline optimization example:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --max-new-evaluations 3
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --resume
```

Here `system.yaml` is resolved from the optimization file's directory. This example uses Sobol.
Install the optional environment for a run configured with `policy: botorch`:

```sh
pixi install -e bayes
```

Outside Pixi, the package extras are:

```sh
python -m pip install -e .
python -m pip install -e '.[bayes]'
python -m pip install -e '.[bayes,benchmark]'
```

The `benchmark` extra adds SMAC for comparisons. SMAC is not a public CLI search policy.

## How the workflow fits together

1. Describe the components, connections, observations, and system objective.
2. Run the baseline and inspect component and terminal errors.
3. Research plausible changes and assess whether the data and compute can support them.
4. Test executable replacements or optimize a declared parameter and architecture space.
5. Compare system outcomes, constraints, cost, and failures. Keep the evidence for every trial.

Deep research proposes changes. The replacement loop measures supplied implementations. BO chooses
configurations within a declared space. Connecting these steps into one controlled workflow is
still in progress. The [model improvement guide](docs/model-improvement.md) proposes criteria for
choosing a method, including a decision to collect data or retain the baseline.

## What we still need

- A model DAG that connects model implementations, parameters, data, observations, costs, and
  experiment lineage across research, execution, and optimization.
- A harness interface for adapting models, validating inputs and outputs, running experiments, and
  exposing consistent results to the CLI and app.
- An eye-catching dynamic web app with an interactive DAG, experiment controls, progress, linked
  result views, and access to the evidence. The harness may be presented inside the app.
- More examples and visualizations, including adverse results and comparisons at equal budgets.
  Additional examples are being developed separately.
- A range of model improvements: alternative parameterizations, simple statistical models, basic
  machine learning, and full surrogate deep learning models.
- Tested criteria that weigh data availability, computational complexity, and potential improvement
  before choosing among those methods.

The [roadmap](docs/roadmap.md) gives the prerequisites and completion criteria for this work.

## Commands

Run commands with `pixi run autoengineering`.

| Command | Purpose |
| --- | --- |
| `describe <system.yaml>` | Describe components and connections. |
| `graph <system.yaml>` | Print a Mermaid graph. |
| `components <system.yaml>` | List components and model types. |
| `validate <system.yaml> -c <name> -b <baseline.csv> -s <simulated.csv>` | Compare component arrays. |
| `report <system.yaml> -r <results.json>` | Report saved validation results. |
| `candidates <system.yaml> -c <name> [-o candidates.yaml]` | Scaffold candidates. This command does not search the literature. |
| `improve <system.yaml> -C <candidates.yaml> --chain <module:factory> -b <observed.csv> -O <output>` | Run the bounded replacement loop. |
| `experiments <autoresearch.jsonl>` | Render an experiment tree. |
| `optimize <system.yaml> <optimization.yaml> --workdir <path>` | Start or resume whole-system optimization. |

The [workflow guide](docs/workflow.md) describes the Python interfaces. The Claude agent and
research skills under `.claude/` provide an agent entry point to the same package.

## Development

```sh
pixi run lint
pixi run test
pixi run -e bayes test-bayes
pixi run -e bayes benchmark-release-a
pixi run -e bayes benchmark-full-network
```

The [documentation index](docs/README.md) separates current guides from frozen research protocols
and evidence. Development and review of the BO branch used OpenAI Codex with GPT-5.

## License

BSD-3-Clause. Copyright (c) 2025, Battelle Memorial Institute. Research skills adapt feynman.is and
alphaXiv's openresearch-cli. See [NOTICE](NOTICE) for attribution.
