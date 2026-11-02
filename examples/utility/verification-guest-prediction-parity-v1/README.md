# Saved native and guest numerical parity

All seven outputs passed the fixed symmetric tolerance
`abs(native - guest) <= 1e-10 + 1e-12 * max(abs(native), abs(guest))`.
The largest absolute difference was `2.1316282072803006e-14` in reservoir storage.
Both scalar initial states were included. The scoring prediction vector passed
with a largest absolute difference of `7.105427357601002e-15`. Prediction JSON
was not exactly equal. Model, partition and selection metadata were equal.

This separately counted diagnostic reused the completed exposed authored guest
inference and launched one native reference from the same frozen fit, original
seed and drivers. Its original 20-second model timeout was retained. Tolerances
were saved before the native run. No new guest run, fitting or scoring occurred.
The native supervisor reported a verified receipt, exit zero and stopped state.

The request digest is
`10748e82884df3445dc38be969fb9bdad3f4036b6859f93ddba9c7df791d5687`.
The original completion digest is
`d01f44b5195cca2ece81f49d2276e4641e8f9796570c7c72800fedb3eaba9f35`.
`runner.py.txt` preserves the exact producer. The job, result, supervisor report,
output arrays and prediction documents support saved recomputation:

```sh
pixi run python -m examples.utility.guest_parity_reader \
  examples/utility/verification-guest-prediction-parity-v1 \
  --expected-digest d01f44b5195cca2ece81f49d2276e4641e8f9796570c7c72800fedb3eaba9f35
```

The reader verifies saved producer records and recomputes numerical comparisons.
It does not attest the operating system or independently reimplement the physics.
This is platform/transport parity over known exposed inputs, not independent
predictive evidence, private runtime admission or the complete 26-case matrix.
