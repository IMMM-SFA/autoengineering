# Workflow tools and remaining integration

The repository already provides most of the individual steps needed for a small model improvement
experiment. The remaining work is to connect their contracts and make their results easier to
inspect.

| Layer | Current implementation | Remaining work |
| --- | --- | --- |
| System description | YAML, `System`, components, ports, and NetworkX graph queries. | A common model DAG spanning data, implementations, training, and experiments. |
| Execution | Python and command runnables, feed-forward runner, and optimization evaluators. | A harness with a consistent lifecycle and explicit state, resources, and validation. |
| Research | Project agent skills, cited briefs, and candidate specifications. | Structured method assessments and a reliable handoff to implementations and training. |
| Experiments | Bounded replacements and durable whole-system optimization. | Shared orchestration and acceptance criteria across method families. |
| Inspection | CLI output, Mermaid graphs, Markdown reports, JSONL ledgers, and artifacts. | Linked visualizations and a dynamic web app for interaction and results. |

NetworkX is the current graph implementation. Replacing it or introducing a graph database needs a
measured requirement that the existing graph cannot meet. The application design is still open.
It should consume the same harness and evidence as the CLI.

## Deep research and BO

Deep research identifies alternatives and records the evidence for testing them. A candidate file
connects that research to the replacement loop when the implementations exist. BO searches a
space supplied by an evaluator. It does not create model implementations or supply a general
training pipeline.

The function-network research layer adds observations and costs to component models. Its passing
and adverse comparisons are described in [BO status](../docs/bayesian-optimization-status.md).
Those experiments inform the design but do not settle how the full workflow should select between
parameterizations, statistical models, ML, and deep surrogates.

## Next design inputs

Use the [model improvement criteria](../docs/model-improvement.md) to compare usable data, total
compute, and potential terminal gain. Use checked [examples](../examples/README.md) to test the
harness and visualization contracts. Integrate additional examples when their evidence is ready.
The [roadmap](../docs/roadmap.md) describes the intended DAG, harness, and app behavior.
