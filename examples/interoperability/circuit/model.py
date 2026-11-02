"""Pinned OpenMDAO engineering circuit and explicit inner-work inspection.

Uses OpenMDAO's supplied resistor/diode/implicit-node implementation under its
Apache-2.0 license. No framework code is copied or altered numerically.
"""
from __future__ import annotations

import numpy as np

from autoengineering.adapters.openmdao import SolveDiagnostics


def factory(context):
    import openmdao.api as om
    from openmdao.test_suite.scripts.circuit_analysis import Circuit

    class CircuitProblem(om.Problem):
        def final_setup(self):
            super().final_setup()
            if not getattr(self, "initial_guess_supplied", False):
                self.set_val("circuit.n1.V", 10.)
                self.set_val("circuit.n2.V", 1.)
                self.initial_guess_supplied = True

    problem = CircuitProblem(reports=False)
    problem.model.add_subsystem("source", om.IndepVarComp("I", .05, units="A"))
    problem.model.add_subsystem("ground", om.IndepVarComp("V", 0., units="V"))
    circuit = problem.model.add_subsystem("circuit", Circuit())
    problem.model.connect("source.I", "circuit.I_in")
    problem.model.connect("ground.V", "circuit.Vg")
    # configure runs after the upstream setup has installed its solvers.
    original_configure = circuit.configure

    def configure():
        original_configure()
        solver = circuit.nonlinear_solver
        solver.options.update({"iprint": 0, "maxiter": 100, "atol": 1e-13,
                               "rtol": 1e-14, "err_on_non_converge": True})
        problem.derivative_calls = 0
        for component in circuit.system_iter(recurse=True, include_self=False):
            original = component._linearize

            def counted(*args, _original=original, **kwargs):
                problem.derivative_calls += 1
                return _original(*args, **kwargs)

            component._linearize = counted

    circuit.configure = configure
    return problem


def diagnostics(problem):
    def scalar(name):
        return float(np.asarray(problem.get_val(name)).item())

    residuals = [
        scalar("source.I") - scalar("circuit.R1.I") - scalar("circuit.R2.I"),
        scalar("circuit.R2.I") - scalar("circuit.D1.I"),
    ]
    v1, v2 = scalar("circuit.n1.V"), scalar("circuit.n2.V")
    residuals.extend([
        v1 / 100. - scalar("circuit.R1.I"),
        (v1 - v2) / 10000. - scalar("circuit.R2.I"),
        1e-15 * (np.exp(v2 / .025875) - 1.) - scalar("circuit.D1.I"),
    ])
    if not np.isfinite(residuals).all():
        raise ValueError("circuit residuals must all be finite")
    residual = float(max(abs(r) for r in residuals))
    circuit = problem.model.circuit
    # These two instrumentation hooks are bound to OpenMDAO 3.41.0 source.
    # They are not a portable OpenMDAO API or a compatibility claim.
    return SolveDiagnostics(
        residual <= 1e-10, residual, 1e-10, circuit.nonlinear_solver._iter_count,
        sum(c.iter_count + c.iter_count_apply for c in circuit.system_iter(recurse=True)),
        problem.derivative_calls,
    )
