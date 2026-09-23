"""BMI 2.0 control, variable and scalar-grid contract for the example models."""

from __future__ import annotations

from pathlib import Path

from bmipy import Bmi
import numpy as np
import yaml


class ScalarBmi(Bmi):
    """Shared scalar-grid plumbing; concrete subclasses implement numerical steps.

    Values are float64 arrays of length one. Water time is measured in days.
    Steady-state components use dimensionless sample-index time (units ``1``).
    Pointers remain stable until finalize. Inputs persist until replaced by the driver.
    """

    INPUTS: dict[str, str] = {}
    OUTPUTS: dict[str, str] = {}
    TIME_UNITS = "1"

    def __init__(self, parameters: dict | None = None) -> None:
        self._parameters = dict(parameters or {})
        self._initialized = False

    def initialize(self, config_file: str | None = None) -> None:
        if self._initialized:
            raise RuntimeError("Finalize before initializing again")
        params = dict(self._parameters)
        if config_file is not None:
            supplied = yaml.safe_load(Path(config_file).read_text())
            if not isinstance(supplied, dict):
                raise ValueError("BMI configuration must be a YAML mapping")
            params.update(supplied)
        self.parameters = params
        self._time = 0.0
        self._end = float(params.get("end_time", 1.0))
        if not np.isfinite(self._end) or self._end < 0 or not self._end.is_integer():
            raise ValueError("end_time must be a finite nonnegative integer number of steps")
        self._values = {
            name: np.zeros(1, dtype=np.float64) for name in (*self.INPUTS, *self.OUTPUTS)
        }
        self._initialize_model()
        self._initialized = True

    def _initialize_model(self) -> None:
        pass

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("BMI model is not initialized")

    def _variable(self, name: str) -> np.ndarray:
        self._require_initialized()
        return self._values[name]

    def update(self) -> None:
        self._require_initialized()
        if self._time >= self._end:
            raise RuntimeError("BMI model has reached end_time")
        if not all(np.isfinite(value).all() for value in self._values.values()):
            raise ValueError("BMI exchange values must be finite")
        self._step()
        self._time += 1.0

    def _step(self) -> None:
        raise NotImplementedError

    def update_until(self, time: float) -> None:
        self._require_initialized()
        target = float(time)
        if (
            not np.isfinite(target)
            or target < self._time
            or target > self._end
            or not target.is_integer()
        ):
            raise ValueError("Target must be a forward, in-range whole time step")
        while self._time < target:
            self.update()

    def finalize(self) -> None:
        self._values = {}
        self._initialized = False

    def get_component_name(self) -> str:
        return type(self).__name__

    def get_input_item_count(self) -> int:
        return len(self.INPUTS)

    def get_output_item_count(self) -> int:
        return len(self.OUTPUTS)

    def get_input_var_names(self) -> tuple[str, ...]:
        return tuple(self.INPUTS)

    def get_output_var_names(self) -> tuple[str, ...]:
        return tuple(self.OUTPUTS)

    def get_var_grid(self, name: str) -> int:
        self._variable(name)
        return 0

    def get_var_type(self, name: str) -> str:
        return str(self._variable(name).dtype)

    def get_var_units(self, name: str) -> str:
        self._variable(name)
        return (self.INPUTS | self.OUTPUTS)[name]

    def get_var_itemsize(self, name: str) -> int:
        return self._variable(name).itemsize

    def get_var_nbytes(self, name: str) -> int:
        return self._variable(name).nbytes

    def get_var_location(self, name: str) -> str:
        self._variable(name)
        return "node"

    def get_current_time(self) -> float:
        self._require_initialized()
        return self._time

    def get_start_time(self) -> float:
        return 0.0

    def get_end_time(self) -> float:
        self._require_initialized()
        return self._end

    def get_time_units(self) -> str:
        return self.TIME_UNITS

    def get_time_step(self) -> float:
        return 1.0

    def get_value(self, name: str, dest: np.ndarray) -> np.ndarray:
        np.copyto(dest, self._variable(name), casting="same_kind")
        return dest

    def get_value_ptr(self, name: str) -> np.ndarray:
        return self._variable(name)

    @staticmethod
    def _indices(inds: np.ndarray) -> np.ndarray:
        indices = np.asarray(inds)
        if not np.issubdtype(indices.dtype, np.integer) or np.any(indices != 0):
            raise IndexError("Scalar grid indices must be zero")
        return indices

    def get_value_at_indices(self, name: str, dest: np.ndarray, inds: np.ndarray) -> np.ndarray:
        np.copyto(dest, self._variable(name)[self._indices(inds)], casting="same_kind")
        return dest

    def set_value(self, name: str, src: np.ndarray) -> None:
        value = np.asarray(src)
        if value.shape != (1,) or not np.isfinite(value).all():
            raise ValueError("Scalar BMI values must be finite arrays of shape (1,)")
        np.copyto(self._variable(name), value, casting="same_kind")

    def set_value_at_indices(self, name: str, inds: np.ndarray, src: np.ndarray) -> None:
        value = np.asarray(src)
        if value.shape != np.asarray(inds).shape or not np.isfinite(value).all():
            raise ValueError("Indexed BMI values must match indices and be finite")
        self._variable(name)[self._indices(inds)] = value

    def _grid(self, grid: int) -> None:
        self._require_initialized()
        if grid != 0:
            raise ValueError("Only scalar grid 0 exists")

    def get_grid_rank(self, grid: int) -> int:
        self._grid(grid)
        return 0

    def get_grid_size(self, grid: int) -> int:
        self._grid(grid)
        return 1

    def get_grid_type(self, grid: int) -> str:
        self._grid(grid)
        return "scalar"

    def get_grid_shape(self, grid: int, shape: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no structured shape")

    def get_grid_spacing(self, grid: int, spacing: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no spacing")

    def get_grid_origin(self, grid: int, origin: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no structured origin")

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("These lumped models have no spatial coordinates")

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("These lumped models have no spatial coordinates")

    def get_grid_z(self, grid: int, z: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("These lumped models have no spatial coordinates")

    def get_grid_node_count(self, grid: int) -> int:
        self._grid(grid)
        return 1

    def get_grid_edge_count(self, grid: int) -> int:
        self._grid(grid)
        return 0

    def get_grid_face_count(self, grid: int) -> int:
        self._grid(grid)
        return 0

    def get_grid_edge_nodes(self, grid: int, edge_nodes: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no edges")

    def get_grid_face_edges(self, grid: int, face_edges: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no faces")

    def get_grid_face_nodes(self, grid: int, face_nodes: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no faces")

    def get_grid_nodes_per_face(self, grid: int, nodes_per_face: np.ndarray) -> np.ndarray:
        self._grid(grid)
        raise NotImplementedError("Scalar grids have no faces")
