# Valid undercoverage iteration

This directory preserves the final Item 8 evidence executed from signed revision `b287c82` with
the independent posterior propagation correction in decision 0005. The run is scientifically
valid. It is not an invalidated execution.

The raw audit, replay, scope, regret, fallback, and constraint Brier criteria pass. Pooled 90
percent objective interval coverage is 0.65625, below the frozen minimum of 0.75. The result kept
the full-network backend experimental and stopped work before Item 9.

Verify exact reconstruction from a clean checkout of the recorded execution revision:

```console
pixi run -e bayes benchmark-full-network \
  --output benchmarks/full_network/iterations/b287c82-undercoverage
```

The command reconstructs every derived artifact from `raw-records.jsonl`, confirms the decision
and source hashes, reports `FAIL`, and exits 1 because the coverage criterion fails. A later source
revision will reject the directory's recorded source hash. That rejection protects the evidence
binding and does not invalidate this iteration.
