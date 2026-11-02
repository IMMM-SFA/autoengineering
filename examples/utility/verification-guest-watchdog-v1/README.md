# Candidate independent guest watchdog

The watchdog uses one detached local child, an anonymous owner pipe and the
original monotonic deadline. Original CID/image/labels authorize cleanup. Pinned
daemon identity must still match. Resource drift does not prevent owned cleanup.
Kill and forced removal each have durable intent and are never automatically
repeated. Lost responses require observation. Explicit stop and absence evidence
remain distinct. A completed outcome replays without contacting the daemon.

The 340-case related regression passed in 160.83 seconds. It includes the first
14 watchdog cases plus the daemon, owner, observation, input, attach, bootstrap and
receipt suites. The final watchdog check adds positive parent disarm, unknown
creation-response refusal and prevention of guard replacement. It passed 17 cases in 34.79 seconds. Its log/XML record
the final result. The core watchdog bytes stayed unchanged between these checks.
The original regression test snapshot and source pins are retained separately
from the expanded final test source.

Native fixtures use owned Unix HTTP peers with authored container state. They
exercise actual child readiness, owner EOF, cancellation, deadline and invalid
disarm. Another actual owner subprocess is killed with SIGKILL. Its detached guard
survives, observes EOF, records stop and absence, and terminates. No actual Docker,
container, image or guest model runs. These fixtures do not establish OS privacy,
container termination, scientific utility, installed-package or platform admission.

`authored-owner-loss.tar.gz` retains that original owner's saved evidence.
`expected-outcome.json` records its original outcome. Run the cold reader with:

```sh
.pixi/envs/default/bin/python \
  examples/utility/verification-guest-watchdog-v1/replay-owner-loss.py.txt
```

The reader relocates the archive and disables process/socket creation and new
monotonic clocks before verification. It reads no original suite, drivers or
labels. The retained archive has authored fixture records and private test paths;
it is not independent scientific evidence. The successful output is saved in
`relocated-replay.log`.

Start/attach integration, parent journal reconciliation, initialization recovery,
actual pinned daemon/image/resource/privacy qualification, the independent task
partitions, useful gains/tolerances and the scientific matrix remain open.
