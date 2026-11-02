"""Keep scientific failure evidence when cleanup also fails."""
import numpy as np
import pytest

from autoengineering.adapters.python import PythonAdapter, run_lifecycle
from test_bmi_adapter import context


class Adapter(PythonAdapter):
    def cleanup(self, handle):
        raise RuntimeError("cleanup failure")


def test_primary_failure_survives_cleanup():
    ctx = context()

    def fail(*args):
        raise ValueError("model failure")

    adapter = Adapter(fail, lambda params: None)
    with pytest.raises(ValueError, match="model failure") as error:
        run_lifecycle(
            adapter, ctx, {"forcing": np.ones(3)}, ctx.model.inputs, ctx.model.outputs,
        )
    assert error.value.__notes__ == ["adapter cleanup failed: cleanup failure"]


def test_cleanup_failure_after_success_is_visible():
    ctx = context()
    adapter = Adapter(lambda *args: {"flow": np.ones(3)}, lambda params: None)
    with pytest.raises(RuntimeError, match="cleanup failure"):
        run_lifecycle(
            adapter, ctx, {"forcing": np.ones(3)}, ctx.model.inputs, ctx.model.outputs,
        )
