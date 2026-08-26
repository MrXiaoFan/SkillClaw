# Case CVE Catalog for Paper (2026-08-25)

## What This Package Contains

- [case_cve_backfill_20260825.md](/D:/Code/SkillClaw/SkillClaw/paper/materials_20260824/reports/briefing_20260825/case_cve_backfill_20260825.md)
- [case_cve_backfill_20260825.csv](/D:/Code/SkillClaw/SkillClaw/paper/materials_20260824/reports/briefing_20260825/case_cve_backfill_20260825.csv)

These two files are the paper-facing copies of the engineering-side CVE backfill audit for benchmark cases whose `ground_truth.cves` field was previously empty.

## How To Read It

- The authoritative benchmark case files remain under [benchmarks/cases](/D:/Code/SkillClaw/SkillClaw/benchmarks/cases).
- The files in this directory are for paper writing, result checking, and citation support.
- `assignerOrgId`, `assignerShortName`, and `reporter` were extracted from official CVE records.

## Main Outcome

- Audited empty-case set: 19
- Backfilled cases: 18
- Intentionally left empty: 1

The only case intentionally left without a CVE is:

- `f9k1122-webs-overflow-formSetPassword.json`

Reason:

- the local case file already marks it as a duplicate / invalid dataset copy of `formSetSystemSettings`, so it should not be presented as an independent CVE-bearing benchmark case.

## Reporter Interpretation for the Paper

The following reporter names belong to your own team and should be treated as team-originated disclosures rather than unrelated external reporters:

- `LtzHust (VulDB User)`
- `LtzHust2 (VulDB User)`
- `LtzHuster (VulDB User)`
- `LtzHuster2 (VulDB User)`
- `Jimi (VulDB User)`

The following reporter in this table is not currently marked as part of your team:

- `panda_0x1 (VulDB User)`

There is also one case with no reporter listed in the official record:

- `CVE-2024-30637`

## Practical Use in the Manuscript

For the paper draft, these tables can support three kinds of statements:

1. Which benchmark firmware cases already correspond to public CVE records.
2. Which benchmark cases are team-originated disclosures versus non-team disclosures.
3. Which samples should be excluded from publication tables because they are invalid duplicates.

## Recommended Citation / Cross-Check Path

When the paper agent needs to verify one case, use this order:

1. The benchmark case JSON under [benchmarks/cases](/D:/Code/SkillClaw/SkillClaw/benchmarks/cases)
2. The backfill table in this folder
3. The official CVE record URL stored in the backfill table

## Notes on Model / Product Naming

One known naming inconsistency remains worth mentioning in the paper materials:

- `f1202-httpd-overflow-fromAdvSetWan.json` maps to `CVE-2025-7527`, but public records often label the product as `FH1202` while the local dataset uses `F1202`.

This does not currently block benchmark use, but the naming mismatch should be kept visible in paper-side notes.
