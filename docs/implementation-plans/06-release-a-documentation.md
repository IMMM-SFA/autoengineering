# Item 6 implementation plan: Release A documentation and review

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `045c158`_

## Outcome

Document the supported whole-system optimization workflow from installation through recovery and
benchmark interpretation. Remove stale setup commands and hard-coded test counts, expose the
optimization command and example from the repository entry points, and complete the Release A
review and platform checks without starting function-network work.

## Current documentation gaps

The README and `CLAUDE.md` still name a removed `install` Pixi task. The README command table omits
`optimize`, its API section omits the optimization contracts, and its development section contains
a stale test count. There is no optimization guide or example index. The auto-engineer instructions
describe only the component replacement workflow and do not distinguish whole-system optimization
from the planned function-network research layer. `CLAUDE.md` also says the environment supports
only macOS ARM even though `pixi.toml` declares macOS ARM and Linux.

## Documentation structure

Add `docs/optimization.md` as the authoritative guide. It will cover:

1. base and Bayesian installation with Pixi and package extras;
2. the whole-system estimand and sequential execution contract;
3. the complete run YAML schema, path resolution, and declared input provenance;
4. random, scrambled Sobol, and BoTorch policy selection and options;
5. deterministic, known, and learned observation-noise modes;
6. scientific constraints, failures, evaluator costs, and budget stop reasons;
7. bounded starts, required resume intent, text and JSON CLI output;
8. Python construction with `OptimizationRunSpec`, `ObservationLedger`, policy creation, and
   `OptimizationStudy`;
9. durable artifacts, manifest-last commits, run identity, pending recovery, and incompatible
   resume behavior;
10. categorical enumeration limits, acquisition retries, diagnostics, and Sobol fallbacks;
11. the self-contained optimization example;
12. Release A benchmark design, raw evidence, gate interpretation, and invalidated-trial history;
    and
13. the boundary between supported whole-system optimization and the unimplemented
    function-network research layer.

Keep the guide linked to the public example and checked benchmark artifacts rather than copying
large schemas or aggregate tables. Claims about defaults and artifact names must match code and
tests at the final revision.

## Entry-point updates

- Rewrite the README installation and quick-start commands to use existing Pixi tasks and the
  editable package already declared by the environment.
- Add optimization imports to the Python API reference and `optimize` to the CLI reference.
- Link the optimization guide, example index, benchmark report, decisions, and current status.
- Add `examples/README.md` with dependency, network, purpose, and entry-command notes for every
  example. Mark `optimization_chain` as the Release A no-network optimization example. Record that
  the checked Leaf River cache avoids network access and its fetcher is used only if that cache is
  absent.
- Update `CLAUDE.md` and `.claude/agents/auto-engineer.md` with current commands, supported
  platforms, the optimization workflow, recovery safeguards, and the whole-system versus
  function-network boundary.
- Remove hard-coded test counts from general documentation. Historical completion and review
  records may retain exact observed counts as evidence.

## Documentation contracts

Add a focused test that reads the checked documentation and requires:

- every local Markdown link to resolve;
- every README and agent CLI command name to exist in Click's registered command set;
- every named Pixi task to exist in `pixi.toml`;
- the optimization guide to cover required policies, noise modes, recovery states, artifacts,
  benchmark evidence, limitations, and research boundary; and
- the example index to list all checked example directories with accurate network labels.

Use structural assertions rather than prose snapshots so normal editing remains possible while
stale commands and missing coverage fail clearly.

## Verification workflow

Run the focused documentation test, lint, default tests, Bayesian tests, and checked benchmark
verification in the implementation worktree. Run scoped Waterology and whitespace checks on every
touched document and test.

Create a Git archive from the same signed candidate revision and extract it into new temporary
directories on macOS ARM and the Linux `bean-box` host. In each fresh checkout:

1. install the declared Pixi environments;
2. run lint and the default suite;
3. run the Bayesian suite;
4. verify the checked Release A benchmark from raw evidence; and
5. record platform, Python, and package results in the item 6 review.

The fresh checks must use only committed files. They must not push, publish, or alter the source
checkout. Remove only the exact temporary archives and directories created for this verification.

## Completion gate

Item 6 is complete only when the guide and every entry-point update agree with the current public
API and CLI, the documentation contract test passes, an independent review finds no remaining
Release A defect, all four repository commands from the parent plan pass at one signed revision,
and fresh macOS ARM and Linux checkouts pass the declared verification workflow.

If a platform or dependency check fails, preserve the exact failure and keep item 6 in progress.
Do not weaken Release A behavior or benchmark criteria to make a documentation or portability check
pass.
