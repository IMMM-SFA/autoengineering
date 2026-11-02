# Fixed container scorer integration

The new programmatic ContainerRMSEScorer connects frozen prediction artifacts to
the existing ConfirmationService. It has no CLI or registry activation and remains
an unqualified candidate. It runs no supplied model code. Independent-data
admission and the complete new-runtime failure matrix remain outstanding.

Construction binds artifact metadata, outcome, package source, pinned image,
explicit local Unix endpoint and server fingerprint. It opens neither labels nor
a socket. Before label access, the callback checks the grant, finite public
predictions, partition/selection identities, cached image and daemon fingerprint.
It writes a durable access intent before reading the original private artifact.
The final version also checks staged job and label hashes against that intent
before creating a container. Inputs are limited to one MiB each.

The runtime uses a fixed nonroot command, 64 MiB memory, zero swap, one CPU,
16 PIDs, no network, read-only root and source stage, dropped capabilities,
no-new-privileges and a 4 MiB tmpfs. Its independent owner-pipe watchdog must arm
before start and removes the exact original ID on EOF or deadline. The fixed
trusted scoring child shares a hard 16 KiB stdout/stderr file cap. The callback
requires 64 reserved active seconds for bounded lifecycle/API work. This is not a
claim of a strict whole-host callback deadline or complete cost measurement.

Two distinct synthetic confirmations ran serially, one for the initial source
and one after staged-input binding was added. Both returned RMSE 1.0 and committed
public receipts. Both original containers were removed and their absence checked
through HTTP 404. These are separate development controls, not a retry of an
uncertain attempt or independent scientific repetitions. No real confirmation
data, provider call, image pull or remote job was used.

For each version, the source label file opened once after suite reservation and
access intent. After completion, all three synthetic label copies were deleted.
The scorer recovered from the original completed runtime evidence with daemon
requests forbidden. ConfirmationService replay reused the committed public
receipt without rescoring. Runtime recovery checks original IDs, nonce, command,
source bytes, input metadata, stop/cleanup evidence and bounded original output.
It reads public job/source metadata, never original labels or staged label bytes.
Missing or inconsistent evidence refuses recovery. Uncertain attempts stay charged.

Original and hardened source snapshots and raw executions are preserved separately.
The initial harness had a syntax error before any statement executed. After that
was corrected, its scoring and cleanup succeeded, but its later synthetic-label
deletion check failed on the intentionally read-only stage directory. Only offline
postchecks resumed against that same completed result after changing the owned
directory mode for deletion. The second harness incorporated this postcheck fix.
Neither issue launched a replacement for the original scoring attempt. Raw harness
bytes are stored as text artifacts, separate from maintained executable source.

The initial unit fixture also omitted its required artifacts directory. Seven
fixture setup failures occurred before scoring and were corrected. Their record
is retained. Final checks and installed-wheel evidence are recorded alongside this
file. Earlier broad base/Bayes checkpoints retain their original source scope.

The offline wheel matched all 198 core Python files. From a relocated execution
copy, its scorer recovered RMSE 1.0 while socket calls, process/fork starts,
original-root opens and original-label access were forbidden. Archived Python was
checked as data; only the installed package supplied executable recovery code.
The raw execution manifests anchor the saved files. The installed check does not
establish current live absence or independently prove daemon assertions.

Remaining work includes the complete failure matrix for this new runtime source,
explicit suite-level publication of a scorer-recovered pending confirmation,
container-specific public cost evidence, and independent task custody, useful-gain
thresholds and a frozen authorized protocol. The current service safely refuses
automatic retry of pending attempts. It does not yet expose the explicit recovery
publication path. This integration does not qualify private scoring, Linux x86-64,
independent hardware, scientific utility or complete total costs.

The final runtime/scorer/output/confirmation/cost/archive/documentation suite
passed 161 tests in 11.85 seconds. Ruff passed. The earlier 158-test checkpoint
is retained separately. These are focused software checks, not a fresh full
base/Bayes suite or a scientific comparison.
