# Function-network example

This example shows the representation and evidence path for a three-component function network.
It records one complete system action and one `score` component action, then reconstructs scalar
training tables from the ledger and verified NPZ arrays. It runs in the default environment and
does not use a Bayesian policy.

From the repository root after `pixi install`, choose a new output directory:

```sh
pixi run python examples/function_network/run_example.py --output outputs/function-network
```

The directory must not already exist. The run uses no network access. Inspect the final JSON output
and its reconstructed tables alongside the ledger and NPZ artifacts.

The representation is a foundation for the planned model DAG. It does not demonstrate a unified
harness or web app. Separate research backends use component surrogates for optimization. Their
scope and evidence are documented in the [optimization guide](../../docs/optimization.md) and
[BO status](../../docs/bayesian-optimization-status.md).
