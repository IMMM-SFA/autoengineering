"""Test exact solar component reuse and a scalar-coupling counterexample."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from examples.local_models.models import load_data, solar_model, solar_power, solar_temperature


def probe(output: Path) -> dict[str, object]:
    """Preserve temperature arrays; measure real costs without artificial delays."""
    data = load_data("solar")
    data = data.loc[data.split != "test"]
    poa, air = data.poa_w_m2.to_numpy(), data.air_c.to_numpy()
    config = {"temperature": "ross", "heat_loss": 25.0, "loss": 0.9}
    complete = solar_model(data, config)
    output.mkdir(parents=True, exist_ok=False)
    artifact = output / "temperature.npz"
    np.savez(artifact, poa=poa, module_temperature=complete["temperature"])
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with np.load(artifact, allow_pickle=False) as stored:
        rerun = solar_power(stored["poa"], stored["module_temperature"], loss=0.85)
    full = solar_model(data, dict(config, loss=0.85))["prediction"]
    np.testing.assert_array_equal(rerun, full)
    # Both traces have the same mean. Their covariance with irradiance differs.
    permuted = complete["temperature"][::-1]
    power_a = solar_power(poa, complete["temperature"], loss=0.9)
    power_b = solar_power(poa, permuted, loss=0.9)

    def median_seconds(callable_):
        timings = []
        for _ in range(11):
            started = time.perf_counter()
            callable_()
            timings.append(time.perf_counter() - started)
        return float(np.median(timings))

    result = {
        "parent_sha256": digest,
        "reused_power_matches_full": bool(np.array_equal(rerun, full)),
        "temperature_mean_difference": float(np.mean(complete["temperature"]) - np.mean(permuted)),
        "mean_power_difference_kw": float(np.mean(power_a) - np.mean(power_b)),
        "temperature_seconds": median_seconds(
            lambda: solar_temperature(poa, air, model="ross", heat_loss=25.0)
        ),
        "power_seconds": median_seconds(
            lambda: solar_power(poa, complete["temperature"], loss=0.9)
        ),
        "full_seconds": median_seconds(lambda: solar_model(data, config)),
        "partial_bo_application_status": "unresolved_scalar_time_series_representation",
        "scope": "component reuse and representation probe; no partial BO efficacy claim",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(probe(parser.parse_args().output), indent=2))
