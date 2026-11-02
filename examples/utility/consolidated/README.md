# Consolidated execution preparation

Real CAMELS, solar and wind inputs are staged under the ignored owner-private
`outputs/consolidated-execution-v1/` directory. No confirmation model was run.
The [readiness record](execution-readiness.json) distinguishes completed source
and baseline work from the incomplete live-agent suite integration.

Completed:

- CAMELS development and confirmation partitions, using the verified archive,
  published dates, A-only flow mask and causal initialization.
- All 365 PVDAQ 1278 daily objects from 2013: 35,058 rows, including 14,942
  eligible daytime samples. The 2011 development files were independently
  hash-checked and staged for fitting and selection.
- WIND Toolkit reserve years 2012-2014 and development years 2008-2011. The
  existing verified 2007 development point remains the fitting-period input.
  The intermediate reserve binary is interleaved speed/direction. The existing
  annual custody service uses concatenated arrays, so sealing must reconstruct
  its drivers from the retained NPZ files rather than copying this binary.
- Four numeric development references and absolute gain margins in
  [baseline-references.json](baseline-references.json). CAMELS required one new
  baseline evaluation. Other reference receipts were retained. The CAMELS
  development volume bias is 23.1 percent and exceeds the unchanged 10 percent
  secondary limit; it is not presented as a feasible baseline.
- Executable scientific selection functions for all four domains, the new solar
  normalization/scoring interface, and a shared host/science selection supervisor.
  It reserves complete timeouts before launch, charges uncertain attempts and
  refuses automatic retries. Its 600-second allowance covers both kinds of work.
- Common post-selection engineering scoring for either selection regime, with
  original-result recovery. Like wind, its 60-second confirmation allowance is
  a reservation, not an enforced OS deadline or an end-to-end cost claim.
- One read-only scientific source snapshot: 361 file hashes verified. Its capture
  script contains the executed pre-cleanup version with an unused local variable;
  the later lint-only cleanup does not alter the captured scientific kernels.

The final targeted checks passed 25 tests, with no skips. The process test needs
`ps` and passed outside the filesystem sandbox. Solar's actual development score
matched the prior reference. Wind's actual 2010 and 2011 baseline runs produced
31.3974506977 and 27.5665947208 GWh. These are development results, not confirmation.
There were four new development model starts and zero confirmation starts.

## Blocking condition and remaining work

The saved host configuration is
`outputs/campaign-part3-proposal-context-20261027/prepared-study/host.toml`.
Its required `qualification.json` is absent from the referenced qualification
root. Native host verification fails before credentials are read or a provider
is contacted. No newer native host qualification manifest was found in the
inspected worktree output/evidence inventories. A path to current evidence was
requested from the user.

Scientific entry points are not a live-agent suite coordinator. The final
72-cell and 18-cell manifests and protected worker/scorer registrations remain
incomplete, including the hydrology and solar confirmation adapters. After the
host identity is resolved, finish those registrations and create exactly one
new engineering scenario draw under the resulting suite identity. Seal all
staged inputs to that identity, preserving the original source receipts.

Do not substitute a scripted/fake host, generate a provisional engineering draw,
score reserves, loosen the CAMELS bias limit, or restart the historical control
matrix to make this preparation look complete. This is an explicit incomplete
execution handoff, not an admitted study or a claim that all requested tasks are
finished.
