# Candidate guest composite confirmation

The separate v2 registration/service binds original guest facade, inference runtime,
publisher and policy to the existing fixed vector scorer. Vector and local composite
services/scorers refuse the guest path before reservation/access. The parent grant
continues to reserve two scientific starts. Original inference and its completed
initialization precede a create-only transition to the prediction-specific inner
grant. No inner score can start on failed inference or after stage cancellation.

Original receipt/transition verification supports both local/v1 and guest/v2 paths
without changing v1 serialization. Recovery can finish original inference/handoff
publication but cannot start an inner score that did not complete. A reconstructed
service with a recovery-only facade can recover a saved score without live inference
scopes or label files. That facade cannot execute.

Guest accounting records separate inference/scoring container counts and their
total. Success has one reported container in each stage and two total. Failed
inference has no scoring container. Incomplete successful handoff retains unknown
scoring/total counts and durations. Versioned registration selects this behavior;
legacy supervisor fields cannot silently change local container accounting.
Callback time contains both stages and must not be added to overlapping stage time.

The first 9 guest cases passed in 60.89 seconds. Their authored scoring fixture
reported two fork/thread warnings because its HTTP peer threads were still live.
The completed inference peer is now closed before the fixed local score worker
exercises fork. No production worker/runtime allowlist was changed. The related
guest/local composite, receipt, cost and grant regression passed 60 cases in 166.67
seconds. All 15 final guest-composite cases passed in 110.60 seconds. Source snapshots,
pins, logs and XML retain these scopes. Full default tests were not rerun.

Tests exercise original parent identity, subordinate grant, both container counts,
failed inference, missing inner result, original-score recovery, cancelled handoff
with zero label reads, changed runtime before access and corrupt initialization.
All guest daemon state/results and container proof fields remain authored. The
existing fixed stdlib vector worker actually runs in the authored local fixture.
No actual container, image, guest model or independent labels are used. These tests
do not establish OCI privacy, physical inference or independent scientific utility.

Replay the retained public-only suite with:

```sh
.pixi/envs/default/bin/python \
  examples/utility/verification-guest-composite-v1/replay-public.py.txt
```

The fresh reader reproduces the original score, nested receipt, transition and both
container costs. It denies model imports, process/socket creation, array loading,
clocks, publisher source probes, writes and private/unrelated reads during validation.
Public metadata-reader code is initialized before the strict file-read barrier.
No live scorer/facade instance, original drivers, owner workspace or labels are needed.

Current core count remains 223 with changed registration/orchestration/accounting
sources. Earlier checkpoints and prepared environment v3 retain their original
scopes. No default CLI/scorer activates the guest profile. Early unstarted resource
cleanup, strict filesystem timing and actual runtime/privacy, installed/platform/
host qualification remain open. Independent task partitions, useful gains/tolerances
and scientific comparison remain open. Part 5 is incomplete.
