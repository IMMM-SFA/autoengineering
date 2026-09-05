"""Physical and empirical model components implementing CSDMS BMI 2.0."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from examples.local_models.bmi_base import ScalarBmi
from examples.local_models import kernels


class PetBmi(ScalarBmi):
    INPUTS = {
        "air_temperature": "degC",
        "maximum_temperature": "degC",
        "minimum_temperature": "degC",
        "day_of_year": "1",
    }
    OUTPUTS = {"potential_evaporation": "mm d-1"}
    TIME_UNITS = "d"

    def _step(self) -> None:
        v = self._values
        if self.parameters["pet"] == "hamon":
            result = kernels.HAMON(v["air_temperature"], v["day_of_year"])
        else:
            result = kernels.HARGREAVES(
                v["air_temperature"],
                v["maximum_temperature"],
                v["minimum_temperature"],
                v["day_of_year"],
            )
        v["potential_evaporation"][:] = result


class SoilBucketBmi(ScalarBmi):
    INPUTS = {"precipitation": "mm d-1", "potential_evaporation": "mm d-1"}
    OUTPUTS = {"actual_evaporation": "mm d-1", "excess_water": "mm d-1", "soil_storage": "mm"}
    TIME_UNITS = "d"

    def _initialize_model(self) -> None:
        self._capacity = float(self.parameters["capacity"])
        if self._capacity <= 0:
            raise ValueError("capacity must be positive")
        self._values["soil_storage"][0] = self._capacity / 2

    def _step(self) -> None:
        v = self._values
        if v["precipitation"][0] < 0 or v["potential_evaporation"][0] < 0:
            raise ValueError("Water flux inputs must be nonnegative")
        aet, excess, storage = kernels.BUCKET(
            v["precipitation"], v["potential_evaporation"], self._capacity, v["soil_storage"][0]
        )
        v["actual_evaporation"][:] = aet
        v["excess_water"][:] = excess
        v["soil_storage"][:] = storage


class LinearReservoirBmi(ScalarBmi):
    INPUTS = {"excess_water": "mm d-1"}
    OUTPUTS = {"flow": "mm d-1", "reservoir_storage": "mm"}
    TIME_UNITS = "d"

    def _initialize_model(self) -> None:
        self._recession = float(self.parameters["recession"])
        if not 0 <= self._recession < 1:
            raise ValueError("recession must be in [0,1)")

    def _step(self) -> None:
        v = self._values
        if v["excess_water"][0] < 0:
            raise ValueError("Excess water must be nonnegative")
        storage = v["reservoir_storage"][0] + v["excess_water"][0]
        v["flow"][0] = (1 - self._recession) * storage
        v["reservoir_storage"][0] = storage - v["flow"][0]


class SolarTemperatureBmi(ScalarBmi):
    INPUTS = {"irradiance": "W m-2", "air_temperature": "degC"}
    OUTPUTS = {"module_temperature": "degC"}

    def _step(self) -> None:
        v = self._values
        v["module_temperature"][:] = kernels.solar_temperature(
            v["irradiance"],
            v["air_temperature"],
            model=self.parameters["temperature"],
            heat_loss=float(self.parameters["heat_loss"]),
        )


class PvWattsDcBmi(ScalarBmi):
    INPUTS = {"irradiance": "W m-2", "module_temperature": "degC"}
    OUTPUTS = {"dc_power": "kW"}

    def _step(self) -> None:
        from pvlib.pvsystem import pvwatts_dc

        v = self._values
        v["dc_power"][:] = pvwatts_dc(
            v["irradiance"], v["module_temperature"], pdc0=2369.0, gamma_pdc=-0.0028
        ) * float(self.parameters["loss"])


class PvWattsInverterBmi(ScalarBmi):
    INPUTS = {"dc_power": "kW"}
    OUTPUTS = {"ac_power": "kW"}

    def _step(self) -> None:
        from pvlib.inverter import pvwatts

        self._values["ac_power"][:] = pvwatts(
            self._values["dc_power"], pdc0=1910.0 / 0.96, eta_inv_nom=0.96
        )


class TemperatureBasisBmi(ScalarBmi):
    INPUTS = {"temperature": "K"}
    OUTPUTS = {"scaled_temperature": "1"}

    def _step(self) -> None:
        self._values["scaled_temperature"][:] = self._values["temperature"] / 800.0


class CopperRegressionBmi(ScalarBmi):
    INPUTS = {"scaled_temperature": "1"}
    OUTPUTS = {"expansion_coefficient": "source_expansion_units"}

    def __init__(
        self, parameters: dict | None = None, training: pd.DataFrame | None = None
    ) -> None:
        super().__init__(parameters)
        self._training = training

    def _initialize_model(self) -> None:
        data = kernels.load_data("copper") if self._training is None else self._training
        train = data.loc[data.split == "train"]
        self._degree = 2 if self.parameters["model"] == "rational2" else 3
        powers = np.polynomial.polynomial.polyvander(
            train.temperature_k.to_numpy() / 800.0, self._degree
        )
        y = train.expansion.to_numpy()
        ridge = float(self.parameters["ridge"])
        if self.parameters["model"] == "polynomial":
            self._numerator = np.linalg.lstsq(
                np.vstack([powers, np.sqrt(ridge) * np.eye(self._degree + 1)]),
                np.r_[y, np.zeros(self._degree + 1)],
                rcond=None,
            )[0]
            self._denominator = np.zeros(self._degree)
            return

        def residual(params):
            predicted = (powers @ params[: self._degree + 1]) / (
                1 + powers[:, 1:] @ params[self._degree + 1 :]
            )
            return np.r_[predicted - y, np.sqrt(ridge) * params]

        initial = np.r_[np.linalg.lstsq(powers, y, rcond=None)[0], np.zeros(self._degree)]
        lower = np.r_[np.full(self._degree + 1, -np.inf), np.zeros(self._degree)]
        fit = least_squares(residual, initial, bounds=(lower, np.inf), max_nfev=500)
        if not fit.success:
            raise ValueError(f"Rational fit failed: {fit.message}")
        self._numerator = fit.x[: self._degree + 1]
        self._denominator = fit.x[self._degree + 1 :]

    def _step(self) -> None:
        powers = np.polynomial.polynomial.polyvander(
            self._values["scaled_temperature"], self._degree
        )
        self._values["expansion_coefficient"][:] = (powers @ self._numerator) / (
            1 + powers[:, 1:] @ self._denominator
        )
