# Current Experiment Reports

This directory is the working index for experiment conclusions. Historical evidence remains in
place; this README only provides the shortest route to the material that should be read first.

## Start here

1. [runset.md](runset.md) — frozen run-set overview
2. [result_matrix.md](result_matrix.md) — consolidated result matrix
3. [experiment_log_all_20260820.md](experiment_log_all_20260820.md) — experiment log
4. [experiment_archive_all_20260820.md](experiment_archive_all_20260820.md) — historical archive index
5. [cleanup_candidates_20260903.md](cleanup_candidates_20260903.md) — file classification and cleanup boundary

## Current unresolved retrieval question

- [diagnostic_f9k_skill_conditions_20260902.md](briefing_20260902/diagnostic_f9k_skill_conditions_20260902.md)
  — no-skill, natural retrieval, and catalog smoke comparison
- [server_catalog_effectiveness_f9k_20260903.md](briefing_20260902/server_catalog_effectiveness_f9k_20260903.md)
  — server-side catalog selection was operational but selected the wrong skill in the tested case

These reports are diagnostic evidence, not a successful retrieval claim.

## Main validated experiment lines

- [briefing_20260816/](briefing_20260816/) — frozen/clean validation and main claim support
- [briefing_20260826/](briefing_20260826/) — held-out transfer follow-up
- [briefing_20260827/](briefing_20260827/) — clean transfer follow-up
- [briefing_20260902/](briefing_20260902/) — latest retrieval and catalog diagnostics
- [ablation/](ablation/) — ablation evidence and summaries

## Reproduction rule

Read a summary report for the conclusion, then follow its run IDs, case IDs, and paths into
`runtime/`. Do not delete or rewrite runtime records when simplifying this directory. The
reports are the index layer; `runtime/` is the source-of-record layer for reruns and auditing.

## Older material

Older briefings and experiment logs remain under their dated directories. They may contain
superseded interpretations, so prefer the latest report that explicitly revisits the same case
or condition. No historical report is removed solely because it is no longer the preferred summary.
