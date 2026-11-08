"""Integration tests for the flagship DOE IM3 Water-Scarcity 9-Subcomponent example."""

from __future__ import annotations

from pathlib import Path
import pytest

from autoengineering.research.candidates import load_candidates
from autoengineering.system.graph import System
from autoengineering.triage import triage_system
from examples.im3_water_scarcity.run_workflow import BUNDLE_PATH, HERE, run_im3_workflow


class TestIM3WaterScarcityExample:
    def test_system_and_candidates_yaml_contract(self):
        system = System.from_yaml(HERE / "system.yaml")
        assert system.name == "im3_conus_water_scarcity_subcomponents"
        assert len(system.components) == 9
        order = system.topological_order()
        assert order[-1] == "mosart_reservoir_demand_wm"
        assert "lsm_canopy_snow_et" in order
        assert "lsm_surface_infiltration" in order
        assert "lsm_subsurface_drainage" in order
        assert "tethys_irrigation_downscaler" in order
        assert "tethys_thermoelectric_industrial_downscaler" in order
        assert "tethys_municipal_domestic_downscaler" in order
        assert "mosart_hillslope_tributary_routing" in order
        assert "mosart_channel_network_routing" in order

        candidates = load_candidates(HERE / "candidates.yaml")
        assert len(candidates) == 12
        report = triage_system(system)
        by_comp = {c.component: c for c in report.components}
        # The 20-layer Richards vadose solver (120 node-hrs) is the #1 compute bottleneck
        assert by_comp["lsm_subsurface_drainage"].upstream_hpc_hours == 120.0
        assert by_comp["lsm_subsurface_drainage"].emulator_roi.viable is True

    @pytest.mark.skipif(not BUNDLE_PATH.exists(), reason="Local IM3 bundle not staged")
    def test_end_to_end_im3_workflow(self, tmp_path: Path):
        summary = run_im3_workflow(tmp_path)
        assert summary["n_gauges_total"] == 1190
        assert summary["n_gauges_natural_hcdn"] == 672
        assert summary["n_gauges_regulated_dams"] == 518

        statuses = {s["status"] for s in summary["stages"]}
        assert "baseline" in statuses
        assert "vetoed" in statuses
        assert "reverted" in statuses
        assert "kept" in statuses

        # Final retained internal physics stage outperforms baseline across all regimes
        base_st = summary["stages"][0]
        final_st = summary["stages"][-1]
        assert final_st["conus_kge"] > base_st["conus_kge"] + 0.05
        assert (
            final_st["median_gauge_kge_small_basins"]
            > base_st["median_gauge_kge_small_basins"] + 0.30
        )
        assert (
            final_st["median_gauge_kge_regulated"]
            > base_st["median_gauge_kge_regulated"] + 0.30
        )

        # Whole-model emulator comparison points verify that blind upstream emulation alone
        # cannot fix downstream small-basin routing or regulated reservoir skill
        bms = summary["whole_model_emulator_benchmarks"]
        blind_emu = bms["whole_lsm_emulator_without_downstream_fixes"]
        last_resort_emu = bms["whole_lsm_emulator_after_internal_fixes_last_resort"]
        assert final_st["conus_kge"] > blind_emu["conus_kge"] + 0.06
        assert (
            final_st["median_gauge_kge_small_basins"]
            > blind_emu["median_gauge_kge_small_basins"] + 0.30
        )
        assert last_resort_emu["hpc_node_hours"] < 5.0

        assert (tmp_path / "triage_report.md").is_file()
        assert (tmp_path / "im3_conference_summary.md").is_file()
        assert (tmp_path / "figure1_triage_and_emulator_roi.svg").is_file()
        assert (tmp_path / "figure2_im3_intervention_progression.svg").is_file()
