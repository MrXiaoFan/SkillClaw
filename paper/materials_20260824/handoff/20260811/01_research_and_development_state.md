# 01 Research and Development State

## 1. Purpose of this file

This file is the first entry point for a successor agent.

It answers four questions:

1. What are the real research and engineering goals now?
2. What changed from native SkillClaw to the current extended system?
3. What has actually been completed?
4. What has not yet been proven, even if the pipeline looks complete?

Read this file before touching services, benchmarks, or the paper draft.

## 2. Current project goal

The project goal is not simply "use an LLM to answer known CVEs."

The current target is a **skill evolution framework for vulnerability analysis**:

1. expose server-side skills to an analysis agent,
2. run blind vulnerability-analysis tasks,
3. score and externally confirm the result,
4. convert the run into structured feedback,
5. let the evolution service generate candidate skill revisions,
6. gate those revisions before they can affect the live skill library.

The intended scientific claim is therefore about a **trustworthy vulnerability-skill lifecycle**, not about raw benchmark accuracy alone.

## 3. What native SkillClaw originally did

The native system already provided the base agent infrastructure:

- request proxying and protocol bridging in `skillclaw/api_server.py`
- server-side skill management and inline injection in `skillclaw/skill_manager.py:1069` and `skillclaw/skill_manager.py:1108`
- session capture and sharing in `skillclaw/launcher.py`, `skillclaw/skillspace.py`, and related storage code
- evolution-side consumption in `evolve_server/engines/workflow.py`

In short, native SkillClaw already knew how to:

- receive requests,
- select and inject skills,
- store sessions,
- let an evolution service consume session data.

## 4. What the extension added

The extension added the research-facing layer that native SkillClaw did not have.

### 4.1 Benchmark and execution layer

- benchmark case definitions under `benchmarks/cases/`
- local and remote case runners:
  - `evaluation/runs/run_single_case.py:569`
  - `evaluation/runs/run_remote_case.py:763`
  - `evaluation/remote/experiment_vm.py:280`

### 4.2 Result scoring and finalization layer

- structured scoring rules in `evaluation/cases/loader.py:13`
- score calculation in `evaluation/runs/score_case_output.py:83`
- record finalization in `evaluation/postprocess/finalize_record.py:537`

### 4.3 External evidence and confirmation layer

- generic validation modules in `evaluation/validation/`
- confirmation-specific modules in `evaluation/confirmation/`
- replay-gate compatibility path in `skillclaw/replay_gate_worker.py:42`

### 4.4 Feedback and evolution handoff layer

- validated handoff entry in `evaluation/evolution.py:345`
- feedback bundle generation in `evaluation/reporting/feedback/build_feedback_bundle.py:265`
- current report refresh in `evaluation/reporting/current/refresh_reports.py:288`
- evolve-side feedback loading in `evolve_server/engines/workflow.py:104`
- evolve-side validated-pair loading in `evolve_server/engines/workflow.py:168`

### 4.5 Skill workspace split

The current system no longer treats "all skills" as one flat place.

The workspace is now logically separated into:

- `skillspace/live/`: the live skills actually injected into later runs
- `skillspace/share/default/candidate_skills/`: candidate revisions proposed by evolve
- `skillspace/share/default/skills/`: shared persisted skill snapshots and versions

This separation is important: a candidate may exist and still never become a live skill.

## 5. Current engineering status

### 5.1 What is already real

The following chain already exists in code and in stored artifacts:

`blind case -> run -> score -> confirm/validate -> finalize -> feedback bundle -> evolve candidate -> gate decision`

The evidence for that claim is spread across:

- code:
  - `evaluation/runs/run_single_case.py:569`
  - `evaluation/runs/run_case_validation.py:67`
  - `evaluation/postprocess/finalize_record.py:537`
  - `evaluation/reporting/feedback/build_feedback_bundle.py:265`
  - `evaluation/evolution.py:345`
  - `evolve_server/engines/workflow.py:104`
  - `evolve_server/engines/workflow.py:168`
- reports:
  - `reports/current/runset.md`
  - `reports/current/result_matrix.md`
  - `reports/current/skill_feedback_bundle.json`
  - `reports/current/skill_gate.json`
  - `reports/current/briefing_20260805/closed_loop_proof.csv`

### 5.2 What is still not proven

The following stronger claims are **not** yet supported by current evidence:

1. evolved skills already improve later held-out tasks,
2. a candidate skill has been stably accepted and published into the live library,
3. a target firmware vulnerability can only be found with one specific skill and fails without it.

This boundary matters. Future agents must not overstate the current maturity.

## 6. Completed experiments that matter

### 6.1 Core six-case remote blind runset

The current engineering runset is defined in:

- `reports/current/runset_manifest.json`
- `reports/current/runset.md`
- `reports/current/result_matrix.md`

The six core source/binary cases currently tracked are:

1. `giflib-5.1.2 / CVE-2016-3977`
2. `libxml2-2.9.4 / CVE-2017-8872`
3. `tcpdump-4.9.1 / CVE-2018-14469`
4. `libarchive-3.8.0 / CVE-2025-60753`
5. `tcpdump-4.9.1 / CVE-2017-13031`
6. `exiv2-0.26 / CVE-2017-17725`

Representative scores from `reports/current/result_matrix.md`:

- giflib: `8/10`
- libxml2: `8/10`
- tcpdump-2018-14469: `2/10`
- libarchive: `10/10`
- tcpdump-2017-13031: `10/10`
- exiv2: `6/10`

### 6.2 Firmware skill ablation

The current firmware ablation package is in:

- `reports/current/briefing_20260805/summary.md`
- `reports/current/briefing_20260805/firmware_ablation_summary.csv`
- `reports/current/briefing_20260805/firmware_ablation_runs.csv`

The two firmware cases under ablation are:

- `firmware2-login-cgi-cve-2026-2527`
- `firmware2-wireless-cgi-cve-2026-2529`

The important result is not just absolute score. It is that **changing only the exposed skill profile changes blind-analysis quality**.

Mean score summary:

- login case:
  - `none = 4.333`
  - `relevant = 5.0`
  - `wrong = 4.5`
  - `seed = 5.0`
- wireless case:
  - `none = 2.667`
  - `relevant = 3.0`
  - `wrong = 3.0`
  - `seed = 4.0`

This is useful evidence that skill content matters.
It is not yet proof of strict necessity.

### 6.3 Closed-loop proof

The current closed-loop proof table is:

- `reports/current/briefing_20260805/closed_loop_proof.csv`

What it proves:

- handoff happened,
- evolve consumed receipts,
- candidate jobs were queued,
- validation follow-up jobs existed.

What it does **not** prove:

- accepted publication into live,
- measurable post-evolution gains.

## 7. The single most important current truth

The most important current truth is:

**feedback exists, candidate revision exists, gate decision exists, but live-skill improvement is not yet a proven outcome.**

Any new experiment, report, or paper section should preserve that distinction.

## 8. Suggested reading order for the next agent

1. `docs/handoff/20260811/02_paper_frame_and_manuscript_state.md`
2. `docs/handoff/20260811/03_engineering_status_tests_and_next_plan.md`
3. `paper/skillclaw_confirmation_feedback_elsarticle.tex`
4. `reports/current/briefing_20260805/summary.md`
5. `reports/current/runset.md`
