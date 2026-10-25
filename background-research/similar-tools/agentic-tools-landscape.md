# Agentic Tools Comparable to Autoengineering

*Research date: 2026-10-25. Scope: open tools and documented research systems that construct, execute, validate, or optimize scientific models. This is a landscape review, not a hands-on benchmark.*

## Executive summary

Autoengineering does not have a close drop-in equivalent among the tools reviewed. Its distinctive combination is a user-declared graph of scientific components, validation, explicit component replacement, constrained whole-system parameter/architecture search, and durable optimization evidence. It is also important to state that **Autoengineering itself is not currently an LLM agent**: it executes supplied implementations and algorithmic search policies rather than autonomously researching or implementing candidates.

The closest agentic systems fall into three groups:

1. **Joint model-structure and parameter discovery:** **Model Discovery Agent (MDA)**, **G-Sim**, **Scientific Generative Agent (SGA)**, and **SOCIA-EVO**. These are the strongest conceptual matches. They use observations or execution feedback to revise model structure while separately inferring or fitting parameters. Unlike Autoengineering, their search object is generally generated simulator code, modular mechanisms, or a scientific hypothesis, not a stable graph of user-supplied component implementations.
2. **Agent-directed physical model construction:** the **Modelica commissioning-agent study**, **AutoMOOSE**, and **Foam-Agent**. These provide concrete engineering execution and repair loops. The Modelica study is especially relevant because agents may add, remove, replace, and reconnect library components, then calibrate and accept the resulting models. AutoMOOSE and Foam-Agent automate domain-specific simulation workflows but do not provide general architecture optimization.
3. **Evaluator-guided code improvement:** **TusoAI**, **AIDE**, **FunSearch**, and **AlphaEvolve**. These iteratively generate and evaluate code changes. They are useful models for an agentic proposal layer above Autoengineering, but optimize scientific methods, ML programs, or algorithms rather than declared component graphs.

For non-agentic functional comparison, **OpenMDAO**, **DAKOTA**, **PyMT/BMI**, and **Ax** matter at least as much as the AI-scientist tools. They are mature references for model composition, simulation optimization, model interoperability, and sequential experiment management respectively. Combining these categories is a better description of Autoengineering's position than calling it another autonomous scientist.

## Recommended shortlist

| Priority | Tool | Why it matters | Main difference from Autoengineering |
| --- | --- | --- | --- |
| 1 | [Model Discovery Agent](https://arxiv.org/html/2608.09696) | Modular mechanism discovery, Bayesian structure/parameter/state inference, and value-of-information experiment design | Discovers mechanistic world models from experimental data rather than optimizing a fixed component graph |
| 2 | [G-Sim](https://github.com/samholt/generative-simulations) | Iterative structural simulator design plus gradient-free calibration or simulation-based inference | LLM-generated simulator structure; no fixed user-supplied component-DAG replacement protocol |
| 3 | [SGA](https://github.com/PingchuanMa/SGA) | Explicit bilevel search: LLM for discrete hypotheses, differentiable simulation for continuous parameters | Focused on constitutive laws and molecular design; requires differentiable inner simulation |
| 4 | [SOCIA-EVO](https://aclanthology.org/2026.acl-long.1274/) | Structural refinement, black-box parameter calibration, and a persistent repair-strategy record | Social-simulator code generation, not general engineering component graphs |
| 5 | [Modelica commissioning agents](https://github.com/jfrochte/agents-as-modelica-suppliers) | Direct component-level model editing, calibration, unseen-experiment tests, and physical-invariant checks | A commissioning and acceptance harness using stock coding agents, not a general optimization platform |
| 6 | [TusoAI](https://github.com/Alistair-Turcan/TusoAI) | Literature-informed scientific-code evolution with measured evaluations, history, budgets, and resume | Evolves functions/codebases, especially computational-biology methods; no native system graph |
| 7 | [AutoRA](https://autoresearch.github.io/autora/) | Closed-loop model discovery, experimental design, and data collection | Primarily empirical model discovery and experiment selection; no inherent LLM or component-DAG optimizer |
| 8 | [OpenMDAO](https://openmdao.org/) | Strong non-agentic baseline for connected models and multidisciplinary optimization | Python-built models and mature numerical optimization, not autonomous candidate generation |

## Comparison by capability

These are **documented capabilities, not independently reproduced results**. “Structure search” is broad: it can mean generated equations or code, not necessarily Autoengineering's exact `swap_component` semantics. Publication status and evaluation domain are separated from capability. “Resume not established” means the reviewed sources did not document restored search state, compatibility checks, and exactly-once recovery; it does not imply that continuation is impossible.

| Tool | Structure and parameter search | Evidence status and evaluated domains | Artifacts retained | Search continuation / compatible recovery |
| --- | --- | --- | --- | --- |
| MDA | LLM modular mechanisms; Bayesian parameters/latent states; experiment design | 2026 preprint; chemical rates, glucose ODEs, neuron SDEs, other benchmarks | Model posterior and experiment records described in paper | Resume not established |
| G-Sim | LLM structure; gradient-free or SBI parameters | ICML 2025; data-grounded simulators | Run history/logs | Resume not established |
| SGA | LLM discrete hypotheses; differentiable calibration | ICML 2024; constitutive laws, molecular design | Candidate artifacts/history | `resume` preserves output directory; restored population/search state not established |
| SOCIA-EVO | Structural code refinement; black-box calibration | ACL 2026; ratings, mask adoption, mobility | Blueprint, logs, strategy records | Resume not established |
| Modelica agents | Component edits; agent-written calibration | 2026 preprint; four simulated systems and one measured magnet | Run ledger and acceptance reports | Campaign resume not established |
| TusoAI | Literature-informed code/method evolution | Project documentation and paper; computational-biology methods | History, prompts, evaluations | `load_history` continuation; compatible exactly-once recovery not established |
| AIDE | ML-code tree search; training inside generated code | Paper plus ML/research-engineering benchmarks | Solution tree, scripts, scores, logs | Recovery contract not established |
| AutoRA | Formal model discovery and fitting; experiment selection | JOSS 2024; empirical-science workflows | Workflow state/documentation | Depends on composed workflow |
| AutoMOOSE | Solver-input generation; sweeps, not general graph search | 2026 preprint and repository; phase-field benchmarks | Detailed per-run records | Campaign recovery not established |
| Foam-Agent | CFD case generation/repair; no general optimizer found | CMAME 2026 and repository; FoamBench | Case copies, logs, reports | Explicitly no task-resume step |
| OpenMDAO | No automatic structure search; user-defined structure; numerical optimization | Actively maintained engineering platform | Native case recording | Different model from Autoengineering's study recovery |

## Closest agentic tools

### Model Discovery Agent (MDA)

The [Model Discovery Agent](https://arxiv.org/html/2608.09696) (2026 preprint) combines LLM proposals for modular scientific mechanisms, approximate Bayesian inference over structures, parameters, and stochastic latent trajectories, and value-of-information experiment design. It therefore connects the structural-search ideas in G-Sim with AutoRA's concern for choosing informative observations. Reported evaluations cover symbolic chemical reaction rates, partially observed glucose ODEs, stochastic single-neuron SDEs, and additional benchmark domains.

MDA is highly relevant conceptually, but it discovers mechanistic world models from limited experimental data rather than searching a fixed graph of supplied engineering components. Its Bayesian structure posterior and explicit experiment-value calculation go beyond Autoengineering's current heuristic prioritization. The evidence is a recent preprint across the stated benchmarks, not a demonstration of general coupled-engineering optimization.

**Best use as a reference:** joint structure/parameter uncertainty and experiment selection based on expected information value.

### G-Sim

[G-Sim](https://proceedings.mlr.press/v267/holt25b.html) (ICML 2025) is arguably the closest conceptual match. An LLM iteratively proposes and refines core simulator components and causal relationships. Numerical calibration then estimates parameters using gradient-free optimization or simulation-based inference, including for stochastic and non-differentiable simulators. This separation resembles Autoengineering's distinction between architecture choices and continuous parameters.

The key difference is where structure lives. G-Sim generates simulator structure and code; Autoengineering evaluates a declared graph and supplied alternatives. G-Sim's [public reproduction code](https://github.com/samholt/generative-simulations) supports its published experiments, but the reviewed material does not document a durable compatible-resume contract comparable to Autoengineering's optimization ledger. Its published limitations include scaling to high-dimensional systems, obtaining sufficiently diverse structures, and the fact that parameter posteriors do not represent uncertainty over model structure ([paper](https://arxiv.org/html/2506.09272v1)).

**Best use as a reference:** designing an LLM structural-proposal layer that remains grounded by an independent numerical evaluator.

### Scientific Generative Agent (SGA)

[SGA](https://proceedings.mlr.press/v235/ma24m.html) (ICML 2024) explicitly formulates discovery as bilevel optimization. The LLM proposes discrete scientific hypotheses such as equations or molecular structures; simulation supplies feedback and differentiable optimization fits continuous physical parameters. A top-K candidate history supports iterative exploration.

This is a close architectural analogue, but not a general connected-system optimizer. The published domains are constitutive-law discovery and molecular design, and the inner loop relies on differentiability where Autoengineering supports black-box random, Sobol, and BoTorch search. The [research code](https://github.com/PingchuanMa/SGA) targets a CUDA-oriented environment and calls hosted LLM APIs. No declared repository license was found, which is a practical adoption constraint.

**Best use as a reference:** bilevel search and retaining a diverse elite set of structural candidates.

### SOCIA-EVO

[SOCIA-EVO](https://aclanthology.org/2026.acl-long.1274/) (ACL 2026) addresses two agent failure modes: contextual drift and instability caused by conflating structural and parametric errors. It combines a static empirical “Blueprint,” outer structural code refinement, inner numerical parameter calibration, and a Strategy Playbook that records and evaluates repair hypotheses. Calibration can use random search, Bayesian optimization, or other black-box methods.

Its separation of structural and parameter repair, explicit evidence records, and falsification of ineffective strategies are highly relevant. Its [implementation](https://github.com/cruiseresearchgroup/SOCIA-EVO) uses specialized agents and supports Docker-isolated execution; lite mode uses subprocesses, and full mode can fall back to LLM-simulated execution ([execution code](https://github.com/cruiseresearchgroup/SOCIA-EVO/blob/main/agents/simulation_execution/agent.py)). That fallback is not equivalent to running a simulator and should be visible in evidence records. The published experiments used one-time expert verification of the initial Blueprint, followed by automatic optimization iterations ([paper, sections 3.2.1 and 4.2](https://aclanthology.org/2026.acl-long.1274.pdf)). Evidence concerns social simulations such as user ratings, mask adoption, and mobility rather than coupled engineering PDE systems.

**Best use as a reference:** persistent, evaluator-tested repair strategies and explicit separation of structure from calibration.

### LLM agents as Modelica suppliers

The [Modelica commissioning-agent study](https://arxiv.org/html/2610.25019v1) is the clearest reviewed example of agents performing component-level physical-system modeling. Stock coding agents receive shell/file tools and OpenModelica, construct models from library components, write calibration routines, and choose between numerical and structural repairs. Structural repair can add, remove, replace, or reconnect components.

Its strongest lesson is acceptance rather than agent architecture. The [public harness](https://github.com/jfrochte/agents-as-modelica-suppliers) supplies five tasks and separately checks conformance, parameters, behavior, energy invariants, unseen experiments, variants, and reports. One demonstrated model fit its data yet created energy. That directly supports Autoengineering's caution that compatible ports and good scalar fitness do not prove scientific compatibility.

This is a task and acceptance framework around interchangeable coding agents, not a branded autonomous modeling product or a sequential architecture-search controller. The preprint and five-task evidence base are early, but its acceptance design is unusually relevant.

**Best use as a reference:** held-out experiments, physical invariants, variant tests, and layered acceptance in addition to fit metrics.

## Code-improvement and research-loop tools

### TusoAI

[TusoAI](https://github.com/Alistair-Turcan/TusoAI) evolves scientific methods from an existing function or code template and an evaluation script. It mines literature, constructs candidate changes, evaluates temporary copies, and retains search history. Its documented controls include time and estimated LLM-cost budgets, per-evaluation timeouts, parallel workers, resource limits, and resume through `load_history`.

This makes it one of the closest practical examples of an agentic proposal layer around a measured evaluator. The important difference is that TusoAI is expected to create algorithmic and data innovations in code; Autoengineering intentionally requires implementations to be supplied and searches a bounded declared space. TusoAI's framing and examples emphasize computational biology, so its results should not be generalized to arbitrary coupled physical models without evaluation.

**Potential relationship:** complementary. TusoAI could propose candidate implementations; Autoengineering could provide graph-aware execution, constraints, failure states, and durable whole-system evidence.

### AIDE

[AIDE ML](https://github.com/WecoAI/aideml) performs LLM-guided tree search over executable Python ML solutions. It drafts, executes, debugs, and patches code using a user-defined validation metric, and saves candidate scripts, scores, logs, and a tree visualization. Hosted and local OpenAI-compatible models are supported.

AIDE is relevant to measured candidate refinement, not to scientific graph composition. Its benchmarks concern ML and research-engineering tasks. The authors also report substantial task variation, possible benchmark contamination, and greedy-search local optima ([paper](https://arxiv.org/html/2502.13138v1)). It should therefore not be cited as evidence of general scientific-discovery capability.

**Potential relationship:** AIDE-like code search could generate candidates, while Autoengineering supplies scientific-system evaluation and recovery.

### FunSearch and AlphaEvolve

[FunSearch](https://deepmind.google/discover/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/) pairs LLM-generated functions with an automated evaluator and an evolutionary program pool; [AlphaEvolve](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) extends this pattern to larger codebases and broader algorithm discovery. They are foundational references for keeping proposal generation separate from executable scoring. Their published successes are in mathematics, algorithms, and computing infrastructure, and AlphaEvolve was announced with limited early access rather than as a general open-source scientific-system optimizer. Neither supplies Autoengineering's component-graph abstraction.

**Potential relationship:** their evaluator-gated evolutionary pattern is directly relevant to candidate proposal and retention, but not evidence of performance on coupled scientific models.

### AutoRA

[AutoRA](https://autoresearch.github.io/autora/) automates model discovery, experimental design, data collection, and research documentation. Its theorists construct formal models, experimentalists choose follow-up experiments, and runners collect data; users compose these modules into closed-loop workflows. The framework does not inherently require an LLM. Its [JOSS paper](https://joss.theoj.org/papers/10.21105/joss.06839) and active documentation make it a more established research framework than many recent agent demonstrations.

AutoRA is most relevant when the next action is a real-world experiment rather than another simulation. It does not natively provide Autoengineering's explicit multi-component DAG replacement and whole-system BO, and domain-specific runners remain necessary.

**Potential relationship:** AutoRA-style experimental design could complement Autoengineering when model improvement requires new observations.

## Domain-specific engineering agents

[AutoMOOSE](https://github.com/sukritimanna/AutoMOOSE) turns natural-language specifications into MOOSE phase-field inputs, executes locally or on HPC, checks physics invariants, performs bounded numerical recovery, and stores detailed run records. Its MCP interface could let an external optimizer drive it. Only grain-growth and spinodal plugins are marked ready; solidification and ferroelectric plugins are stubs. Bayesian optimization is future work, so it is not currently a direct whole-system optimizer.

[Foam-Agent](https://github.com/csml-rpi/Foam-Agent) automates OpenFOAM case creation or modification, meshing, local/Slurm execution, reviewer-driven repair, and visualization. Its reported FoamBench results vary sharply by model and should not be generalized to arbitrary CFD cases. The repository explicitly says there is no task-resume step, and local restart data are not preserved. It is a useful execution adapter and repair-loop reference, not a graph optimizer.

[JutulGPT](https://github.com/SINTEF-agentlab/JutulGPT) similarly combines documentation retrieval, Julia/Jutul code generation, execution, solver diagnostics, and bounded repair for reservoir simulation. It is relevant as a domain execution agent, but no general parameter/architecture campaign controller was found.

## Important non-agentic functional peers

- **[OpenMDAO](https://github.com/OpenMDAO/OpenMDAO):** the strongest composition-and-optimization baseline. It provides hierarchical connected components, coupled solvers, analytic derivatives, optimization and design-of-experiment [drivers](https://openmdao.org/newdocs/versions/latest/features/building_blocks/drivers/index.html), and case recording. Those documented features directly address large multidisciplinary and tightly coupled systems; Autoengineering instead emphasizes declarative candidate replacement, validation reports, and compatible study recovery.
- **[DAKOTA](https://snl-dakota.github.io/docs/6.20.0/users/usingdakota/introduction/aboutdakota.html):** a mature simulation-analysis toolkit for gradient and non-gradient optimization, uncertainty quantification, calibration, sensitivity analysis, surrogates, and HPC. It is a functional peer for optimization/UQ, not an agent or component-replacement experiment system.
- **[PyMT/BMI](https://pymt.readthedocs.io/en/stable/readme.html):** the relevant model-interoperability baseline. BMI standardizes model control, units, grids, variable access, and time stepping; PyMT adds coupling and data exchange. This addresses scientific interface semantics that matching Autoengineering port names alone do not.
- **[Ax](https://ax.dev/) and [BoTorch](https://botorch.org/docs/botorch_and_ax):** Ax is the closer sequential-experiment management comparison; BoTorch is the lower-level BO library Autoengineering already uses. Ax provides problem specification, metadata, storage, and experiment management rather than scientific component graphs.
- **[Optuna](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/001_rdb.html) and [Ray Tune](https://docs.ray.io/en/latest/tune/tutorials/tune-fault-tolerance.html):** useful references for persisted trials, distributed execution, pruning, and restore. They orchestrate objective functions or trainables, not scientific model composition.

## Tools often mentioned but less comparable

**The AI Scientist-v2, Agent Laboratory, and Denario** automate portions of ideation, coding, analysis, and paper writing. Their trees and graphs primarily represent code-search history or agent workflow, not connected scientific components. They are relevant to a future research/reporting layer, but less useful as direct functional comparisons. Published evaluations are narrow and include documented failures, so manuscript generation is not evidence of valid model optimization ([AI Scientist-v2](https://arxiv.org/html/2504.08066), [Agent Laboratory](https://arxiv.org/html/2501.04227), [Denario](https://arxiv.org/html/2510.26887)).

**SciAgents** uses an ontological knowledge graph to generate and critique materials-research hypotheses. That graph is not an executable model-component graph, and the public artifact does not run whole-system simulator optimization ([paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12138853/), [code](https://github.com/lamm-mit/SciAgentsDiscovery)).

**ChemCrow and Coscientist** are important domain-specific laboratory/tool agents, but their chemistry planning and physical-experiment demonstrations are not general model-composition or architecture-search systems ([ChemCrow](https://pmc.ncbi.nlm.nih.gov/articles/PMC11116106/), [Coscientist](https://www.nature.com/articles/s41586-023-06792-0)).

## Implications for Autoengineering

### Most defensible positioning

> Autoengineering is a local scientific-system composition, validation, and optimization substrate. Agentic tools can propose hypotheses or implementations above it; mature simulation and optimization platforms supply alternative execution and search capabilities below or beside it.

This is more precise than marketing Autoengineering as an autonomous scientist. Its current strengths are bounded action spaces, explicit failure states, reproducible evidence, and recovery—not open-ended ideation or code generation.

### Features worth borrowing, as testable steps

1. **Add a separate, untrusted proposal interface:** G-Sim, SGA, SOCIA-EVO, FunSearch, and AlphaEvolve support a clean division between an LLM proposer and an evaluator-owned numerical search. Start with serialized candidate manifests and no direct evaluator privileges; compare against existing random/Sobol/BoTorch workflows at fixed seeds and budgets before claiming improvement.
2. **Add optional layered scientific acceptance:** the Modelica study shows why held-out inputs, physical invariants, variants, and report consistency should supplement scalar fitness. Prototype these as explicit validation checks whose failures remain visible rather than silently changing objective values.
3. **Record intervention rationale and outcomes:** SOCIA-EVO's playbook and TusoAI's resumable history suggest backward-compatible records of why structural interventions were proposed and whether classes of intervention worked. Preserve existing ledgers and recovery compatibility rather than replacing their evidence model.
4. **Integrate solver interfaces, not nested agents:** AutoMOOSE, Foam-Agent, and JutulGPT demonstrate useful routes to MOOSE, OpenFOAM, and Jutul. Evaluate the underlying solver interfaces as candidate execution backends while keeping agent orchestration outside trusted measurement and retaining Autoengineering's failure classification and provenance.
5. **Consider experiment selection after simulation-only improvements:** MDA and AutoRA offer value-of-information and closed-loop empirical-design references for choosing informative new observations.

### Adoption cautions

- Do not infer scientific validity from executable code or benchmark success. Agent-generated models can fit data while violating physics.
- Do not equate an agent orchestration graph, knowledge graph, or code-search tree with a physical component DAG.
- Do not compare benchmark scores across these tools directly: tasks, models, budgets, metrics, and acceptance tests differ.
- Generated-code systems need isolation and resource limits. Autoengineering's trusted-configuration boundary should remain explicit if agent-generated implementations are admitted.
- Several closest systems are recent research prototypes with small domain-specific evaluations. “No resume found” here means the reviewed documentation did not establish one, not that it is impossible.

## Bottom line

Start with **MDA, G-Sim, SGA, SOCIA-EVO, the Modelica commissioning-agent harness, and TusoAI** for agentic design ideas. Use **OpenMDAO, DAKOTA, PyMT/BMI, and Ax** as functional and maturity baselines. Treat general AI-scientist and paper-writing systems as adjacent research orchestration, not direct competitors.

The clearest opportunity is complementary: let an external agent propose bounded candidate components or structural hypotheses, while Autoengineering remains the evaluator-controlled, auditable authority for execution, validation, optimization, retention, and recovery.
