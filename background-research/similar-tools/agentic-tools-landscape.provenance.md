# Provenance: Agentic Tools Comparable to Autoengineering

- **Date:** 2026-10-25
- **Slug:** `agentic-tools-landscape`
- **Request:** “Look into similar agentic tools as autoengineering”
- **Scope:** Documented tools and research systems for scientific model construction, execution, validation, experiment selection, and parameter/structure optimization. Functional non-agentic peers were included to avoid conflating optimization with agent autonomy. No tools were installed or benchmarked.
- **Research process:** 3 parallel researcher passes (scientific-discovery agents; engineering/simulation agents; adjacent optimization platforms), lead primary-source verification and synthesis, 1 citation-verification pass, and 1 critical review pass.
- **Sources consulted:** Approximately 45 primary papers, official repositories, and official documentation pages across direct and adjacent categories.
- **Sources accepted:** Primary sources linked inline in `outputs/agentic-tools-landscape.md`. Peer-reviewed papers, preprints, repository claims, and vendor project reports are identified as different evidence types; reported benchmark results were not treated as general evidence.
- **Important exclusions:** OpenFOAMGPT and FeaGPT were not prioritized because official reusable implementations were not established. Pufibara and MOOSEnger were excluded from the main comparison because their full implementations were not public. Generic AutoML, laboratory agents, and paper-writing agents were compressed or omitted when they did not illuminate component-graph construction or optimization.
- **Name disambiguation:** SciAgents was treated as the MIT bio-inspired knowledge-graph system, not unrelated projects with the same name. SciAgent reasoning benchmarks were not treated as simulator-construction tools.

## Verification

**Status:** PASS WITH CORRECTIONS APPLIED.

The verifier checked the capability table and load-bearing claims for G-Sim, SGA, SOCIA-EVO, Modelica commissioning agents, TusoAI, AutoRA, AutoMOOSE, Foam-Agent, and OpenMDAO. Corrections applied:

1. SOCIA-EVO execution wording now distinguishes Docker-isolated full mode, direct-subprocess lite mode, and LLM-simulated fallback; it also records one-time expert verification of the initial Blueprint in the published experiments.
2. SGA resume wording now says its `resume` option preserves the output directory, while restoration of the in-memory population/search state was not established.
3. OpenMDAO's table entry now explicitly says there is no automatic structure search; structure is user-defined.
4. History/logging was separated from continuation and compatible exactly-once recovery. Unknown recovery guarantees remain marked as not established.
5. OpenMDAO comparison wording was changed from an unsupported performance judgment to concrete documented capabilities.

No broken or clearly mis-cited links were found in the verifier's reviewed set.

## Critical review and revisions

1. Added **Model Discovery Agent** because it directly combines modular mechanism discovery, structure/parameter/state inference, and experiment design.
2. Added **FunSearch** and **AlphaEvolve** as foundational evaluator-guided program-evolution references, with their different domains and availability made explicit.
3. Added publication/evaluation-domain evidence to the comparison table and labeled capabilities as documented rather than independently reproduced.
4. Replaced the recommendation to use agent systems as execution backends with a recommendation to evaluate underlying MOOSE, OpenFOAM, and Jutul solver interfaces while keeping agents outside trusted measurement.
5. Replaced “deterministic” with “evaluator-controlled” in the final recommendation because Autoengineering supports seeded stochastic search and noisy evaluations.
6. Converted implications into testable steps requiring fixed-seed, fixed-budget comparisons before improvement claims.

## Limitations

- This is a source-based landscape review, not hands-on reproduction or a controlled benchmark.
- Repository capabilities can change; the research date above bounds the review.
- “Resume not established” is a documentation finding, not proof that no checkpoint or continuation mechanism exists.
- Coverage is intentionally selective rather than an exhaustive catalog of AI-for-science agents.
- Recent preprints and project-reported results carry more uncertainty than replicated, peer-reviewed evidence; the brief preserves those distinctions where practical.
