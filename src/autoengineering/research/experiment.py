"""Experiment tree: every auto-research iteration as a node in a lineage.

Adapted from alphaXiv openresearch-cli's experiment-tree concept (see the repo
``NOTICE``). The baseline system is the root. Each candidate that gets swapped in
and measured becomes a child of the node it was derived from, carrying the
validation results and score observed for that variant.

The discipline that concept enforces is "grow down, not sideways": descend onto
winners rather than accumulating siblings off the root. :meth:`ExperimentTree.best`
returns the current highest-scoring node, and the loop grows the next child from
there — so the tree deepens along the improving path instead of fanning out.

Higher score = better here: the loop stores a goodness-of-fit fitness (mean of the
NSE/KGE/correlation skill metrics, or negative RMSE when no skill metric is scored;
see ``loop._fitness``). Nodes also store the raw metric dict for reporting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from autoengineering.validate.compare import ValidationResult


@dataclass
class ExperimentNode:
    """One point in the experiment lineage."""

    id: str
    parent_id: str | None = None
    component: str = ""  # the component that was swapped to create this node
    candidate: str = ""  # candidate name / short label for the change
    description: str = ""
    results: list[ValidationResult] = field(default_factory=list)
    score: float = 0.0  # fitness, higher is better
    status: str = "baseline"  # baseline | kept | reverted | failed
    metrics: dict = field(default_factory=dict)  # metric_name -> value
    sources: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "component": self.component,
            "candidate": self.candidate,
            "description": self.description,
            "results": [r.to_dict() for r in self.results],
            "score": round(self.score, 6),
            "status": self.status,
            "metrics": {k: _round(v) for k, v in self.metrics.items()},
            "sources": list(self.sources),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExperimentNode:
        return cls(
            id=data["id"],
            parent_id=data.get("parent_id"),
            component=data.get("component", ""),
            candidate=data.get("candidate", ""),
            description=data.get("description", ""),
            results=[ValidationResult(**r) for r in data.get("results", [])],
            score=data.get("score", 0.0),
            status=data.get("status", "baseline"),
            metrics=data.get("metrics", {}) or {},
            sources=list(data.get("sources", []) or []),
            notes=data.get("notes", ""),
        )


def _round(v):
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return v


class ExperimentTree:
    """A tree of experiment nodes rooted at the baseline."""

    def __init__(self, root: ExperimentNode):
        if root.parent_id is not None:
            raise ValueError("root node must have parent_id=None")
        self.nodes: dict[str, ExperimentNode] = {root.id: root}
        self.root_id: str = root.id
        self._counter: int = 0

    # --- construction ---

    def new_id(self, prefix: str = "exp") -> str:
        """Deterministic monotonic id (no wall-clock, safe for reproducible runs)."""
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def add_child(self, parent_id: str, node: ExperimentNode) -> ExperimentNode:
        if parent_id not in self.nodes:
            raise KeyError(f"parent node '{parent_id}' not in tree")
        node.parent_id = parent_id
        self.nodes[node.id] = node
        return node

    # --- queries ---

    def children_of(self, node_id: str) -> list[ExperimentNode]:
        return [n for n in self.nodes.values() if n.parent_id == node_id]

    def best(self, statuses: tuple[str, ...] = ("baseline", "kept")) -> ExperimentNode:
        """Highest-scoring node among the given statuses (defaults to the kept path)."""
        candidates = [n for n in self.nodes.values() if n.status in statuses]
        if not candidates:
            candidates = list(self.nodes.values())
        return max(candidates, key=lambda n: n.score)

    def path_to_best(self) -> list[ExperimentNode]:
        """The lineage from root down to the current best node."""
        node = self.best()
        chain = [node]
        while node.parent_id is not None:
            node = self.nodes[node.parent_id]
            chain.append(node)
        return list(reversed(chain))

    # --- serialization ---

    def to_jsonl(self, path: str | Path) -> None:
        """Write one JSON object per node (structured autoresearch.jsonl log)."""
        lines = [json.dumps(self.nodes[nid].to_dict()) for nid in self._ordered_ids()]
        Path(path).write_text("\n".join(lines) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> ExperimentTree:
        rows = [
            json.loads(line)
            for line in Path(path).read_text().splitlines()
            if line.strip()
        ]
        nodes = [ExperimentNode.from_dict(r) for r in rows]
        roots = [n for n in nodes if n.parent_id is None]
        if not roots:
            raise ValueError("jsonl has no root node (parent_id=None)")
        tree = cls(roots[0])
        for n in nodes:
            if n.id == tree.root_id:
                continue
            tree.nodes[n.id] = n
        tree._counter = len(nodes)
        return tree

    def _ordered_ids(self) -> list[str]:
        """Root first, then a stable DFS so parents precede children."""
        ordered: list[str] = []

        def visit(nid: str):
            ordered.append(nid)
            for child in sorted(self.children_of(nid), key=lambda n: n.id):
                visit(child.id)

        visit(self.root_id)
        # Include any orphans defensively.
        for nid in self.nodes:
            if nid not in ordered:
                ordered.append(nid)
        return ordered

    def to_markdown(self) -> str:
        """Indented tree view, in the spirit of ``orx experiments``."""
        icon = {
            "baseline": "●",
            "kept": "✓",
            "reverted": "✗",
            "failed": "!",
        }
        lines = ["# Experiment Tree", ""]

        def render(nid: str, depth: int):
            n = self.nodes[nid]
            indent = "  " * depth
            mark = icon.get(n.status, "•")
            label = n.candidate or n.component or n.id
            metric_str = ", ".join(
                f"{k}={_round(v)}" for k, v in n.metrics.items()
            )
            best_tag = " (best)" if nid == self.best().id else ""
            lines.append(
                f"{indent}{mark} {label}  [score={round(n.score, 3)}"
                f"{'; ' + metric_str if metric_str else ''}]"
                f" — {n.status}{best_tag}"
            )
            for child in sorted(self.children_of(nid), key=lambda c: c.id):
                render(child.id, depth + 1)

        render(self.root_id, 0)
        return "\n".join(lines)
