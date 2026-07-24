"""Candidate replacement models: the deep-research -> auto-research bridge.

``rank_opportunities`` tells you *which* component is weakest. Deep research
(the ``deep-research-candidates`` skill) answers *what to replace it with*, and
records its answer as a list of :class:`Candidate` specs written to a YAML file.
:func:`autoengineering.research.loop.auto_improve` then reads that file, turns
each candidate into a :class:`~autoengineering.system.component.Component` via
:meth:`Candidate.to_component`, and swaps it in to measure the gain.

A candidate is a component plus provenance: a ``rationale`` for why it should be
better and the ``sources`` (citations/URLs) the research rests on. Carrying the
sources through to the final report is what makes the improvement auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from autoengineering.system.component import Component


@dataclass
class Candidate:
    """A proposed replacement for a component, with research provenance.

    The ``name`` should usually match the component being replaced so that
    ``swap_component`` preserves the graph wiring; a different name is allowed and
    triggers a rename (see ``swap_component``).
    """

    name: str
    model_type: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    rationale: str = ""
    sources: list[str] = field(default_factory=list)

    def to_component(self) -> Component:
        """Convert to a Component suitable for ``swap_component``.

        The runnable spec and any other research metadata are preserved under
        ``metadata``; rationale and sources are stashed there too so they survive
        the swap and can be surfaced in the report.
        """
        meta = dict(self.metadata)
        if self.rationale:
            meta.setdefault("rationale", self.rationale)
        if self.sources:
            meta.setdefault("sources", list(self.sources))
        return Component(
            name=self.name,
            model_type=self.model_type,
            description=self.description,
            metadata=meta,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "model_type": self.model_type,
            "description": self.description,
            "metadata": self.metadata,
            "rationale": self.rationale,
            "sources": list(self.sources),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Candidate:
        return cls(
            name=data["name"],
            model_type=data.get("model_type", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}) or {},
            rationale=data.get("rationale", ""),
            sources=list(data.get("sources", []) or []),
        )


def load_candidates(path: str | Path) -> list[Candidate]:
    """Load a candidates YAML file written by the deep-research step.

    Expected shape::

        target: pet_estimator        # optional: the component these replace
        candidates:
          - name: pet_estimator
            model_type: evapotranspiration
            description: ...
            rationale: ...
            sources: [https://doi.org/...]
            metadata:
              runnable: {kind: python, entry: "...", inputs: [...], outputs: [...]}
    """
    data = yaml.safe_load(Path(path).read_text()) or {}
    raw = data.get("candidates", data if isinstance(data, list) else [])
    return [Candidate.from_dict(c) for c in raw]


def save_candidates(
    path: str | Path, candidates: list[Candidate], target: str = ""
) -> None:
    """Write candidates to a YAML file (round-trips with :func:`load_candidates`)."""
    data: dict = {}
    if target:
        data["target"] = target
    data["candidates"] = [c.to_dict() for c in candidates]
    Path(path).write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def candidate_template(component: Component) -> str:
    """Return a YAML scaffold for researching replacements for ``component``.

    Used by the ``autoengineering candidates`` CLI command to give the research
    step (human or agent) a correctly-shaped file to fill in.
    """
    example = Candidate(
        name=component.name,
        model_type=component.model_type,
        description="<what this alternative model does>",
        rationale="<why it should outperform the current implementation>",
        sources=["<citation or URL from deep research>"],
        metadata={
            "runnable": {
                "kind": "python",
                "entry": "models.<module>:<callable>",
                "inputs": [p.name for p in component.inputs],
                "outputs": [p.name for p in component.outputs],
            }
        },
    )
    return save_candidates_to_string(target=component.name, candidates=[example])


def save_candidates_to_string(target: str, candidates: list[Candidate]) -> str:
    data: dict = {}
    if target:
        data["target"] = target
    data["candidates"] = [c.to_dict() for c in candidates]
    return yaml.dump(data, default_flow_style=False, sort_keys=False)
