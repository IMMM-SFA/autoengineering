# Native wind callback evidence

The [native review](../../../docs/reviews/part-5-wind-annual-native.md) records
one three-year control using authored constant drivers and authored selection
evidence. It made exactly three native PyWake evaluations and three private
payload reads, then recovered a prespecified suite score-commit failure without
more source or model work. This is not independent confirmation or a utility gain.

- [Predeclared request](native-request.json)
- [Native result](native-result.json)
- [Recovered receipt](native-receipt.json)
- [Native JUnit](native-tests.xml)
- [Source and regression summary](summary.json)
- [Metadata-only reader](read.py.txt)

`suite/` retains the public suite/selection/access/work records and declared code
sources. `public-source/` contains identity metadata. `callback-work/` contains
the original callback pin. No private `.f64le` driver or private kernel journal
is included. The reader supplies an empty private placeholder in its owned
temporary metadata copy. Runtime lock files are
excluded from the manifest, while `pixi.lock` remains part of the model closure.

The native run emitted a possible NumPy binary-compatibility warning. The saved
import-only traces reproduce it in the installed netCDF4 extension through
PyWake. The earliest import probes did not expose it because NumPy installs an
ignore filter. The later probe applies the error filter after NumPy import.
Those diagnostics made no model calls and changed no installation. Retain this
dependency limitation when interpreting the passing native control.

The first temporary-copy replay failed because macOS returned its `/var`
temporary-directory alias. The reader now resolves its owned temporary path.
The store's symlink checks remain unchanged. The initial failure is preserved in
[its record](reader-initial-failure.json). Relocated replay then passed and a
rehashed modified work artifact was rejected.

Run the reader from the checkout with its trusted source root:

```sh
.pixi/envs/default/bin/python -I -B examples/utility/verification-wind-annual-native-v1/read.py.txt --source-root "$PWD"
```

The reader needs base dependencies and the matching example code, but refuses
optional model imports. It copies verified metadata into an owner-private
temporary scope so a public archive needs no writable journal or private directory.
It verifies hashes and the original work pin, then joins
callback and suite recovery without private inputs. It does not execute models,
check the actual OS boundary or qualify an installed wheel. The verification
summary separately records relocation and altered-artifact checks.

The native test requires the wind environment and test harness. It is a controlled
verification, not a standalone bundled scientific example. Do not rerun it as a
reader. Its source and exact test command are recorded in the summary.
