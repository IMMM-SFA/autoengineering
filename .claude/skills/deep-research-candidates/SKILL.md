---
name: deep-research-candidates
description: Investigate alternatives for a model component and produce a cited brief with executable candidates when implementations are available.
---

# Research candidate replacements

Find changes worth testing in the connected system. Read `docs/model-improvement.md` for the
proposed method assessment and `docs/workflow.md` for the execution contract. Component ranking is
an initial clue, not proof of the cause of system error.

This skill adapts feynman's research workflow. See `NOTICE`. Use only tools available in the current
session. The package itself does not search for sources or call an LLM.

## Establish scope

Use the system definition, target component, current implementation, validation results, and
terminal objective. Identify available input and response data, units, time support, compute
budget, and evaluation split. Continue within existing authorization. Ask only for missing inputs
or decisions required to conduct the research.

Write a bounded research plan at `outputs/.plans/<slug>.md`. Record the question, methods to compare,
evidence needed, source budget, and stopping rule. Consider parameter changes, parameterization
swaps, statistical models, basic ML, and deep surrogates only where their data and compute needs
are plausible.

## Gather and compare

Use `multi-hop-lit-search` where relevant. Record primary sources, methods, implementation links,
input requirements, and limits in `outputs/.drafts/<slug>-research.md`. Separate a source's findings
from inferences about this system. Record unavailable evidence rather than inventing it.

Compare usable data, implementation effort, total compute, plausible terminal gain, and uncertainty.
Include a simple baseline. A method without the required data or an affordable pilot stays blocked
or conditional. A source supporting a method in another setting does not establish local benefit.

## Prepare the executable handoff

The command below creates a scaffold and does not perform the research:

```sh
pixi run autoengineering candidates system.yaml -c <component> -o candidates.yaml
```

For each executable candidate:

- Keep `name` equal to the target component and distinguish alternatives through description and
  metadata.
- Preserve required ports and verify units, shapes, time support, and available inputs.
- Include a rationale, sources, and a `metadata.runnable` declaration for an existing Python
  callable or command.
- Test the adapter on a small input before including it in the runnable candidate list.
- Explain candidate order because the loop tries candidates once in order against the current
  retained system.

Use the checked `examples/leaf_river/candidates.yaml` as a schema example. Keep proposed methods
without implementations in the brief, with their missing prerequisites. Do not label placeholders
as executable candidates.

## Deliver

Write `outputs/<slug>.md` and `outputs/<slug>.provenance.md`. Record source access, claim support,
accepted and rejected alternatives, method assessments, implementation checks, and unresolved
questions. Check that citations support the associated claims as well as resolving to a source.
Link the brief, provenance, and candidate file. Hand off to `auto-research-loop` within the user's
existing execution authorization. A separate BO study needs an explicit evaluator and search space.
