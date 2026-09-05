"""BMI lifecycle, exchange, state and numerical parity for the real examples."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

pytest.importorskip("bmipy")
pytest.importorskip("pvlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bmipy import Bmi
from examples.local_models import bmi_components as b, kernels, models
from examples.local_models.bmi_chain import run_components

CASES = [
    (b.PetBmi, {"pet": "hamon"}),
    (b.SoilBucketBmi, {"capacity": 100.0}),
    (b.LinearReservoirBmi, {"recession": 0.7}),
    (b.SolarTemperatureBmi, {"temperature": "ross", "heat_loss": 25.0}),
    (b.PvWattsDcBmi, {"loss": 0.9}),
    (b.PvWattsInverterBmi, {}),
    (b.TemperatureBasisBmi, {}),
    (b.CopperRegressionBmi, {"model": "rational3", "ridge": 1e-6}),
]


@pytest.mark.parametrize("cls,config", CASES)
def test_bmi_lifecycle_metadata_copy_pointer_and_indexing(cls, config):
    model = cls(dict(config, end_time=3))
    assert isinstance(model, Bmi)
    model.initialize()
    assert model.get_input_item_count() == len(model.get_input_var_names())
    assert model.get_output_item_count() == len(model.get_output_var_names())
    assert model.get_grid_type(0) == "scalar"
    assert model.get_grid_rank(0) == 0
    assert model.get_grid_size(0) == 1
    assert model.get_grid_node_count(0) == 1
    assert model.get_grid_edge_count(0) == model.get_grid_face_count(0) == 0
    variable = model.get_input_var_names()[0]
    model.set_value(variable, np.array([1.0]))
    pointer = model.get_value_ptr(variable)
    destination = np.empty(1)
    assert model.get_value(variable, destination) is destination
    destination[0] = 99.0
    assert pointer[0] == 1.0
    model.set_value_at_indices(variable, np.array([0]), np.array([2.0]))
    assert pointer[0] == 2.0
    model.get_value_at_indices(variable, destination, np.array([0]))
    assert destination[0] == 2.0
    with pytest.raises(IndexError):
        model.set_value_at_indices(variable, np.array([-1]), np.array([3.0]))
    for name in (*model.get_input_var_names(), *model.get_output_var_names()):
        assert model.get_var_grid(name) == 0
        assert model.get_var_type(name) == "float64"
        assert model.get_var_itemsize(name) == model.get_var_nbytes(name) == 8
        assert model.get_var_units(name)
        assert model.get_var_location(name) == "node"
    with pytest.raises(ValueError):
        model.update_until(0.5)
    assert model.get_current_time() == 0.0
    model.update_until(2.0)
    assert model.get_current_time() == 2.0
    assert model.get_value_ptr(variable) is pointer
    with pytest.raises(ValueError):
        model.update_until(1.0)
    model.update()
    with pytest.raises(RuntimeError):
        model.update()
    model.finalize()
    with pytest.raises(RuntimeError):
        model.get_value_ptr(variable)
    model.initialize()
    assert model.get_current_time() == 0.0
    model.finalize()


def test_yaml_initialization_and_soil_storage_persists(tmp_path):
    path = tmp_path / "bucket.yaml"
    path.write_text("capacity: 100\nend_time: 2\n")
    model = b.SoilBucketBmi()
    model.initialize(str(path))
    model.set_value("precipitation", np.array([20.0]))
    model.set_value("potential_evaporation", np.array([0.0]))
    model.update()
    assert model.get_value_ptr("soil_storage")[0] == 70.0
    model.update()
    assert model.get_value_ptr("soil_storage")[0] == 90.0
    assert model.get_time_units() == "d"
    model.finalize()


@pytest.mark.parametrize("domain", models.DOMAINS)
def test_bmi_chains_match_independent_vectorized_reference(domain):
    data = models.load_data(domain)
    for config in [models.BASELINES[domain], *models.SWAPS[domain]]:
        actual = models.MODELS[domain](data, config)
        reference = kernels.MODELS[domain](data, config)
        for name in reference:
            np.testing.assert_allclose(actual[name], reference[name], rtol=1e-12, atol=1e-12)


def test_missing_bmi_forcing_rejected_and_models_finalized():
    model = b.SoilBucketBmi({"capacity": 100.0, "end_time": 1})
    with pytest.raises(ValueError, match="exactly one source"):
        run_components({"soil": model}, [], {"soil": {"precipitation": np.array([1.0])}}, 1)
    with pytest.raises(RuntimeError):
        model.get_current_time()


def test_incompatible_bmi_clock_rejected():
    class DifferentClock(b.SoilBucketBmi):
        def get_time_step(self):
            return 0.5

    model = DifferentClock({"capacity": 100.0, "end_time": 1})
    with pytest.raises(ValueError, match="step=1"):
        run_components({"soil": model}, [], {}, 1)
    with pytest.raises(RuntimeError):
        model.get_current_time()
