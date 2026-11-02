# Separate administrative-tools wheel

A fresh copied-input wheel includes all 224 core Python files and 318 packaged
Python sources from 359 pinned build inputs. Its SHA-256 is
`55fc3857513cb4a7155fc058fe18fac0f3de469ccb7f820264469404cbbcfc9b`.
It includes the context materializer, archive downloader and local image-build
helper that were outside the preceding guest wheel. This wheel does not replace
the frozen runtime wheel, environment package, real context or build request.

Five fresh isolated interpreters loaded CLI modules from the extracted wheel and
passed help checks outside the checkout. A sixth interpreter replayed the 50 real
archive files, real context and one authored build-completion sample using only
relocated saved bytes after code initialization. Processes, sockets, clocks, array
loading, model imports, source probes, writes and file reads outside the relocated
data scope were denied. The source package directory was also outside that scope.
Dependencies remain inherited from the existing base interpreter environment.
This is extracted-wheel evidence, not a package installation or Linux qualification.

`authored-build-metadata.tar.gz` contains stubbed Docker metadata and no real image
execution. `fixture-summary.json` makes that distinction explicit. The real cache
and context are copied temporarily for verification and remain local ignored
outputs. No downloaded binary, Docker daemon, installer or image was executed.

The first guarded replay refused the safely extracted fixture's directory modes.
The corrected harness restores private modes after safe tar extraction. Initial
logs remain as `*-before-private-modes.log`. All 359 build inputs remain unchanged.
The frozen build request `066de0ca...` is unchanged and its work directory absent.
Image preparation still awaits the requested separate approval. Current installed,
platform/host, runtime/privacy and independent confirmation requirements remain open.
