# Function-network representation example

This default-environment example evaluates a fixed three-component chain without a Bayesian
backend. It records one complete system action and one `score` component action. Both actions write
arrays to verified NPZ artifacts and scalar observations to the JSONL ledger. The final JSON file
contains component training tables reconstructed from those durable records.

Run it from the repository root with a new output path:

```bash
pixi run python examples/function_network/run_example.py --output /tmp/function-network-example
```

The output directory must not already exist. The example does not use network access.
