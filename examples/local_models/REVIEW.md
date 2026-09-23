# Review and verification

The implementation was reviewed independently in three bounded passes: scientific example
contracts, the discovered parameter-decoder boundary defect, and BMI interoperability. Review
findings were resolved before the final BMI matrix.

Corrections included:

- Attribute final prediction errors to system output, and rank measured solar temperature separately.
- Supply explicit diagnostic references for opportunity ranks.
- Disclose two copper test points outside the training temperature hull.
- Hash system YAML, original water cache inputs, package source and the environment lock.
- Clarify training-label use, model allocation assumptions and copper's unresolved unit multiplier.
- Preserve exact parameter bounds during decoding and retain strict rejection of out-of-range inputs.
- Implement and test BMI indexed access, stable pointers, persistent storage and reinitialization.
- Reject incompatible grids, clocks and incomplete BMI coupling before evaluating the chain.
- Distinguish arbitrary-trace information loss from the restricted Ross model family.

The reviewer independently ran 7 initial example tests, 146 optimization/recovery tests after the
boundary fix, and 22 BMI/example tests after conversion. The final verification record includes the
expanded tests and final source state. The final raw observation audit recalculates every recorded
BMI objective and held-out recommendation rather than relying only on summary files.

The boundary correction can change suggestions at rounded endpoints relative to old package
versions. Original code is required for exact historical replay. Fresh example studies bind their
package source hashes; generic older studies without source hashes do not gain retroactive
cross-version recovery protection from this work.

The complete BMI matrix and original partial-observability gate remain distinct evidence sets.
No passing claim is made for application partial BO or for the earlier failed partial gate.
