"""Explicit scalar contracts for the pinned engineering circuit."""
from importlib.metadata import version
from pathlib import Path

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.openmdao import OpenMdaoAdapter, VariableBinding
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract
from autoengineering.campaign.serialization import digest
from .model import diagnostics, factory

ROOT = Path(__file__).resolve().parents[3]
VARIABLES = {
    "node1_voltage": ("circuit.n1.V", "V"),
    "node2_voltage": ("circuit.n2.V", "V"),
    "resistor1_current": ("circuit.R1.I", "A"),
    "resistor2_current": ("circuit.R2.I", "A"),
    "diode_current": ("circuit.D1.I", "A"),
}


def context(current, scratch):
    sources = tuple(reference(ROOT, f"examples/interoperability/circuit/{name}",
                              media_type="text/plain", producer="circuit-fixture")
                    for name in ("model.py", "fixture.py", "protocol.json"))
    ports = tuple(PortContract(name, (), units, "float", (), "scalar",
                               digest({"grid": "scalar"}), None)
                  for name, (_, units) in VARIABLES.items())
    model = ModelSnapshot(digest(VARIABLES), {"circuit": "openmdao-3.41.0"}, sources,
                          digest({"openmdao": version("openmdao")}), (), ports)
    return PrepareContext(model, {"source_current": current}, 17, str(scratch), ())


def adapter():
    return OpenMdaoAdapter(
        factory, inputs={},
        outputs={name: VariableBinding(variable, units)
                 for name, (variable, units) in VARIABLES.items()},
        parameters={"source_current": VariableBinding("source.I", "A")},
        inspector=diagnostics,
    )
