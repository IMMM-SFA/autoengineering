# Exact engineering source binding

A caller-pinned source-binding artifact now fixes the generated source's actual
public manifest, private payload, seed commitment, original claim, policy and code
identities. Sealing refuses any prior selection activity. Reads never refresh the
artifact hash from disk. The task's prospective partition policy remains separate
from the actual sealed source commitment.

The existing confirmation grant schema is unchanged. The new helper derives its
scorer identity from the declared scorer-code digest plus the sealed binding.
The trusted reader checks that identity, the exact task and complete barrier,
then the active charged confirmation attempt and committed access receipt.
It records a once-only source-read intent before opening private bytes. A completed
score replays through the existing service without reopening the source. An uncertain
source read remains charged and cannot retry through the helper or service.

Eleven new tests cover successful service composition, actual access ordering,
changed source/code/ref identities, sealing after selection, unknown source access,
failed private reads and saved-score replay. The active-access test changes the
public manifest after sealing and confirms refusal before private reading while
retaining the original confirmation charge. The full related regression passed
75 tests. The existing selection fixture gains an optional preparation hook with
its default behavior unchanged.

The executed control used the existing authored selected-model fixture and a fresh
source draw. It sealed source metadata before the fixture's selection work, then
completed one callback through the unmodified confirmation service. The callback
returned a declared constant fixture score. Its base scorer-code identifier is an
authored stand-in, not a qualified native scorer code closure. No coupled-model
outputs or solver work were produced. One confirmation start remains charged;
source reading happened once and saved replay performed neither reading nor scoring.
These are mechanism checks, not real scientific confirmation.

Only public metadata, bindings, child evidence, source-read intent and score receipts
are archived. The seed and scenario rows remain in local outputs. The guarded cold
reader verifies public file hashes, the exact binding and derived scorer identity,
full suite/child/selection evidence, the source-read claim and saved receipt. It
starts no model, process, scorer, network or entropy request and opens no private
source. Its initial attempts refused missing metadata-module initialization. The
final checker initializes BatchSpec/BatchStore and baseline-selection helpers before
its first guarded reconstruction.

The source-binding artifact must remain part of the final trusted registration and
execution source closure. The callback remains application-owned. This module does
not activate a CLI scorer, qualify an OS boundary, admit a task, replace physical
checks or establish complete inner-work accounting. A real coupled-model scorer,
qualified protected runtime, development-reference gains, final budgets and the
full matched independent study remain required. All task dossiers remain blocked
and the original grid proposal is unchanged and unevaluated. Part 5 is incomplete.
