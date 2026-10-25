# References for pilot-based method selection

These sources informed the working heuristic in
[the optimization guide](../docs/optimization.md#choosing-a-search-method).
Reusable BibTeX entries are saved in
[references.bib](../reports/model-search-results/references.bib).

- Peter I. Frazier (2018), _A Tutorial on Bayesian Optimization_.
  [arXiv:1807.02811](https://arxiv.org/abs/1807.02811),
  DOI [10.48550/arXiv.1807.02811](https://doi.org/10.48550/arXiv.1807.02811).
  Explains Gaussian-process surrogates, acquisition functions and the rationale
  for BO when objective evaluations are expensive. It does not validate our
  proposed pilot size or a universal model-complexity threshold.
- James Bergstra and Yoshua Bengio (2012), _Random Search for Hyper-Parameter
  Optimization_, Journal of Machine Learning Research 13(10), 281-305.
  [Publisher page](https://www.jmlr.org/papers/v13/bergstra12a.html).
  Supports random search as a baseline and distinguishes nominal parameter count
  from the smaller subset that may control performance. Its results concern
  hyperparameter search and do not establish a Sobol-to-BO switching rule for
  engineering chains. No DOI is supplied by the publisher page used here.

Titles, author names, years and available identifiers were checked against the
linked primary-source pages. The heuristic is an adopted working approach with an
open TODO to "further explore a pilot-based selection rule". The current benchmark
is evidence for the distinction between target attainment, runtime and held-out
prediction, not validation of that rule across new problems.
