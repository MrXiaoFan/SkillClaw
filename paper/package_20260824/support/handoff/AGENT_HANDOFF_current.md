# Current handoff — 2026-09-03

## Start here

- [Research roadmap](../../../docs/plans/research_roadmap_20260820.md)
- [Current reports](../../../reports/current/README.md)
- [Catalog diagnostics](../../../reports/current/briefing_20260902/README.md)
- [Paper package README](../../README.md)

## Engineering status

The main loop is operational:

`run → score/confirmation → feedback → evolve → gate → publish`

The four skill modes are explicitly separated:

- `catalog`: downstream model receives the OpenClaw-compatible catalog and lazy-loads skills.
- `inline` / `server-inline-lexical`: SkillClaw server performs lexical retrieval and injects bodies.
- `server-catalog`: SkillClaw server asks a selector model to choose names, then injects bodies.
- session disable override: no-skill control condition.

The research main line is server-side catalog selection. No independent client catalog is planned.

## Latest server-catalog finding

The selector trace is preserved through final artifacts. On F9K WlanSetup, the focused v4
server-side family guard selected only `elf-cwe120-firmware-triage` in three runs:

- scores: `4.5`, `2.0`, `4.5`; mean `3.67/10`;
- function and evidence hit in 2/3 runs;
- CVE identity hit in 0/3 runs;
- the command-injection skill was excluded by the explicit buffer-overflow guard.

This is a diagnostic improvement, not evidence of stable server-catalog effectiveness. See
[the full WlanSetup report](../../../reports/current/briefing_20260902/server_catalog_f9k_wlansetup_20260903.md)
and [the inline comparison](../../../reports/current/briefing_20260902/server_catalog_vs_inline_f9k_20260903.md).

The server-catalog path no longer reuses the lexical session cache. A post-fix smoke confirmed
that all checked history turns use `stable_action=server-select`; see the
[trace smoke report](../../../reports/current/briefing_20260902/server_catalog_trace_smoke_20260903.md).

## Next work

1. Improve source-run quality before generating a new held-out candidate; the current WlanSetup v4 source set is correctly blocked (`function_identity_miss` in 3/3 and root-cause hit in 0/3).
2. Keep candidate generation isolated and do not bypass the quality gate with `allow-source-quality-risk`.
3. Keep the arXiv concept manuscript independent; do not add unverified catalog or v4 claims.
4. Continue final paper-package cleanup only after engineering evidence is frozen.

## Verification

Latest targeted tests: `15 passed` (`tests/test_session_skill_overrides.py` and
`tests/test_record_finalizer.py`). The full suite still has the previously documented unrelated
baseline failures and has not been used as a release gate for this change.

Held-out runner tests: `10 passed`. The current v4 WlanSetup source audit is blocked as
expected and no candidate was generated or published from it.

The forced source-quality v2 check also remains blocked: three runs scored `4.5/2.0/2.0`,
with exact predicted-function hits `0/3` and root-cause hits `0/3`. See
[the source-quality report](../../../reports/current/briefing_20260902/source_quality_v2_f9k_wlansetup_20260903.md).
