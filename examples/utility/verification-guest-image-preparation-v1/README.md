# Offline guest image preparation evidence

The new preparer saves a source-matched image recipe without acquiring or executing
packages or images. The [prepared package](../prepared-guest-image-v1/README.md)
contains input pins, recipe references, transfer/build proposals and explicit
remaining prerequisites. Its plan digest is
`f9b1782fb389a6e7d262de44089c5cafb3bde1fb4852ffa36c0e1b57fbb252d3`.

Image/environment tests: 39 passed in 1.11 seconds. The fresh copied-input wheel
contains 224 core files and 315 Python sources, with 356 input hashes. All four
previous environment packages still verify. The example README was updated after
the build. Other captured inputs, including all Python sources, remain unchanged.

`replay-plan.py.txt` extracts the wheel outside the checkout and starts one fresh
isolated reader. `cold-plan.py.txt` verifies relocated saved bytes with processes,
sockets, arrays, clocks, source probes, writes and unrelated reads denied.
No actual installation, image build, daemon, container or independent data ran.

`metadata-evidence.json` records hashes of bounded official public metadata
responses and the factual selected base/installer fields. The 26-case runtime
proposal remains unrun. A context materializer, bounded acquisition/build runner,
actual-daemon handlers and separate diagnostic profiles remain required. The
full default suite was not rerun. Part 5 remains incomplete.
