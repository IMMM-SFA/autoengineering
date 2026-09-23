# Documentation

Autoengineering is a work in progress. These guides describe the current workflow and distinguish
working interfaces from research results and planned features.

| Guide | Purpose |
| --- | --- |
| [Project overview](../README.md) | Current scope, installation, commands, and remaining work. |
| [Concept](../concept.md) | The problem the workflow is intended to solve. |
| [Workflow and architecture](workflow.md) | Deep research, model execution, replacement experiments, and optimization handoffs. |
| [Model improvement criteria](model-improvement.md) | Proposed assessment of data, compute, and potential gain across modeling methods. |
| [Roadmap](roadmap.md) | Model DAG, harness, dynamic web app, examples, visualizations, and method selection. |
| [Optimization guide](optimization.md) | Run configuration, APIs, recovery, and research backend limits. |
| [BO status](bayesian-optimization-status.md) | Passing and adverse evidence at the reviewed revision. |
| [Examples](../examples/README.md) | Checked examples, commands, inputs, and outputs. |
| [Background research](../background_research/README.md) | Design context and the retained literature investigation. |

## Documentation scope

The current documentation includes the guides above, example READMEs, `CLAUDE.md`, the project
agent, and the three project research skills under `.claude/skills/`. Their prose and capability
claims are maintained together. The local model benchmarks, open model chains and [figure report](../reports/model-search-results/report.html)
are integrated in version 0.2.0. All BO backends remain experimental.

The following files are historical or executable research records. Their original text is
preserved so that protocols, decisions, and claims remain traceable:

| Records | Why they are preserved |
| --- | --- |
| [BO implementation plan](bayesian-optimization-plan.md) and [implementation plans](implementation-plans/) | Original scope, prerequisites, frozen experiments, and stop conditions. |
| [Decisions](decisions/) and [reviews](reviews/) | Acceptance criteria, corrections, and evidence assessments. |
| [Benchmark artifacts](../benchmarks/) | Generated reports, raw records, invalidated runs, and adverse results. |
| [Candidate-generation](../autoresearch-candidate-generation.md), [decision-pool](../autoresearch-decision-pool.md), and [common-utility](../autoresearch-common-utility.md) experiment records | Approved run contracts and recorded outcomes. |
| [Literature memo](../background_research/multi-model-system-optimization.md), its [provenance](../background_research/multi-model-system-optimization.provenance.md), and background drafts and plans | Original source synthesis and verification history. Current implementation claims belong in the guides above. |
| [Vendored Feynman skills](../.agents/skills/feynman/) | Upstream guidance and attribution, maintained separately from project prose. |

A historical plan may describe work as future even when the current status page records its
completion. A preserved research memo may contain claims that need a new literature check before
reuse. This documentation revision does not rerun or revalidate those external sources.
