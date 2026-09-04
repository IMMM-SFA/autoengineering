# Examples

Run examples from the repository root after `pixi install`. Four examples execute model chains and
component improvement workflows. The two optimization examples cover the Release A whole-system
controller and the later function-network representation.

| Example | Purpose | Network access | Command |
| --- | --- | --- | --- |
| [`hydro_chain`](hydro_chain/) | Synthetic three-component hydrology workflow and model swap. | No | `pixi run python examples/hydro_chain/run_workflow.py` |
| [`signal_chain`](signal_chain/) | Synthetic signal generator, filter, and detector workflow. | No | `pixi run python examples/signal_chain/run_workflow.py` |
| [`lotka_volterra`](lotka_volterra/) | Predator-prey ODE workflow and functional-response replacement. | No | `pixi run python examples/lotka_volterra/run_workflow.py` |
| [`leaf_river`](leaf_river/) | Rainfall-runoff workflow using USGS and NOAA observations. | No with checked cache | `pixi run python examples/leaf_river/run_workflow.py` |
| [`optimization_chain`](optimization_chain/) | Deterministic mixed-space whole-system optimization with resume. | No | See below. |
| [`function_network`](function_network/) | NPZ-backed system and component evaluation with deterministic training-table replay. | No | See below. |

The Leaf River observations are checked into `leaf_river/data/`, so a fresh checkout does not need
network access. Its fetcher contacts USGS and NOAA only if those cache files are absent. The
[`README`](leaf_river/README.md) also documents the automated component research workflow.

## Optimization chain

Start with a bounded invocation:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --max-new-evaluations 3
```

Resume the same study:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --resume
```

This example is self-contained and uses no network resources. Its
[`README`](optimization_chain/README.md) explains the objective, constraint, durable artifacts, and
reproducibility check. The broader [optimization guide](../docs/optimization.md) defines the strict
run contract and the boundary between Release A whole-system optimization and later
function-network research.

## Function network

Run the representation and replay example with a new output directory:

```sh
pixi run python examples/function_network/run_example.py --output outputs/function-network
```

The example validates an immutable function-network description against its `System`, evaluates
one system action and one component action, then reconstructs four scalar training rows from the
ledger and verified NPZ artifacts. Its [`README`](function_network/README.md) describes the checked
files and output contract.
