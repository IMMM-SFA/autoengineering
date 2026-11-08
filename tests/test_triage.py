"""Tests for ecosystem bottleneck & error-propagation triage and physical vetoes."""

from __future__ import annotations

import json
import numpy as np
import pytest
from click.testing import CliRunner

from autoengineering.cli import cli
from autoengineering.research.candidates import Candidate
from autoengineering.research.loop import auto_improve
from autoengineering.system.graph import System
from autoengineering.triage import triage_system
from autoengineering.validate.compare import (
    PhysicalCheck,
    evaluate_physical_checks,
    low_flow_pbias,
    pbias,
)


def _build_demo_system() -> System:
    system = System(name="demo_water_chain", description="Three-component test chain")
    system.add_component(
        name="land_surface",
        model_type="process_based",
        inputs={"forcing": "timeseries"},
        outputs={"runoff": "timeseries"},
        metadata={
            "compute_cost": {
                "hpc_hours_per_run": 240.0,
                "emulator_training_hours": 480.0,
                "emulator_inference_hours": 0.01,
                "local_runtime_seconds": 12.0,
            },
            "tunable_parameters": 8,
        },
    )
    system.add_component(
        name="water_demand",
        model_type="empirical",
        inputs={"population": "timeseries"},
        outputs={"withdrawal": "timeseries"},
        metadata={
            "compute_cost": {
                "hpc_hours_per_run": 0.5,
                "local_runtime_seconds": 0.2,
            },
            "structural_deficit": True,
            "tunable_parameters": 2,
        },
    )
    system.add_component(
        name="river_routing",
        model_type="process_based",
        inputs={"runoff": "timeseries", "withdrawal": "timeseries"},
        outputs={"streamflow": "timeseries"},
        metadata={
            "compute_cost": {
                "hpc_hours_per_run": 0.1,
                "local_runtime_seconds": 0.05,
            },
            "tunable_parameters": 3,
        },
    )
    system.connect("land_surface", "river_routing", "runoff", "runoff")
    system.connect("water_demand", "river_routing", "withdrawal", "withdrawal")
    return system


class TestTriageEngine:
    def test_triage_recommendations_and_emulator_roi(self):
        system = _build_demo_system()
        obs = np.linspace(10.0, 100.0, 50)

        def perturber(comp_name: str, frac: float) -> dict[str, np.ndarray]:
            runoff = obs * (1.05 * (1.0 + (frac if comp_name == "land_surface" else 0.0)))
            demand = 5.0 * (1.0 + (frac if comp_name == "water_demand" else 0.0))
            routing_factor = 1.0 + (frac if comp_name == "river_routing" else 0.0)
            flow = (runoff - demand) * routing_factor
            return {"streamflow": flow}

        report = triage_system(
            system,
            observed=obs,
            validate_output="streamflow",
            component_perturber=perturber,
            perturbation_fraction=0.10,
        )

        by_name = {c.component: c for c in report.components}
        assert by_name["land_surface"].recommendation == "ai_emulator"
        assert by_name["land_surface"].emulator_roi.viable is True
        assert by_name["land_surface"].emulator_roi.breakeven_runs == 3
        assert by_name["land_surface"].emulator_roi.speedup_factor > 1000.0
        assert by_name["water_demand"].recommendation == "component_swap"

        md = report.to_markdown()
        assert "Ecosystem Triage Report" in md
        assert "ai_emulator" in md
        parsed = json.loads(report.to_json())
        assert parsed["system_name"] == "demo_water_chain"

    def test_cli_triage_command(self, tmp_path):
        system = _build_demo_system()
        yaml_path = tmp_path / "system.yaml"
        system.to_yaml(yaml_path)
        out_json = tmp_path / "triage.json"

        runner = CliRunner()
        res = runner.invoke(
            cli,
            ["triage", str(yaml_path), "--format", "json", "-o", str(out_json)],
        )
        assert res.exit_code == 0, res.output
        payload = json.loads(out_json.read_text())
        assert payload["system_name"] == "demo_water_chain"
        assert len(payload["components"]) == 3


class TestPhysicalChecksAndVetoes:
    def test_pbias_and_low_flow_pbias(self):
        obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        sim = obs * 1.20
        assert pytest.approx(pbias(obs, sim), rel=1e-6) == 20.0
        assert pytest.approx(low_flow_pbias(obs, sim, quantile=0.20), rel=1e-6) == 20.0

    def test_evaluate_physical_checks(self):
        outputs = {
            "streamflow": np.array([1.0, -0.5, 3.0]),
            "inflow": np.array([10.0, 10.0, 10.0]),
            "outflow": np.array([10.0, 10.0, 10.0]),
        }
        checks = [
            PhysicalCheck(name="positive_flow", kind="nonnegative", port="streamflow"),
            PhysicalCheck(
                name="water_balance",
                kind="mass_balance",
                inflow_ports=("inflow",),
                outflow_ports=("outflow",),
                tolerance=1e-6,
            ),
        ]
        results = evaluate_physical_checks(outputs, checks)
        assert results[0].passed is False
        assert results[1].passed is True

    def test_auto_improve_vetoes_unphysical_candidate(self, tmp_path):
        system = _build_demo_system()
        obs = np.array([10.0, 20.0, 30.0, 40.0])

        def run_chain(sys_obj: System) -> dict[str, np.ndarray]:
            comp = sys_obj.get_component("land_surface")
            mode = comp.metadata.get("mode", "baseline")
            if mode == "unphysical_high_kge":
                return {
                    "streamflow": np.array([10.0, 20.0, 30.0, 40.0]),
                    "storage": np.array([5.0, -2.0, 3.0, 4.0]),
                }
            if mode == "physical_good":
                return {
                    "streamflow": np.array([9.8, 19.8, 30.1, 40.2]),
                    "storage": np.array([5.0, 4.0, 3.0, 4.0]),
                }
            return {
                "streamflow": np.array([8.0, 16.0, 24.0, 32.0]),
                "storage": np.array([5.0, 5.0, 5.0, 5.0]),
            }

        candidates = [
            Candidate(
                name="land_surface",
                model_type="ml_hybrid",
                description="Higher KGE but negative storage",
                metadata={"mode": "unphysical_high_kge"},
                rationale="Overfits streamflow by draining storage below zero.",
            ),
            Candidate(
                name="land_surface",
                model_type="process_based",
                description="Physically consistent improvement",
                metadata={"mode": "physical_good"},
                rationale="Respects storage nonnegativity while improving KGE.",
            ),
        ]

        tree = auto_improve(
            system,
            run_chain,
            obs,
            validate_output="streamflow",
            candidates=candidates,
            physical_checks=[
                PhysicalCheck(name="nonnegative_storage", kind="nonnegative", port="storage")
            ],
            workdir=tmp_path,
        )

        statuses = [n.status for n in tree.nodes.values()]
        assert "vetoed" in statuses
        assert "kept" in statuses
        assert tree.best().description == "Physically consistent improvement"
