# Durable Anthropic exchange evidence

Status: verified development increment. No production host/profile admission,
provider call, real credential, scientific run or independent access is claimed.

## Contract

`AnthropicExchange` reuses the durable reservation/recovery protocol while binding
a distinct response policy, exact role envelope and frozen output-token cap. The
original Responses exchange keeps its fields and artifact names. The new exchange
stores complete upstream JSON as upstream-response.json. It rebuilds the outbound
Messages request from the approved prompt/model/schema/cap. Native system text,
account/cache metadata, history, tools and headers do not become provider input.

One dispatch intent is committed before a trusted callback can run. Repeated exact
requests replay saved evidence. Conflicting requests fail. Missing or uncertain
outcomes cannot acquire a new callback allowance. A complete response must have the
reported requested model, end_turn, text-only content and a valid role envelope.
Only then does the application generate a fresh native StructuredOutput stream.
The provider cannot inject a native tool event. Inner role/grant/scientific checks
remain the controller's responsibility.

`usage-observation.json` preserves bounded reported model/token categories even if
the handoff is rejected. It binds the raw response digest, keeps missing/invalid
categories unknown and never infers billing or remote stop. The accepted response's
usage and native CLI counters remain separate. Overflow/transport failures keep
conservative unknown outcomes. A trusted upstream still needs its own network,
credential, process and deadline qualification.

`AnthropicEndpoint` uses the existing absolute request deadline, byte/connection
caps and separate local stop states. It accepts the pinned native Messages route
and a scoped local helper capability. Duplicate/conflicting authentication headers,
wrong routes and mismatched exchange protocols fail before dispatch. Native headers
are neither retained nor forwarded. The probe uses a fixed authored capability,
not a provider key or a production credential interface.

## Checks

The combined final-source run passed 222 tests across the new exchange/endpoint,
legacy Responses boundary/endpoint, Claude primitive, records, scheduler and
brokered host. Earlier logs preserve a test race: the test inspected active atomic
event writes. Moving that assertion after endpoint shutdown fixed the test. The
product event writer was unchanged. All 95 then-current endpoint contracts passed.
Later usage preservation and adversarial tests are included in the final 222.

Two final v2 probes ran actual Claude Code 2.1.310 through the durable endpoint and
an authored in-process JSON callback. Both completed with structured output and
verified native/endpoint stops. Each recorded two HTTP connection attempts, one
accepted exchange and one authored callback. Completed recovery added no callback
and reproduced the original native process/result. No external upstream exists.
Source identity: b595972dc5e2e20320bb5b4b1c960c42b3dc7d98cd7ea8c103308e30dc83ced8.

The missing-cache case demonstrates the accounting distinction: broker cache
categories, input total and total tokens remain unknown. The SDK reports zero
cache counts and a complete 17-token total. The complete authored case has 22
normalized tokens. All token/dollar fields in these probes are fixture data,
not measured provider work. Future host/cost joins must use broker evidence and
must not fill its gaps from native SDK counters.

archives.json pins regular-file-only copies of v1 and final v2 roots. The v1 roots
precede the usage-observation source and cannot be relabelled as current evidence.
Original absolute paths in native records are provenance. final-source contains
the checked source/test/probe bytes. Primary documentation and its API-reference
access limit are recorded separately.

## Remaining work

A real upstream adapter, API/subscription choice, full credential/runtime/privacy/
resource qualification, truthful Host records/admission, scheduler/factory/cost
integration and actual authorized LLM conformance remain open. The helper key in
this probe is an authored local fixture. These checks do not implement a real
credential lease or prove provider billing/stop. Earlier full-suite results retain
their source scope. The fresh default suite passed 2016 tests with 106 optional skips in 2145.54
seconds. All 364 frozen source/test files were unchanged. Lint passed. The earlier
Bayes result retains its preceding source scope.
The full Part 5 data/custody/scorer/platform/protocol/analysis gates remain open.

## Installed and process checks

A fresh wheel matched all 184 current core Python files. Installed exchange tests
passed 46 cases with original opens and all sockets denied. The HTTP endpoint's
13 cases passed separately with local IPv4 TCP permitted while original opens,
external lookup/connect and subprocesses remained denied. The initial combined
run retained 47 passes and 12 guard-blocked socket tests. These are distinct test
policies. The offline-reader policy was not relaxed.

Guarded installed readers verified every caller-pinned regular file and recovered
complete and missing-cache broker responses unchanged. They also read the saved
broker result from an authored owned-command upstream and six refused/uncertain
cases. Original checkout opens, all sockets and subprocesses were denied. The
Anthropic SDK and optional scientific/model packages were absent. Cached base
paths were reused without editable activation. This is not a minimal solve or
an OS privacy boundary. Readers do not recheck live native state or original
source-worker paths.

The owned-command probe used the existing CommandUpstream with a fixed authored
JSON worker. Native and upstream process stops verified, and saved-byte recovery
added no callback. Its initial driver used the wrong stop enum and marked the
otherwise completed run failed. Both that run and the corrected fresh v2 run are
preserved in command-archives.json with exact staged source. No real upstream,
provider key or network operation existed in the authored worker.

The six refusal fixtures retain their original one-attempt reservations for tool
output, wrong model, missing usage, transport failure, oversized output and loss
after dispatch intent. The v2 fixture explicitly instruments replay and observes
zero callback invocations. The v1 exception-only replay guard was weaker for
reconciliation paths and remains preserved. Failure usage categories stay separate
from successful handoff acceptance, and unknown work never becomes zero.

Default-suite terminal evidence is in default-terminal.json. The shared code stayed
fixed throughout that run. Source copies and inventories preserve the exact scope.
This advances the exchange foundation. Real upstream/profile/host integration,
full runtime/privacy/resource qualification, actual LLM conformance, Linux and all
independent-task/scoring/protocol requirements remain open.

The frozen owned-command worker sources are stored as .py.txt artifacts. Their
bytes match the executed .py files and command-staging-source.json hashes. The
original formatting is retained as evidence. They are not maintained Python
modules or programs to execute during archive inspection. archived-source-map.json
records the path mapping. No production lint rule or source byte was changed.
