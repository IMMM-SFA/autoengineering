# Candidate guest image preparation

This package contains a source-matched wheel, the existing locked Linux input
metadata, and an unexecuted image recipe. It contains no acquired dependency
archives or image layers. No installer or image has run.

Image plan digest: `f9b1782fb389a6e7d262de44089c5cafb3bde1fb4852ffa36c0e1b57fbb252d3`.
The environment-input digest is
`7c66ecada3955ad940d07fcf409b7f78bf68fc643950340f408d9d398a6fa06e`.
The image uses the immutable Linux amd64 manifest for Python 3.12 on Debian
Bookworm, with micromamba 2.9.0 pinned by archive hash. The target environment's
Python remains 3.12.13 from the existing lock. The base interpreter is only a build
tool. The planned pip command selects the target interpreter explicitly.

The plan names 49 locked archives, one installer archive and one local wheel.
Remote compressed payloads total 317,657,548 bytes, plus a 1,048,576-byte registry
metadata allowance. The local wheel is not a download. These are byte bounds for
one acquisition attempt, not measured unpacked size. The proposed build allowance
is one attempt, 1,200 seconds and 8 GiB of disk. No current code enforces those
build limits, so they cannot yet support a qualified execution request.

## Recipe and remaining execution work

`plan.json` identifies each recipe artifact. The Dockerfile checks payload hashes,
extracts only the installer executable, assembles the explicit local package list,
and uses the base image's pip to install the wheel into `/opt/inference` without
index access or dependency resolution. It imports core packages, removes build
inputs and selects user 1000:1000. The final command remains the fixed stdin
bootstrap. The recipe does not expand the inference/scorer command allowlists.

The plan requires Linux amd64 and disabled network for build RUN steps. That setting
does not itself prevent a builder from resolving or pulling a missing base image.
A future runner must verify the exact cached base image and bound all acquisition
before build. A verified context materializer and bounded build runner are still
missing. The recipe artifacts are not a ready Docker build context.

`qualification-proposal.json` enumerates 26 proposed cases, with at most
20 creations and 15
start intents. Every case is `not_attempted`, with actual-daemon handlers missing.
All inputs/canaries must be authored. The six resource/privacy probes require a
separate fixed diagnostic command profile. They cannot use the scientific launch
policy to execute arbitrary code. Scoring, fitting, providers and independent
labels have zero allowances in this proposal. Complete composite/private-scorer
qualification remains separate. The proposal grants no execution authority.

## Verification

The preparation helper refuses mismatched source bytes, missing/new core files,
symlinks and existing output. The verifier reads only the saved package and an
explicit plan pin. `acquisition_authorized`, `build_authorized`, `starts_authorized`
and `runtime_qualified` remain false. The prepared environment and wheel contain
all 224 current core Python files and 315 declared wheel Python sources.

See [verification evidence](../verification-guest-image-preparation-v1/README.md).
The whole Part 5 goal remains incomplete.

## Metadata sources

The [official Python image metadata](https://raw.githubusercontent.com/docker-library/repo-info/master/repos/python/remote/3.12-slim-bookworm.md) supplies the
platform manifest, image ID and compressed-layer size. The
[conda-forge release metadata](https://api.anaconda.org/release/conda-forge/micromamba/2.9.0) supplies the
installer filename, hash, size and license metadata. These were checked with
bounded public metadata requests, without fetching archives or layers.
[The pip documentation](https://pip.pypa.io/en/stable/topics/python-option/)
describes selecting a different interpreter, including one without pip installed.
These sources describe inputs and intended behavior, not a successful image build.
