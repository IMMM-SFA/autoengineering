"""System graph: NetworkX-backed directed graph of model components."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import yaml

from autoengineering.system.component import Component


class System:
    """A system of interconnected model components, backed by a NetworkX DAG."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._graph = nx.DiGraph()

    # --- Component management ---

    def add_component(
        self,
        name: str,
        model_type: str = "",
        description: str = "",
        inputs: dict[str, str] | None = None,
        outputs: dict[str, str] | None = None,
        metadata: dict | None = None,
    ) -> Component:
        """Add a component to the system.

        Args:
            name: Unique component name.
            model_type: Type of model (e.g., "generator", "routing").
            description: Human-readable description.
            inputs: Dict of {port_name: data_type}.
            outputs: Dict of {port_name: data_type}.
            metadata: Arbitrary metadata dict.
        """
        comp = Component(
            name=name,
            model_type=model_type,
            description=description,
            metadata=metadata or {},
        )
        for port_name, data_type in (inputs or {}).items():
            comp.add_input(port_name, data_type=data_type)
        for port_name, data_type in (outputs or {}).items():
            comp.add_output(port_name, data_type=data_type)

        self._graph.add_node(name, component=comp)
        return comp

    def get_component(self, name: str) -> Component:
        """Get a component by name."""
        if name not in self._graph:
            raise KeyError(f"Component '{name}' not found in system '{self.name}'")
        return self._graph.nodes[name]["component"]

    @property
    def components(self) -> list[Component]:
        """All components in the system."""
        return [self._graph.nodes[n]["component"] for n in self._graph.nodes]

    @property
    def component_names(self) -> list[str]:
        """Names of all components."""
        return list(self._graph.nodes)

    # --- Connections ---

    def connect(
        self,
        source: str,
        target: str,
        port_from: str = "",
        port_to: str = "",
        description: str = "",
    ):
        """Connect two components (source -> target)."""
        if source not in self._graph:
            raise KeyError(f"Source component '{source}' not found")
        if target not in self._graph:
            raise KeyError(f"Target component '{target}' not found")
        self._graph.add_edge(
            source,
            target,
            port_from=port_from,
            port_to=port_to,
            description=description,
        )

    @property
    def connections(self) -> list[dict]:
        """All connections as a list of dicts."""
        result = []
        for u, v, data in self._graph.edges(data=True):
            result.append({"source": u, "target": v, **data})
        return result

    # --- Graph queries ---

    def upstream_of(self, component: str) -> list[str]:
        """Components that feed into the given component (all ancestors)."""
        return list(nx.ancestors(self._graph, component))

    def downstream_of(self, component: str) -> list[str]:
        """Components that depend on the given component (all descendants)."""
        return list(nx.descendants(self._graph, component))

    def direct_upstream(self, component: str) -> list[str]:
        """Immediate predecessors."""
        return list(self._graph.predecessors(component))

    def direct_downstream(self, component: str) -> list[str]:
        """Immediate successors."""
        return list(self._graph.successors(component))

    def topological_order(self) -> list[str]:
        """Components in execution order."""
        return list(nx.topological_sort(self._graph))

    def to_networkx(self) -> nx.DiGraph:
        """Return the underlying NetworkX graph."""
        return self._graph.copy()

    # --- Serialization ---

    def to_yaml(self, path: str | Path):
        """Save system definition to YAML."""
        data = {
            "system": {
                "name": self.name,
                "description": self.description,
                "components": [
                    self._graph.nodes[n]["component"].to_dict()
                    for n in self._graph.nodes
                ],
                "connections": [
                    {
                        "source": u,
                        "target": v,
                        "port_from": d.get("port_from", ""),
                        "port_to": d.get("port_to", ""),
                        "description": d.get("description", ""),
                    }
                    for u, v, d in self._graph.edges(data=True)
                ],
            }
        }
        Path(path).write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    @classmethod
    def from_yaml(cls, path: str | Path) -> System:
        """Load system definition from YAML."""
        data = yaml.safe_load(Path(path).read_text())
        sys_data = data["system"]
        system = cls(name=sys_data["name"], description=sys_data.get("description", ""))

        for comp_data in sys_data.get("components", []):
            comp = Component.from_dict(comp_data)
            system._graph.add_node(comp.name, component=comp)

        for conn in sys_data.get("connections", []):
            system._graph.add_edge(
                conn["source"],
                conn["target"],
                port_from=conn.get("port_from", ""),
                port_to=conn.get("port_to", ""),
                description=conn.get("description", ""),
            )

        return system

    # --- Display ---

    def to_mermaid(self) -> str:
        """Generate a Mermaid flowchart diagram of the system."""
        lines = ["```mermaid", "graph LR"]
        for name in self._graph.nodes:
            comp = self._graph.nodes[name]["component"]
            label = f"{name}"
            if comp.model_type:
                label += f"\\n({comp.model_type})"
            lines.append(f'    {name}["{label}"]')
        for u, v, data in self._graph.edges(data=True):
            edge_label = data.get("port_from", "")
            if edge_label:
                lines.append(f"    {u} -->|{edge_label}| {v}")
            else:
                lines.append(f"    {u} --> {v}")
        lines.append("```")
        return "\n".join(lines)

    def describe(self) -> str:
        """Generate a markdown description of the system."""
        lines = [f"# System: {self.name}"]
        if self.description:
            lines.append(f"\n{self.description}\n")
        lines.append(f"**Components**: {len(self._graph.nodes)}")
        lines.append(f"**Connections**: {len(self._graph.edges)}")

        try:
            order = self.topological_order()
            lines.append(f"**Execution order**: {' → '.join(order)}")
        except nx.NetworkXUnfeasible:
            lines.append("**Warning**: System contains cycles")

        lines.append("")
        for name in self._graph.nodes:
            comp = self._graph.nodes[name]["component"]
            lines.append(comp.to_markdown())
            lines.append("")

        lines.append("## Connections")
        for u, v, data in self._graph.edges(data=True):
            port_info = ""
            if data.get("port_from") or data.get("port_to"):
                port_info = f" (`{data.get('port_from', '?')}` → `{data.get('port_to', '?')}`)"
            lines.append(f"- **{u}** → **{v}**{port_info}")

        lines.append("")
        lines.append("## Diagram")
        lines.append(self.to_mermaid())

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"System('{self.name}', "
            f"components={len(self._graph.nodes)}, "
            f"connections={len(self._graph.edges)})"
        )
