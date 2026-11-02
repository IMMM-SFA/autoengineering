# Consumed first diagnostic request

Request `0a99d30a1f5df56c3a10fa099ec23a92f66cbce4c6a646c9267fef01d1669206`
created one unstarted container and refused its inherited image environment.
The original cleanup also refused. A separate administrative removal verified
that exact unstarted container and recorded absence. There were zero starts.

This request cannot resume or retry. Its original source hashes, failed metadata
and separately identified cleanup remain preserved. See the
[resource evidence](../verification-guest-resources-v1/README.md).
