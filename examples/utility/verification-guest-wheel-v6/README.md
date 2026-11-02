# Successor guest wheel and offline build context

The successor wheel contains all 225 current core Python sources and the same 91
example Python sources declared by v5. All 316 Python payloads match their declared
workspace source bytes. The three modified report modules and added core cost
reader are included. This restores source alignment for a future guest image.
It does not transfer the old image's qualification to current source.

[Prepared inputs](prepared-inputs.json) bind the wheel, unchanged lock and the same
49 runtime archives. The old v5 input package still verifies against its original
digest. No runtime archive acquisition or dependency installation ran.

The first preflight refused package data that differed from the previous wheel.
Its [record](initial-preflight-refusal.json) and unused staging scope remain.
The successor builds in a separate scope and deliberately preserves every non-code
package payload from the verified v5 wheel. The README and four task dossiers
therefore remain historical bundled metadata. The
[data origin map](package-data-origins.json) and
[workspace differences](package-data-deltas.json) make this explicit. Consult the
current [task dossiers](../tasks) for current readiness. All four bundled dossiers
still say `blocked_draft`; this packaging step admits no task or partition.

Every package payload matches its staged input pin. A separate local installation
used `--no-index --no-deps --no-compile` and inherited macOS dependencies. The
[guarded report check](installed-reader-result.json) reconstructs current JSON,
Markdown and verification output with example/framework imports denied. Its
`installed_core_only` field describes imported modules; the wheel itself includes
91 example Python files. No model, private source or provider was invoked.

The [image recipe and materialized context](context-result.json) use the existing
verified runtime archive cache. The 67-file context copies 275,254,359 bytes.
A [fresh guarded reader](cold-context-result.json) verified a relocated copy with
original source/cache reads, new imports, writes, processes, network and clocks
denied. A changed wheel payload was rejected. The original context remains valid;
the altered diagnostic copy is preserved separately.

The [prepared local build request](build-request-result.json) binds the current
context, Docker CLI/plugin/socket metadata and cached base manifest. It permits
at most one base pull and one build with a 1,200-second client deadline and no
automatic retries. No Docker command was dispatched. Actual image assembly, the
explicit-environment derivative and current-image controls remain required.
The request reserves zero scientific starts, provider calls or private accesses.

The full default regression is still running under its
[pinned launch](../verification-current-base-v6/launch.json). Core and test sources
were left unchanged during this increment. Image dispatch is deferred while that
run remains active. Image/runtime/privacy, Linux and real independent host
qualification, complete cost accounting and the real four-task study remain open.
See [summary.json](summary.json) for the verification at this checkpoint.
