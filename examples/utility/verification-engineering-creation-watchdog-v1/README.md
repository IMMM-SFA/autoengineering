# Supervision before creation

The owner now arms a watchdog for the original name and immutable configuration
before CREATE. The new prospective plan carries no CID. Once creation is
acknowledged, the owner publishes the CID and waits for the watchdog to verify
ownership and acknowledge that binding before START. Existing plans with a
known CID retain their earlier schema.

Four live controls exercised this protocol. Owner loss before CREATE produced
no container. A container created by the daemon before CID binding was found by
its original name, verified and removed after owner loss. Normal CID binding
and disarm also passed. For an intent-only control, the watchdog retained an
unverified creation rather than treating current absence as proof that the
daemon could not create an object later. That control sent no CREATE, but the
watchdog cannot infer this from the durable intent alone.

Two containers were actually created, none started. Three exact owner PIDs were
killed with SIGKILL. All four watchdog processes exited. The two observed CIDs
were separately confirmed absent. No packet, private source or model result
was involved. The intent-only watcher deliberately reported `absent: false`
despite the test driver's current name lookup returning 404.

The focused suite passed 82 tests and full lint passed. Tests include refusal
to START without the binding acknowledgment, foreign ownership and retained
uncertainty. A standalone stdlib reader joins the saved prospective plans,
bindings, kill intents and outcomes outside the checkout. It rejects promotion
of the uncertain intent to confirmed absence, even with recomputed test pins.
These are producer records, not independent OS attestation.

The [v20 register](../guest-qualification-accounting-v20.json) records 59 container
creations and 44 starts. Its known model-start lower bound remains 105, including
96 coupled evaluations. Older unknown work remains unknown. Core code and the
preceding core-only wheel are unchanged. The full default suite was not rerun.

Arbitrarily delayed daemon creation remains unqualified. Loss during model
computation and the complete resource/interruption matrix remain open. Earlier
scientific controls retain their original helper versions. The current owner
was not rerun on scientific inputs in this increment. Runtime/private admission
and the independent utility study remain false.
