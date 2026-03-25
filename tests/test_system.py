"""Tests for the system module."""

import tempfile
from pathlib import Path

import pytest

from autoengineering.system import Component, Port, System


class TestPort:
    def test_create_port(self):
        p = Port(name="flow", direction="out", data_type="timeseries")
        assert p.name == "flow"
        assert p.direction == "out"
        assert p.data_type == "timeseries"

    def test_roundtrip_dict(self):
        p = Port(name="flow", direction="in", data_type="gridded", units="m3/s")
        d = p.to_dict()
        p2 = Port.from_dict(d)
        assert p2.name == p.name
        assert p2.units == p.units


class TestComponent:
    def test_create_component(self):
        c = Component(name="model_a", model_type="routing")
        c.add_input("inflow", data_type="timeseries")
        c.add_output("outflow", data_type="timeseries")
        assert len(c.inputs) == 1
        assert len(c.outputs) == 1
        assert c.get_port("inflow").direction == "in"

    def test_roundtrip_dict(self):
        c = Component(name="model_a", model_type="routing", description="A router")
        c.add_input("inflow", data_type="timeseries")
        c.add_output("outflow", data_type="timeseries")
        d = c.to_dict()
        c2 = Component.from_dict(d)
        assert c2.name == c.name
        assert len(c2.inputs) == 1
        assert len(c2.outputs) == 1

    def test_to_markdown(self):
        c = Component(name="test", model_type="generator")
        c.add_output("data", data_type="timeseries")
        md = c.to_markdown()
        assert "### test" in md
        assert "generator" in md


class TestSystem:
    def _make_system(self):
        s = System("test_chain", "A test system")
        s.add_component("precip", model_type="generator", outputs={"rainfall": "timeseries"})
        s.add_component(
            "runoff",
            model_type="transform",
            inputs={"rainfall": "timeseries"},
            outputs={"flow": "timeseries"},
        )
        s.add_component(
            "reservoir",
            model_type="storage",
            inputs={"inflow": "timeseries"},
            outputs={"release": "timeseries"},
        )
        s.connect("precip", "runoff", port_from="rainfall", port_to="rainfall")
        s.connect("runoff", "reservoir", port_from="flow", port_to="inflow")
        return s

    def test_add_and_get_component(self):
        s = self._make_system()
        assert len(s.component_names) == 3
        c = s.get_component("runoff")
        assert c.model_type == "transform"

    def test_get_missing_component_raises(self):
        s = System("empty")
        with pytest.raises(KeyError):
            s.get_component("nonexistent")

    def test_connections(self):
        s = self._make_system()
        assert len(s.connections) == 2

    def test_upstream_downstream(self):
        s = self._make_system()
        assert "precip" in s.upstream_of("reservoir")
        assert "reservoir" in s.downstream_of("precip")
        assert s.direct_upstream("runoff") == ["precip"]
        assert s.direct_downstream("runoff") == ["reservoir"]

    def test_topological_order(self):
        s = self._make_system()
        order = s.topological_order()
        assert order.index("precip") < order.index("runoff")
        assert order.index("runoff") < order.index("reservoir")

    def test_yaml_roundtrip(self):
        s = self._make_system()
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        s.to_yaml(path)
        s2 = System.from_yaml(path)
        assert s2.name == s.name
        assert s2.component_names == s.component_names
        assert len(s2.connections) == len(s.connections)
        Path(path).unlink()

    def test_to_mermaid(self):
        s = self._make_system()
        mermaid = s.to_mermaid()
        assert "```mermaid" in mermaid
        assert "precip" in mermaid
        assert "-->" in mermaid

    def test_describe(self):
        s = self._make_system()
        desc = s.describe()
        assert "# System: test_chain" in desc
        assert "precip" in desc
        assert "reservoir" in desc

    def test_repr(self):
        s = self._make_system()
        r = repr(s)
        assert "test_chain" in r
        assert "components=3" in r
