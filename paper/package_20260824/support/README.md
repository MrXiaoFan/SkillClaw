# Paper Materials Package · 2026-08-24

This folder is a curated support package for continuing the current paper work without
re-scanning the whole repository.

## How this support package differs from the source snapshot

This is a curated, paper-facing copy. The provenance-bearing source snapshot lives at
`../../materials_20260824/`. Case files may intentionally differ because the support copy
sanitizes leakage-prone ground-truth fields. Preserve both trees unless a specific file-level
comparison has been completed.

## Primary paper files

- Main arXiv-style draft: [../manuscript/arxiv/skill_evolution_blind_vulnerability_analysis_arxiv.tex](../manuscript/arxiv/skill_evolution_blind_vulnerability_analysis_arxiv.tex)
- Chinese draft explanation: [../manuscript/arxiv/skill_evolution_blind_vulnerability_analysis_arxiv_zh.md](../manuscript/arxiv/skill_evolution_blind_vulnerability_analysis_arxiv_zh.md)
- Earlier full-system `elsarticle` draft: [../manuscript/elsarticle/skillclaw_confirmation_feedback_elsarticle.tex](../manuscript/elsarticle/skillclaw_confirmation_feedback_elsarticle.tex)
- Checked bibliography for the arXiv draft: [../manuscript/arxiv/references_arxiv_checked.bib](../manuscript/arxiv/references_arxiv_checked.bib)
- Reference checklist: [../manuscript/arxiv/reference_checklist_skill_evolution_arxiv_20260824.md](../manuscript/arxiv/reference_checklist_skill_evolution_arxiv_20260824.md)

## Read in this order

1. [01_project_state_and_scope.md](01_project_state_and_scope.md)
2. [02_engineering_architecture_and_workflow.md](02_engineering_architecture_and_workflow.md)
3. [03_experiment_index_and_key_results.md](03_experiment_index_and_key_results.md)
4. [04_paper_status_completed_and_todo.md](04_paper_status_completed_and_todo.md)

After that, use the selected historical evidence under:

- [cases/](cases/)
- [reports/](reports/)
- [handoff/](handoff/)
- [plans/](plans/)

Most duplicated reports have been removed. The remaining files under `reports/` are historical
exceptions with content differences; active reports remain under `reports/current/`.
Heavy raw runtime artifacts under `runtime/imports/remote_vm/` were not duplicated into this
folder. Follow report paths back to those run artifacts when deeper inspection is needed.

## Why this package exists

The repository currently contains several generations of reports, handoff notes, weekly
summaries, and experiment outputs. Some of them are still useful, but they are spread
across `reports/`, `docs/handoff/`, `docs/plans/`, `benchmarks/cases/`, and `paper/`.
This package pulls the paper-relevant subset into one place.

## What is already true

- The engineering chain `remote blind run -> scoring -> feedback -> evolve -> gate ->
  live skill publish` exists and has run for real.
- Multi-case firmware experiments already show that different skills materially change
  blind localization outcomes.
- Current evidence is still not strong enough to claim that the system has already
  achieved stable autonomous skill improvement.

## What not to assume

- Do not treat every historical published candidate skill as a real improvement.
- Do not treat every old weekly report as final ground truth; several later experiments
  revised earlier conclusions.
- Do not assume the older `elsarticle` draft reflects the latest experimental position.

## Notes

- This package is a snapshot created on 2026-08-24.
- It intentionally keeps both the new arXiv draft and the older `elsarticle` draft,
  because both still contain useful material.
