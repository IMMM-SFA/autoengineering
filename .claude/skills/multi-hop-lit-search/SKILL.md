---
name: multi-hop-lit-search
description: Find research literature by following citation chains — fetch a paper, extract its references, fetch the most relevant of those, and repeat for a few hops. Use for academic/research queries where a single search misses connected work. Adapted from alphaXiv openresearch-cli's multi-hop literature search.
---

# Multi-Hop Literature Search

A single search returns a shallow slice. Multi-hop search follows the citation
graph to reach the connected literature a keyword query misses. Adapted from
openresearch-cli's literature search (see the repo `NOTICE`).

Use this before a generic web search for academic or research questions. It is
usually invoked by `deep-research-candidates`, but works standalone.

## Tool discipline

Use only visible tools. Prefer feynman's `alpha_search` / `fetch_content` when
present (alphaXiv full-text, no login); otherwise `WebSearch` / `WebFetch`. Prefer
metadata, abstracts, and HTML over PDF parsing; if only a PDF exists, cite its URL
and mark full-text parsing as blocked rather than fetching it. Provider-agnostic.

## Procedure

1. **Seed (hop 0).** Turn the question into 2–3 distinct queries covering the method,
   its known weakness, and comparisons/reviews. Search; collect the most relevant
   seed papers with title, authors, year, venue, and a stable URL/DOI.

2. **Expand (hops 1–2).** For each strong seed, fetch it and extract its reference
   list and (where available) papers that cite it. Rank the new papers by relevance
   to the question and recency; fetch the top few. Repeat for at most 2–3 hops total.

3. **Stop.** Stop when a hop surfaces no new relevant work, when the same key papers
   recur across branches (a consensus signal), or at the hop budget. Do not chase the
   whole graph.

4. **Deduplicate and record.** Merge by DOI/title. Write a source list with, for each
   entry: citation, URL/DOI, one-line relevance, and the hop it was found at. Note
   consensus vs. disagreement across sources.

## Output

A deduplicated, cited source list ready to drop into a research brief's References
and into a candidate's `sources:` field. Flag any source whose URL could not be
verified as needing follow-up rather than dropping it silently.
