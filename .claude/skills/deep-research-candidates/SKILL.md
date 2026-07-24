---
name: deep-research-candidates
description: Given the weakest component in an autoengineering system (from rank_opportunities), run a source-heavy, cited investigation of better replacement models and emit a swap-ready candidates.yaml plus a cited brief. Use after the Analyze step, before Improve. Adapts feynman's /deepresearch discipline to the autoengineering workflow.
---

# Deep Research — Candidate Discovery

You are finding *what to replace a weak component with*. The autoengineering
Analyze step (`rank_opportunities`) already told you *which* component is weakest;
your job is a cited investigation of alternative models for it, ending in a
**swap-ready `candidates.yaml`** that the auto-research loop consumes.

This workflow adapts feynman's `/deepresearch` (plan → gather → draft → cite →
verify → deliver) — see the repo `NOTICE` for attribution. If feynman is installed
(`.agents/skills/feynman/`), you may run `/deepresearch` for the brief and then do
the candidates step below; otherwise follow this skill directly.

This is an execution request, not a request to explain the workflow. Your first
actions should be tool calls.

## Tool discipline

Use only tools visible in the current tool set. Prefer feynman's `alpha_search` /
`fetch_content` when present; otherwise use `WebSearch` / `WebFetch`. The framework
is model-agnostic — nothing here assumes a specific LLM provider. To ask the user a
question, write plain chat text and wait; do not call an ask-user tool.

## Inputs

- The system YAML and the name of the weakest component (from `autoengineering report`
  or `rank_opportunities`).
- That component's current implementation and its failing metrics (the *why*).
- The component's input/output ports and units — every candidate must honor the same
  interface so `swap_component` preserves the graph.

Scaffold the output file up front:

```bash
pixi run autoengineering candidates system.yaml -c <component> -o candidates.yaml
```

## Step 1 — Plan

Derive a slug (lowercase, hyphenated, ≤5 words), e.g. `pet-estimator-alternatives`.
Write `outputs/.plans/<slug>.md` with: key questions (what class of model, what
inputs are available, what failure mode are we fixing), evidence needed, a scale
decision, a task ledger, and a verification log.

Summarize the plan and ask: `Proceed with this candidate-research plan? Reply "yes"
to continue, or tell me what to change.` Do not gather evidence until confirmed.

## Step 2 — Multi-hop literature search

Invoke the `multi-hop-lit-search` skill. Start from the failing component's method
and known weakness (e.g. "Hamon PET underestimates summer ET"), find review papers
and method comparisons, then **follow citations**: fetch a paper → extract its
references → fetch the most relevant of those → repeat, up to 2–3 hops. Prefer
metadata, abstracts, HTML, and official docs over PDF parsing. Record every source
URL in `outputs/.drafts/<slug>-research.md`.

## Step 3 — Draft the brief

Write `outputs/.drafts/<slug>-draft.md`: candidate models compared on the axes that
matter for this component (inputs required vs. available, known accuracy in similar
settings, implementation cost, licensing). No invented sources or numbers. Mark
inferences as inferences.

## Step 4 — Emit swap-ready candidates

This is the bridge to the loop. Fill in `candidates.yaml` (the scaffold from
`autoengineering candidates`). Each candidate MUST:

- keep `name` equal to the component being replaced (so wiring is preserved),
- honor the same input/output ports and units,
- carry a `rationale` (why it should beat the current model) and `sources`
  (the citations backing that claim),
- include a `runnable` block so the loop can execute it:

```yaml
target: pet_estimator
candidates:
  - name: pet_estimator
    model_type: evapotranspiration
    description: Hargreaves PET using Tmax/Tmin and extraterrestrial radiation.
    rationale: >
      Adds diurnal temperature range and solar geometry, correcting the summer
      underestimation of temperature-only methods.
    sources:
      - https://doi.org/10.13031/2013.26773   # Hargreaves & Samani 1985
    metadata:
      method: hargreaves
      runnable:
        kind: python
        entry: "models.pet_hargreaves:hargreaves_pet"
        inputs: [tmean, tmax, tmin, doy]
        outputs: [pet]
```

Order candidates most-promising first — the loop tries them in order and grows the
experiment tree down from each winner.

## Step 5 — Verify and deliver

Verify every `sources` URL is reachable. Confirm each candidate's `runnable.inputs`
are all available in the chain (an edge into the component, or a driver array like
`doy`). Copy the brief to `outputs/<slug>.md` and write `outputs/<slug>.provenance.md`
(date, sources consulted/accepted/rejected, verification status, links to the plan
and to `candidates.yaml`).

Final response: link `candidates.yaml`, the brief, and the provenance file, then
hand off to the `auto-research-loop` skill.
