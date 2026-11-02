# Watchdog loss controls

The coupled owner now checks its watchdog before dispatch, during bounded
input/output transfer and process-exit waiting, and after client completion.
Supervisor exit revokes result authority and records the exact PID/exit status.
The owner still cleans the original container. A valid worker response cannot
be published after the supervisor has exited.

Two actual controls killed the exact recorded watchdog PID with SIGKILL while
the owner remained alive. One container was ready but unstarted. The other was
observed running before any input was sent. Both owners detected the loss,
refused result authority, removed the original containers and rejected normal
watchdog completion. The producer separately confirmed exact-CID and watchdog
PID absence. No packet or private source was submitted. No model result was
observed. Unknown work is not replaced with zero.

The focused suite passed 77 tests and full lint passed. Tests cover transport
monitoring, refusal after valid output, ownership checks, source/cost contracts
and watchdog EOF/deadline handling. Core code, frozen images and the preceding
core-only wheel are unchanged. The full default suite was not rerun.

The public evidence includes original plans, readiness, kill intent, loss,
refusal and cleanup records. A standalone stdlib reader joins those receipts
outside the checkout and rejects altered result authority even with recomputed
test file pins. These are producer records, not independent OS attestation.

The [v18 register](../guest-qualification-accounting-v18.json) records 56 container
creations and 43 starts. The known model-start lower bound remains 81, including
72 coupled evaluations. Earlier unknown work remains unknown.

Loss during actual model computation, pre-acknowledgment creation loss and the
complete resource/interruption matrix remain unverified. Earlier owner-loss and
scientific controls retain their original helper versions. This increment does
not repeat their scientific runs or transfer full qualification. Runtime/private
admission and the independent utility study remain open.
