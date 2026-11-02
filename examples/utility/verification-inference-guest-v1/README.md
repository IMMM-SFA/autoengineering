# Candidate guest inference transport verification

The first regression passed 30 tests. The later execution/input/composite/cost
regression passed 83 tests in 114.03 seconds. The final cold-decoding/input regression
passed 47 tests in 6.51 seconds. These cover metadata relocation, source/runtime
mismatches, unqualified-profile refusal, old wheel refusal, cold parsing without
runtime/data access, legacy job bytes and v1 execution/recovery/physical checks.

Guest tests use explicitly authored Linux observations and code-layout fixtures.
They stop before selected-model/driver reads in relocation tests. They execute no
Linux image or guest model, qualify no memory/privacy boundary and supply no real
container identity. The fixture's training belongs to ordinary authored v1 setup.
The default host cannot impersonate Linux x86-64 identity.

V1 jobs retain their serialized fields and path/interpreter binding. V2 jobs pin
the environment/wheel/code, image, interpreter/build and proposed limits, with a
path-independent scope. Original job/intent/claim hashes still bind the grant,
executor and nonce. The fixed worker validates runtime and source bindings before
selected-state/model/driver reads. Legacy supervisor archives refuse guest jobs;
a qualified guest owner/receipt chain remains separate work.

A fresh wheel built from 342 copied inputs contains 212 core Python files with
exact source parity. Offline preparation/reconstruction produced a successor input
package with 302 wheel source hashes and unchanged archive pins. The original input
package also still verifies. No acquisition, extraction or execution was permitted
in those preparation calls. A wheel build is not image or runtime qualification.

See [input lineage](prepared-inputs.json),
[successor package](../prepared-inference-environment-v2/README.md) and
[implementation increment](../../../docs/implementation-plans/part-5-frozen-prediction-increment.md).
