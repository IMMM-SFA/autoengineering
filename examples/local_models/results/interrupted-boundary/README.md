# Interrupted development matrix

This first executable development matrix stopped after 20 completed studies and four initial
copper BO evaluations. `SearchSpace.decode` returned a logarithmic boundary outside its own
bounds due to floating-point rounding. The next `encode` rejected that action before evaluation.

Keep these adverse execution records. They are not a complete comparison and must not be pooled
with the replacement matrix. The numerical endpoint correction preserves the parameter bounds
and does not change the example splits, methods, budgets or selection rules. Fresh studies are
required after the decoder correction. Resuming historical studies across this code change is
not asserted to preserve exact suggestion identity at affected endpoints.

Before this matrix, a four-evaluation Sobol smoke test completed in all three domains. A matrix
bootstrap also caught a missing NumPy import in the new ranking calculation before any study
executed. Both were implementation checks, not comparison evidence.
