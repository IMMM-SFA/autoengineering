"""Map the bounded native wind driver into the shared callback proposal contract."""

from __future__ import annotations

from pathlib import Path

from autoengineering.utility.callback_native import CallbackCall, CallbackDriverResult
from examples.utility.wind_process import WindDriverSpec, verify_wind_sources
from examples.utility.wind_proposal import WindNativeSpec, propose


def execute(job):
    spec = job.specification
    native = WindNativeSpec.from_json(spec.options_json)
    if dict(spec.callback_limits) != {
        "wake": native.maximum_wake_calls,
        "gradient": native.maximum_gradient_calls,
    }:
        raise ValueError("wind callback ceilings differ from frozen native options")
    wind = WindDriverSpec(
        "utility-wind-driver-v1",
        spec.execution,
        native,
        spec.entrypoint,
        spec.timeout_seconds,
        spec.output_bytes,
    )
    verify_wind_sources(wind, Path(job.source_root))
    proposal = propose(native)
    result = proposal.result
    calls = tuple(
        CallbackCall(
            call.kind,
            call.index,
            call.status,
            {
                f"{axis}_{i}": value
                for axis, values in (("x", call.x), ("y", call.y))
                for i, value in enumerate(values)
            },
            {"annual_energy": call.energy_gwh} if call.energy_gwh is not None else {},
            {"annual_energy": "GWh"} if call.energy_gwh is not None else {},
        )
        for call in result.calls
    )
    final = {
        f"{axis}_{i}": value
        for axis, values in (("x", result.x), ("y", result.y))
        for i, value in enumerate(values)
    }
    return CallbackDriverResult(
        "utility-callback-result-v1",
        job.digest,
        result.status,
        result.driver_success,
        result.feasible,
        final,
        proposal.configuration,
        calls,
        spec.callback_limits,
    )
