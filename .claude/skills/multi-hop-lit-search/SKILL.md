---
name: multi-hop-lit-search
description: Find relevant research by following references and citing papers within a bounded search.
---

# Search citation chains

Use citation links to extend a focused literature search when the initial results leave an
important question unresolved. This skill adapts alphaXiv's openresearch-cli. See `NOTICE`.
Use only search and source-reading tools available in the current session.

1. Form two or three queries covering the method, the observed failure, and relevant comparisons.
   Record seed sources with title, authors, year, and DOI or stable URL.
2. Read relevant sources and follow their references or citing papers. Prioritize material that
   changes the candidate assessment. Bound the search to two or three hops unless the user has
   authorized a larger investigation.
3. Stop when no new relevant evidence appears or the source budget is spent. Repeated citations
   show overlap in the search, not necessarily independent agreement.
4. Deduplicate by DOI or title. Record source access, relevance, discovery path, supported claims,
   conflicting findings, and unresolved questions.

Prefer primary methods, data, and implementation sources for candidate claims. Read abstracts,
HTML, or PDFs with the available tools. If only an abstract is accessible, state that limit.
Do not present an unread paper as verified support.

For model improvement research, look for data requirements, evaluation design, compute, and
reported failures alongside performance. Deliver a cited source list that the research brief and
candidate rationale can use. Keep inaccessible or uncertain sources visible as unresolved.
