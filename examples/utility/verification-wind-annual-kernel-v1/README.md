# Annual wind kernel verification

The [kernel review](../../../docs/reviews/part-5-wind-annual-kernel.md) describes
the implemented contract and remaining limits. The actual authored parity
control completed two local model starts and no fitting, source acquisition or
container execution. It does not admit a real task or private execution.

[Request](request.json), [saved producer](run.py.txt),
[actual result](actual-result.json), [verification summary](summary.json) and
[JUnit](tests.xml) preserve the exact checkpoint. The source snapshot includes
the kernel, annual records and focused tests. The consumed actual work scope is
`outputs/wind-annual-kernel-authored-v1`; do not rerun the producer as a verifier.
The [metadata-only reader](read.py.txt) verifies archived hashes and receipt joins
without models. It verifies producer metadata, not OS or execution attestation.

```sh
.pixi/envs/default/bin/python -I -S -B -c 'import runpy; runpy.run_path("examples/utility/verification-wind-annual-kernel-v1/read.py.txt", run_name="__main__")'
```

The earlier [annual record checkpoint](../verification-wind-annual-v1/summary.json)
retains its original source bytes. The current annual record adds explicit
`not_attempted` support so a failed kernel can preserve unentered years. No
earlier record or dossier has been rewritten.

The initial model import emitted a Matplotlib cache warning and used a temporary
cache because the default home cache was not writable. Execution then completed.
No installation or global configuration was changed. The wind environment's
Python 3.12.14 and PyWake 2.6.20 were checked before execution. This verifies
only the recorded local environment and authored fixture, not other platforms.
