# Frozen catalog comparison matrix — 2026-09-03

## Scope

This matrix freezes the currently reproducible comparison boundary: two F9K1122 firmware
buffer-overflow cases, remote blind execution, the same SkillClaw proxy and 36-skill catalog.
`catalog` here means the server-side selector condition; the downstream model never reads a
local client catalog.

## Aggregate results

| Case | Condition | Runs | Mean score | Expected-family selection | Function/evidence signal |
| --- | --- | ---: | ---: | --- | --- |
| WISP5G | server-catalog v1 | 5 | 2.00 | 0/5; command injection | 0/5 consistently |
| WISP5G | server-inline-lexical | 3 | 2.83 | 0/3; Windows command injection | 1/3 partial |
| WISP5G | server-catalog v4 guard | 3 | 2.00 | 3/3; CWE-120 family | 0/3 |
| WlanSetup | server-catalog v1 | 3 | 2.00 | 0/3; command injection | 0/3 |
| WlanSetup | server-catalog v4 guard | 3 | 3.67 | 3/3; CWE-120 family | 2/3 |

## Interpretation boundary

The v4 server-side guard improves family-level selection on both cases and preserves a complete
selector trace. It does not establish stable end-to-end improvement: WISP5G remained at 2.0/10,
CVE identity was missed in all v4 runs, and WlanSetup still had material score variance. The
current evidence supports a systems diagnosis, not a general superiority claim over lexical
retrieval.

## Reproduction records

- [WISP5G server-catalog report](server_catalog_effectiveness_f9k_20260903.md)
- [WISP5G catalog versus inline report](server_catalog_vs_inline_f9k_20260903.md)
- [WlanSetup selector guard report](server_catalog_f9k_wlansetup_20260903.md)
- Runtime artifacts are under `runtime/imports/remote_vm/` with matching run IDs.

## Frozen next experiment

The v4 cross-case rerun is now complete. Do not tune against these two cases further; retain
the result as a limitation/diagnostic study and, if needed, reserve any additional case for a
pre-registered held-out validation rather than iterative debugging.
