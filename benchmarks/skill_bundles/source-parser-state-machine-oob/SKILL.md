---
name: source-parser-state-machine-oob
description: "Analyze parser state-machine source code for cur/end/avail lookahead reads that are not dominated by sufficient bounds checks. Use for source-level parser OOB read/write localization, especially libxml2-style chunked parsers. NOT for generic PLT dangerous-function triage."
category: vulnerability-research
---

# source-parser-state-machine-oob

This experimental bundle pairs textual guidance with executable source checks.

For libxml2-like parser code, first inspect parser state-machine functions and
look for mismatches between available-byte guards and later lookahead reads:

- `if (avail < N)` or equivalent guard
- later `cur[K]`, `in->cur[K]`, or `buf[K]`
- vulnerable when `K + 1 > N` and no stronger guard dominates the access

Use `scripts/check_avail_guard.py` to produce machine-readable evidence before
finalizing an answer.
