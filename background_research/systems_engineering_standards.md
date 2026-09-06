# Standards and interfaces

Autoengineering currently describes systems in YAML and a NetworkX graph. Runnable metadata and
optimization evaluators connect that description to model execution. A unified model DAG and
harness are still planned.

Earlier notes considered SysML and model coupling standards. Treat those as integration questions,
not adopted dependencies. The project has no SysML import/export or BMI adapter contract today.

## Questions for the model DAG

The DAG needs stable identities for model implementations, ports, parameters, data, and results.
Before adding an external representation, specify which records must survive a round trip and
which relationships determine execution. Units, time support, observation availability, and model
versions need explicit treatment.

SysML integration is a possible later adapter. The earlier investigation used the
[Systems Modeling repository](https://github.com/Systems-Modeling/SysML-v2-Release) as a starting
reference. A future adapter should demonstrate a small round trip with preserved meaning before
becoming a workflow dependency.

## Questions for the harness

The harness needs consistent preparation, execution, inspection, and error behavior across model
adapters. It must also state who controls model state, time stepping, and data exchange.
The [BMI documentation](https://bmi.readthedocs.io/en/latest/) is a reference for investigating
adapters where a model already exposes that interface. Compatibility has not been demonstrated in
this package.

Document how any adapter maps into the existing runnable and evaluator interfaces. Check units,
state, time support, and failure behavior through a working example. Keep standard selection
separate from a claim that an integration is complete.

## Design decisions still open

We need to decide which fields belong in the common DAG, how stateful or coupled models fit the
execution contract, and whether external standard adapters justify their maintenance cost.
The [roadmap](../docs/roadmap.md) records the proposed completion criteria.
