# Unified Paper Package · 2026-08-24

This is the single consolidated package for the current paper work.

## Use this path from now on

- Root package: [./](./)

## Directory layout

- `manuscript/arxiv/`
  - current arXiv-stage draft
  - checked bibliography
  - Chinese reading note
  - reference checklist
- `manuscript/elsarticle/`
  - older full-system `elsarticle` draft
  - compiled PDF
  - Chinese structural notes
- `support/`
  - curated engineering/project summary
  - experiment index and key results
  - copied benchmark case files
  - copied reports, handoff notes, and plans

## Read order

1. [support/README.md](support/README.md)
2. [support/01_project_state_and_scope.md](support/01_project_state_and_scope.md)
3. [support/02_engineering_architecture_and_workflow.md](support/02_engineering_architecture_and_workflow.md)
4. [support/03_experiment_index_and_key_results.md](support/03_experiment_index_and_key_results.md)
5. [support/04_paper_status_completed_and_todo.md](support/04_paper_status_completed_and_todo.md)

Then continue writing from one of these:

- Main active draft: [manuscript/arxiv/skill_evolution_blind_vulnerability_analysis_arxiv.tex](manuscript/arxiv/skill_evolution_blind_vulnerability_analysis_arxiv.tex)
- Draft analysis and review notes: [manuscript/arxiv/draft_analysis_20260902.md](manuscript/arxiv/draft_analysis_20260902.md)
- Older systems-style draft: [manuscript/elsarticle/skillclaw_confirmation_feedback_elsarticle.tex](manuscript/elsarticle/skillclaw_confirmation_feedback_elsarticle.tex)

The active arXiv draft was refreshed from the user-provided 2026-09-02 version.
The superseded arXiv draft is retained under `paper/archive/manuscript_snapshot_20260824/`.

## Scope

This package is meant to contain:

- the current manuscript sources,
- compiled PDFs worth reviewing,
- bibliography and citation notes,
- experiment summaries and key tables,
- engineering status and handoff material needed for later revision.

It does not duplicate the entire `runtime/imports/remote_vm/` tree, because that would
be too large and noisy. The copied tables and reports inside `support/` are the index
layer used to trace back to raw run artifacts when needed.
