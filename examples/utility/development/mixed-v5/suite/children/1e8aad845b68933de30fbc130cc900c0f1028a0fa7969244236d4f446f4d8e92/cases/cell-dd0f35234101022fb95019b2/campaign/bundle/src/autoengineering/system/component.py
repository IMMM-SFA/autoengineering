"""Component and Port definitions for system modeling."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Port:
    """An input or output port on a component."""

    name: str
    direction: str  # "in" or "out"
    data_type: str = "any"  # e.g., "timeseries", "gridded", "scalar"
    units: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "direction": self.direction,
            "data_type": self.data_type,
            "units": self.units,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Port:
        return cls(**data)


@dataclass
class Component:
    """A model component in a system."""

    name: str
    model_type: str = ""  # e.g., "generator", "routing", "downscaling"
    description: str = ""
    inputs: list[Port] = field(default_factory=list)
    outputs: list[Port] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_input(self, name: str, **kwargs) -> Port:
        port = Port(name=name, direction="in", **kwargs)
        self.inputs.append(port)
        return port

    def add_output(self, name: str, **kwargs) -> Port:
        port = Port(name=name, direction="out", **kwargs)
        self.outputs.append(port)
        return port

    def get_port(self, name: str) -> Port | None:
        for port in self.inputs + self.outputs:
            if port.name == name:
                return port
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "model_type": self.model_type,
            "description": self.description,
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Component:
        inputs = [Port.from_dict(p) for p in data.get("inputs", [])]
        outputs = [Port.from_dict(p) for p in data.get("outputs", [])]
        return cls(
            name=data["name"],
            model_type=data.get("model_type", ""),
            description=data.get("description", ""),
            inputs=inputs,
            outputs=outputs,
            metadata=data.get("metadata", {}),
        )

    def to_markdown(self) -> str:
        lines = [f"### {self.name}"]
        if self.model_type:
            lines.append(f"**Type**: {self.model_type}")
        if self.description:
            lines.append(f"**Description**: {self.description}")
        if self.inputs:
            lines.append("**Inputs**:")
            for p in self.inputs:
                lines.append(f"  - `{p.name}` ({p.data_type}){' — ' + p.description if p.description else ''}")
        if self.outputs:
            lines.append("**Outputs**:")
            for p in self.outputs:
                lines.append(f"  - `{p.name}` ({p.data_type}){' — ' + p.description if p.description else ''}")
        if self.metadata:
            lines.append("**Metadata**:")
            for k, v in self.metadata.items():
                lines.append(f"  - {k}: {v}")
        return "\n".join(lines)
