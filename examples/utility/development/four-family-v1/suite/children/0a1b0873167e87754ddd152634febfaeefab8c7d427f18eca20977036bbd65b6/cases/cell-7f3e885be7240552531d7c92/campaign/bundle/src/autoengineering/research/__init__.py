"""Research: deep-research candidate discovery + bounded auto-research loop.

This subpackage bridges the ``analyze`` step (which component is weakest) to the
``execute`` step (swap in something better) with two capabilities inspired by
feynman.is and alphaXiv's openresearch-cli (see the repo ``NOTICE``):

- **Deep research -> candidates.** An LLM-driven skill investigates replacement
  models for the weakest component and writes swap-ready :class:`Candidate` specs.
- **Auto research loop.** :func:`auto_improve` swaps each candidate in, executes the
  chain, validates it, and records the lineage in an :class:`ExperimentTree`, then
  writes an evidence-first report and provenance sidecar.

The loop itself is deterministic and contains no LLM calls; the model-agnostic
research half lives in the skills under ``.claude/skills/``.
"""

from autoengineering.research.candidates import (
    Candidate,
    candidate_template,
    load_candidates,
    save_candidates,
)
from autoengineering.research.experiment import ExperimentNode, ExperimentTree
from autoengineering.research.loop import auto_improve
from autoengineering.research.provenance import write_report
from autoengineering.research.runner import (
    Runner,
    build_feedforward_runner,
    run_component,
)

__all__ = [
    "Candidate",
    "load_candidates",
    "save_candidates",
    "candidate_template",
    "ExperimentNode",
    "ExperimentTree",
    "auto_improve",
    "write_report",
    "Runner",
    "run_component",
    "build_feedforward_runner",
]
