# Autoengineering Concept

This is the conceptual design for the autoengineering workflow.

## The Autoengineer

The auto-engineer is a friendly systems engineer who can help you improve your systems. The auto-engineer is knowledgeable in the principles of [systems engineering](https://en.wikipedia.org/wiki/Systems_engineering), [systems modeling](https://en.wikipedia.org/wiki/Systems_modeling), and is proficient in [systems thinking](https://en.wikipedia.org/wiki/Systems_thinking) and passionate about helping with [managing complexity](https://en.wikipedia.org/wiki/Systems_engineering#Managing_complexity). It is ready and willing to help you improve your system.

## Your System

In order to help you, the auto-engineer requires a system to work with and information about how the system is connected. In this context "your system" refers to a [Complex System](https://en.wikipedia.org/wiki/Complex_system) that is represented by one or more [models](https://en.wikipedia.org/wiki/Systems_engineering). The auto-engineer is most effective when working with [hard systems](https://en.wikipedia.org/wiki/Hard_systems) composed of computer models. Some examples of models that work well with the autoengineering workflow are [mathematical models](https://en.wikipedia.org/wiki/Mathematical_modeling) (including [scientific models](https://en.wikipedia.org/wiki/Scientific_modelling)), [agent-based models](https://en.wikipedia.org/wiki/Agent-based_model), and [data models](https://en.wikipedia.org/wiki/Data_modeling).

## Input Data

The key pieces of information that the auto-engineer needs to help you are:

1. **A structured system definition** — A YAML file describing each component, its inputs/outputs, and how components connect. The `autoengineering` Python package loads this into a [NetworkX](https://networkx.org/) graph for analysis. Future versions will support [SysML v2 (Textual)](https://github.com/Systems-Modeling/SysML-v2-Release).
2. **A network graph representation** — Created automatically from the YAML definition via NetworkX.
3. **A description of how components interconnect** — Defined through port connections in the system definition. For runtime coupling, the [BMI (Basic Model Interface)](https://csdms.colorado.edu/wiki/BMI) standard is recommended.
4. **An established baseline to compare against** — Baseline data (observed or reference model output) for validating each component [1].

The auto-engineer can also help you develop these inputs if you do not have them already defined. All you really need to get started is your system.

## The Workflow

The auto-engineer helps optimize your system by identifying the highest-value components to improve or replace. The workflow has four steps:

### Step 1: Define
Define your system using a YAML system definition file. Describe each component (name, type, inputs, outputs, metadata) and how they connect.

```bash
autoengineering describe system.yaml    # inspect the system
autoengineering graph system.yaml       # generate a diagram
```

### Step 2: Validate
Validate each system component against its established baseline. Compute standard metrics (RMSE, bias, NSE, KGE, correlation) and flag components that fail thresholds.

```bash
autoengineering validate system.yaml -c rainfall_runoff -b baselines/runoff.csv -s simulated/runoff.csv
```

### Step 3: Analyze
Identify which components can be improved or replaced entirely, and estimate the potential overall improvement. Components are ranked by their improvement potential score.

```bash
autoengineering report system.yaml -r validation_results.json
```

### Step 4: Improve
Swap in an improved component, re-run validation, and quantify the improvement. Compare before/after metrics to demonstrate the value of the change.

## Quick Start

1. Install the `autoengineering` package:
   ```bash
   cd autoengineering/
   pixi install
   pixi run install
   ```

2. Run an example:
   ```bash
   # Simple 3-component hydrology chain
   pixi run python examples/hydro_chain/run_workflow.py

   # Signal processing (synthetic, no domain knowledge needed)
   pixi run python examples/signal_chain/run_workflow.py

   # Predator-prey ODEs (Lotka-Volterra)
   pixi run python examples/lotka_volterra/run_workflow.py

   # Real-data hydrology: Leaf River, MS (fetches USGS/NOAA data)
   pixi run python examples/leaf_river/run_workflow.py
   ```

3. Or invoke the auto-engineer agent in Claude Code to walk through the workflow interactively.

## Background Research
- [Systems engineering standards](background_research/systems_engineering_standards.md)
- [Workflow tools](background_research/workflow_tools.md)

## Related Concepts
- [SEQUAL framework](https://en.wikipedia.org/wiki/SEQUAL_framework)
- [The UML language](https://en.wikipedia.org/wiki/Unified_Modeling_Language)

## References
[1] SYSTEMS ENGINEERING FUNDAMENTALS - DEFENSE ACQUISITION UNIVERSITY PRESS FORT BELVOIR, VIRGINIA 22060-5565
[2] [SEH 2.0 Fundamentals of Systems Engineering](https://www.nasa.gov/reference/2-0-fundamentals-of-systems-engineering/)
[3] [NASA Systems Engineering Handbook](https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf)
