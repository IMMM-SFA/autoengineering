# Offline inference environment input verification

The package was prepared from the existing Linux x86-64 default lock and preserved
pure wheel, with acquisition, process and extraction hooks denied. It contains
49 archive pins, 265,399,717 compressed bytes and 300 wheel Python-source hashes.
No archive bytes were fetched or installed. Its image identity is absent and both
execution authority and runtime qualification remain false.

The final combined regression passed 46 tests: 27 preparer cases and 19 documentation
cases. Strict lock/wheel validation, corruption, symlink parents, publication loss,
no overwrite and reconstructed metadata are covered. A fresh guarded reader also
verifies the actual prepared package. The first nested-directory import failure
and corrected reader are retained. The source lock's selection is used without
another solve or independent version-constraint recheck.

The original producer bytes are in preparer-source.py.txt and match the manifest's
preparer digest. Later strict JSON type checks are recorded in
current-reader-source.py.txt. That reader successfully verifies the original input
package and does not rewrite its manifest or review. Source snapshots here are
historical data; use the reviewed source module for actual preparation.

The v1 worker remains host interpreter/workspace bound. Guest transport, base-image
identity, environment assembly and actual privacy/resource controls remain open.
Candidate limits are proposals. The preceding full default checkpoint does not
cover this added preparer/test file; it retains its original scope.

See [summary](summary.json), [prepared package](../prepared-inference-environment-v1/README.md)
and [implementation increment](../../../docs/implementation-plans/part-5-frozen-prediction-increment.md).
