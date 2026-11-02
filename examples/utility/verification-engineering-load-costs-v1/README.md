# Installed engineering work-cost reader

The offline reader converts a caller-pinned engineering work receipt into the
existing immutable `CostRecord` format. It joins those records with the generic
confirmation costs without reopening private sources or running a model.

The reader verifies the original suite barrier, charged grant, selected model
and current, sealed source binding, scoring policy, callback identity and public
work hash. Completed score receipts must agree with that work. The caller supplies
a frozen `ArtifactRef`; the reader never scans for a substitute or refreshes its
hash. Changed or missing supplied proof is an error. Omitting proof keeps actual
work unknown, even after a successful score.

The [exported records](expected-costs.json) reproduce the preceding native
callback: 24 completed evaluations, 395 nonlinear iterations, 6,440 component
calls and 1,975 component `_linearize` calls. That last counter includes Newton
linearization and is not a count of `compute_totals` calls or FLOPs. No new native
model, private source read, provider call or dependency installation ran here.

Reservations, case attempts, completed evaluations and model starts are separate
resources. An interrupted case leaves total starts and inner work unknown.
Completed counters remain explicit lower bounds. Do not add reservations or
known-completed subsets to full totals. Stable physical receipt IDs reject a
second charge when proof arrives later or a score commit is interrupted. A durable
work receipt can retain completed costs without publishing or recovering a score.

[Installed evidence](installed-reader-result.json) used a copied-input wheel with
224 core and nine example Python sources. Every package payload matched its input
pin and installed bytes. The existing setuptools backend built once. Pip installed
once into an isolated target using `--no-index --no-deps --no-compile`. The copied
reader, expected evidence, inputs and working directory were outside the checkout.
All project module origins resolved to the installation target. Dependencies were
inherited from the local macOS development environment.

After metadata initialization, an active Python guard denied new imports, writes,
process creation, network access, clocks and reads outside the public input scope.
Private source, entropy and native lifecycle callbacks were disabled. Repeated
reading changed no suite event. Duplicate work, omitted proof and a modified
installed input were checked. This guard is not private-runtime or OS qualification.

The first preparation omitted the example namespace from its import path. Its
[record](initial-refusal.json) preserves that error and the dependent input-copy
failure after a successful build/install. A corrected metadata preparation copied
verified evidence into the existing installation. A later relative-path invocation
stopped before launching the reader. The successful check used absolute paths,
then ran with the reader and expected evidence also copied outside the checkout.
No rebuild, reinstall or scientific retry was used to correct these path errors.

The [summary](summary.json) records 172 verified related cases and 19 documentation
checks. The first related run passed 151 cases and was refused at `ps` in 21
supervision cases. Exactly those 21 passed with process inspection available in a
new fixture scope. The original 21 trampolines never opened their executable
gates and a separate observation found none alive. Their original receipts were
not rewritten. Twenty-two new cost-reader cases passed. The
[CSV table](confirmation-costs.csv) exports the joined records with unknowns blank.

The
reader is an application-level supplement to generic cost records. Automatic
common-report ingestion, CPU/RSS, human/setup costs and complete cost accounting
remain open. The full installed workflow, Linux, protected execution, task/gain
admission and independent Part 5 comparison remain unqualified. The original
native evidence and frozen 315-source guest package are unchanged.
