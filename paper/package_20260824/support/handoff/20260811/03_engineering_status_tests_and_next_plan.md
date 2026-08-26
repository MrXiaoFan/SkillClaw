# 03 Engineering Status, Tests, and Next Plan

## 1. Current engineering status in one paragraph

The repository is in a mid-refactor but usable state. The core execution path for blind vulnerability-analysis runs, scoring, finalization, feedback bundling, and evolve-side candidate gating exists in code and has stored artifacts behind it. The biggest engineering truth right now is that the system is good at producing **auditable feedback artifacts**, but it still lacks a clean demonstrated example of **accepted publication into the live skill library followed by measurable downstream improvement**.

## 2. Current entry points and control flow

### 2.1 Skill selection and injection

- `skillclaw/skill_manager.py:1069`
  - `select_skills_for_inline(...)`
- `skillclaw/skill_manager.py:1108`
  - `_keyword_retrieve_for_inline(...)`

Current implication:

- skill selection is still code-side retrieval,
- not LLM-side self-selection,
- and the current inline mode can still over-select semantically nearby but task-mismatched skills.

### 2.2 Run execution

- `evaluation/runs/run_single_case.py:569`
  - single-case execution CLI entry
- `evaluation/runs/run_remote_case.py:763`
  - remote-oriented case execution CLI entry
- `evaluation/runs/run_case_validation.py:67`
  - run validation entry

### 2.3 Scoring and finalization

- `evaluation/cases/loader.py:13`
  - default scoring schema
- `evaluation/runs/score_case_output.py:83`
  - output scoring
- `evaluation/postprocess/finalize_record.py:537`
  - final record construction

### 2.4 Feedback and evolution

- `evaluation/reporting/feedback/build_feedback_bundle.py:265`
  - feedback bundle generation
- `evaluation/evolution.py:345`
  - validated handoff entry
- `evolve_server/engines/workflow.py:104`
  - feedback bundle loading
- `evolve_server/engines/workflow.py:168`
  - validated-pair loading

### 2.5 Replay gate naming transition

- `skillclaw/replay_gate_worker.py:42`
  - `ReplayGateWorker`
- `skillclaw/validation_worker.py`
  - still exists as a compatibility-facing module

Current implication:

- the architecture is already shifting from a generic "validation worker" label toward a more precise "replay gate" label,
- but naming and responsibility boundaries are still only partially cleaned up.

## 3. Current local configuration

Checked in this session via:

- `.\\.venv\\Scripts\\python.exe -m skillclaw.cli config show`

Key current runtime settings:

- `skills.dir = D:\\Code\\SkillClaw\\SkillClaw\\skillspace\\live`
- `sharing.local_root = D:\\Code\\SkillClaw\\SkillClaw\\skillspace\\share`
- `skills.injection_mode = inline`
- `sharing.skill_reload_mode = off`
- `validation.enabled = True`
- `validation.mode = replay`
- `dashboard.enabled = True`

Interpretation:

1. the active injected library is the live workspace under `skillspace/live/`,
2. shared runtime artifacts are under `skillspace/share/`,
3. auto reload is currently off, so live-skill changes should not be assumed to hot-reload unless explicitly rechecked.

## 4. Current service status checked in this session

Checked in this session via:

- `netstat -ano | findstr ":30000 :8787 :3788"`

Observed result:

- no positive listener output was captured in this turn

This means:

- this session did **not** verify that SkillClaw proxy, Evolve Server, and Dashboard were all actively listening at the time of writing,
- so later agents should not assume the three local services are already online.

## 5. Test status checked in this session

The following command was run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider `
  tests\test_evaluation_pipeline.py `
  tests\test_remote_run_orchestration.py `
  tests\test_agent_workspace_feedback.py `
  tests\test_skillspace_layout.py `
  tests\test_skillspace_launcher.py `
  tests\test_inline_skill_session_cache.py `
  tests\test_summarizer_skill_references.py
```

Result:

- `148 passed in 20.71s`

This is strong evidence that the current refactor has not obviously broken the key evaluation/evolution/skillspace logic covered by these tests.

## 6. Current engineering assessment

### 6.1 What is healthy

1. the repository now has clearer modular separation than the earlier `experiment_*` sprawl,
2. `evaluation/` is a real reusable layer now,
3. `reports/current/briefing_20260805/` already forms a reusable reporting package,
4. skill live/candidate/share separation is the correct safety boundary.

### 6.1.1 New 2026-08-11 remote wireless update

After the real remote reruns on August 11, 2026:

1. `firmware2-wireless-live-20260811g` proved that the remote VM path really reaches:
   - remote Claude run,
   - local SkillClaw session capture,
   - evolve candidate generation,
   - replay-gate validation,
   - and final gate rejection.
2. the new replay-gate rule is behaving correctly:
   - candidate was rejected because `candidate_mean_score == baseline_mean_score`,
   - not because the loop was broken.
3. the relevance audit for the wireless firmware case has now been tightened:
   - `embedded-cgi-command-injection-triage` remains `has_task_relevant_skill`
   - `firmware-embedded-lua-shell-extraction` is now `no_task_relevant_skill`

Evidence files:

- `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.md`
- `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.json`
- `runtime/imports/remote_vm/firmware2-wireless-live-20260811g/firmware2-wireless-live-20260811g-final-enriched.json`
- `runtime/imports/remote_vm/firmware2-wireless-wrong-20260811g/firmware2-wireless-wrong-20260811g-final-enriched.json`
- `runtime/logs/remote_vm_commands.log`

### 6.1.2 New 2026-08-11 feedback-bundle/runtime update

In the follow-up engineering check on August 11, 2026, two additional facts were confirmed:

1. Evolve status was advertising:
   - `feedback_bundle_path = runtime/evolve/skill_feedback_bundle.json`
   but that file did not exist at first.
2. the broader current report bundle still existed at:
   - `reports/current/skill_feedback_bundle.json`
   and contained only the older two-skill current runset feedback (`source-parser-state-machine-oob`, `elf-cwe120-plt-analysis`),
   which is not the same thing as the latest firmware runtime feedback.

To reduce this mismatch, the code was tightened in two ways:

1. `evolve_server/engines/workflow.py`
   - `_load_feedback_bundle(...)` now falls back to the default current report bundle if the configured runtime bundle path is missing.
2. `evaluation/evolution.py`
   - `handoff_validated_run(...)` now materializes a run-scoped runtime feedback bundle at the exact path reported by Evolve status, instead of only building the in-memory handoff envelope.

The behavior was smoke-checked with the latest firmware live run:

- source record:
  - `runtime/imports/remote_vm/firmware2-wireless-live-20260811g/firmware2-wireless-live-20260811g-final-enriched.json`
- generated runtime bundle:
  - `runtime/evolve/skill_feedback_bundle.json`

Observed result:

- the runtime bundle now exists,
- it contains one skill entry:
  - `embedded-cgi-command-injection-triage`
- its current gate decision is still:
  - `insufficient_evidence`

This is the correct current engineering interpretation:

1. the runtime feedback path is now no longer silently empty,
2. Evolve can now read either:
   - the explicitly materialized runtime bundle, or
   - the default current report bundle as a fallback,
3. but the firmware loop is still not "effective" yet in the research sense, because the current runtime bundle still records only one low-scoring relevant firmware run rather than a demonstrated improvement trend.

### 6.2 What is still weak

1. retrieval quality is still noisy for some source-only or parser-heavy cases,
2. candidate generation is easier than candidate acceptance,
3. current paper-facing evidence is stronger on lifecycle closure than on evolution efficacy,
4. skill contribution is still mostly inferred from ablation and mismatch analysis, not causally proven.

## 7. Historical cleanup performed in this handoff cycle

This handoff cycle is consolidating new materials under:

- `docs/handoff/20260811/`

The goal is to stop future agents from anchoring on older root-level handoff notes that mixed partially verified conclusions with earlier states.

If cleanup is continued, the preferred direction is:

1. keep active handoff materials under `docs/handoff/<date>/`
2. move superseded handoff notes into an archive subtree
3. avoid creating new root-level handoff files

## 8. What the next agent should do first

### P0. Verify live publication, not just candidate existence

The next engineering milestone is to produce one clean, hard proof of:

1. candidate generated,
2. gate accepted,
3. published into live skill area,
4. later run actually used the new live skill,
5. later run outcome changed in the intended direction.

Until all five are evidenced together, the loop is still only partially complete.

### P1. Freeze a stricter necessity experiment

The best current experiment target is a firmware case.

The next agent should design one case with four controlled conditions:

1. no skill
2. target skill
3. wrong skill
4. degraded target skill

Everything else should be held constant:

- prompt template,
- model,
- tool access,
- workspace,
- and scoring.

### P2. Normalize skill structure before more large-scale runs

This session's skill length audit showed major variance in live skill size.

The next agent should normalize:

- trigger conditions,
- exclusion conditions,
- core procedure blocks,
- evidence/stop conditions.

Priority candidates for review include:

- `skillspace/live/source-parser-state-machine-oob/SKILL.md`
- `skillspace/live/cisco-vmanage-firmware-analysis/SKILL.md`
- `skillspace/live/skillclaw-skill-discovery/SKILL.md`
- `skillspace/live/embedded-cgi-command-injection-triage/SKILL.md`

### P3. Keep paper claims synchronized with engineering truth

Every future paper edit should be checked against:

- `reports/current/runset.md`
- `reports/current/result_matrix.md`
- `reports/current/briefing_20260805/summary.md`
- `reports/current/briefing_20260805/closed_loop_proof.csv`

## 9. What must not be confused again

Do not collapse these into one thing:

1. confirmation / validation of a case result
2. replay gate decision on a candidate skill change
3. actual publication into the live skill library
4. later measured performance gain from the published skill

The repository already has artifacts for (1) and (2).
It does not yet have strong demonstrated evidence for (3) plus (4) together.

### 6.1.3 New 2026-08-11 latest rerun `20260811h`

A further remote rerun completed after service restart:

- run id: `firmware2-wireless-live-20260811h`
- final record:
  - `runtime/imports/remote_vm/firmware2-wireless-live-20260811h/firmware2-wireless-live-20260811h-final-enriched.json`
- selected skill:
  - `embedded-cgi-command-injection-triage`
- score:
  - `2.0 / 10`
- relevance audit:
  - `has_task_relevant_skill`
- enriched handoff:
  - `evolution_handoff.status = handed_off`
- runtime feedback bundle path persisted into the record:
  - `runtime/evolve/skill_feedback_bundle.json`

This rerun confirms that the post-restart path is still intact:

1. remote VM -> SkillClaw proxy,
2. validated final record -> local enriched record,
3. enriched record -> runtime feedback bundle,
4. Evolve -> candidate skill folder,
5. replay gate -> final rejection decision.

But it also confirms the current research limitation again:

- a candidate can be generated,
- yet still produce no measurable answer improvement,
- so the gate correctly rejects publication.

Evidence files:

- `runtime/imports/remote_vm/firmware2-wireless-live-20260811h/firmware2-wireless-live-20260811h-final-enriched.json`
- `runtime/evolve/skill_feedback_bundle.json`
- `skillspace/share/default/candidate_skills/20260811151108-embedded-cgi-command-injection-triage-55516b78/SKILL.md`
- `skillspace/share/default/gate_decisions/20260811151108-embedded-cgi-command-injection-triage-55516b78.json`
- `skillspace/share/default/gate_results/20260811151108-embedded-cgi-command-injection-triage-55516b78/Fan.json`

### 6.1.4 New 2026-08-12 blank-skill / weak-skill control follow-up

Two real remote firmware runs were completed on August 12, 2026 to answer a narrower engineering question:

- is the validated handoff path really usable when the run selects no skills at all?
- if we inject a deliberately weak firmware skill, does the loop still produce a candidate and drive it through client-side replay gate validation?

The two key runs are:

1. blank-skill control
   - run id:
     - `firmware2-wireless-none-20260812c`
   - final record:
     - `runtime/imports/remote_vm/firmware2-wireless-none-20260812c/firmware2-wireless-none-20260812c-final-enriched.json`
   - observed facts:
     - `selected_skill_names = []`
     - `skill_relevance.status = no_selected_skills`
     - `evolution_handoff.status = handed_off`
     - `evolution_handoff.feedback.attribution_status = no_selected_skills_control`
     - `evolution_handoff.consumption_receipt.status = consumed`
     - `evolution_handoff.next_stage = no_candidate`
   - meaning:
     - a no-skill control run no longer crashes or gets dropped before Evolve;
     - it now enters the same validated handoff path as normal runs, but correctly produces no candidate.

2. weak-skill control
   - run id:
     - `firmware2-wireless-seed-20260812a`
   - final record:
     - `runtime/imports/remote_vm/firmware2-wireless-seed-20260812a/firmware2-wireless-seed-20260812a-final-enriched.json`
   - observed facts:
     - `selected_skill_names = ["embedded-cgi-command-injection-triage"]`
     - `skill_relevance.status = has_task_relevant_skill`
     - `evolution_handoff.status = handed_off`
     - `evolution_handoff.consumption_receipt.status = consumed`
     - `evolution_handoff.next_stage = candidate_validation`
     - one candidate was queued and then rejected by client replay gate:
       - `skillspace/share/default/gate_decisions/20260812045011-embedded-cgi-command-injection-triage-7c320ce2.json`
       - `skillspace/share/default/gate_results/20260812045011-embedded-cgi-command-injection-triage-7c320ce2/Fan.json`
   - replay result:
     - `candidate_mean_score = 1.0`
     - `baseline_mean_score = 1.0`
     - rejection reason explicitly requires strict improvement over baseline
   - meaning:
     - the weak-skill run does not prove improvement,
     - but it does prove that the real firmware path now reaches:
       - remote run
       - local session capture
       - validated handoff
       - candidate generation
       - client replay validation
       - final gate rejection

This is the most important engineering interpretation as of August 12:

1. the firmware loop is no longer blocked on "handoff did not happen",
2. the current blocker has moved to candidate quality / acceptance,
3. blank-skill and weak-skill controls now give a usable baseline for later necessity experiments.

### 6.1.4b New 2026-08-12 wrong-skill / live-skill control follow-up

Two more real remote firmware runs were then completed on August 12, 2026 so that the current evidence set became a full four-way control:

1. wrong-skill control
   - run id:
     - `firmware2-wireless-wrong-20260812h`
   - final record:
     - `runtime/imports/remote_vm/firmware2-wireless-wrong-20260812h/firmware2-wireless-wrong-20260812h-final-enriched.json`
   - observed facts:
     - `selected_skill_names = ["firmware-embedded-lua-shell-extraction"]`
     - `skill_relevance.status = no_task_relevant_skill`
     - `evolution_handoff.status = handed_off`
     - `evolution_handoff.consumption_receipt.status = consumed`
     - `evolution_handoff.next_stage = candidate_validation`
     - one candidate was queued and then rejected by client replay gate:
       - `skillspace/share/default/gate_decisions/20260812055115-firmware-embedded-lua-shell-extraction-213c18d3.json`
       - `skillspace/share/default/gate_results/20260812055115-firmware-embedded-lua-shell-extraction-213c18d3/Fan.json`
   - meaning:
     - even an obviously mismatched skill can still reach candidate generation under the current flow,
     - so "candidate generated" must not be treated as evidence that the chosen skill was useful.

2. current-live-skill control
   - run id:
     - `firmware2-wireless-live-20260812i`
   - final record:
     - `runtime/imports/remote_vm/firmware2-wireless-live-20260812i/firmware2-wireless-live-20260812i-final-enriched.json`
   - observed facts:
     - `selected_skill_names = ["embedded-cgi-command-injection-triage"]`
     - `skill_relevance.status = has_task_relevant_skill`
     - `evolution_handoff.status = handed_off`
     - `evolution_handoff.consumption_receipt.status = consumed`
     - `evolution_handoff.next_stage = no_candidate`
   - meaning:
     - the current live firmware skill is genuinely being injected, recorded, and consumed by Evolve,
     - but that still does not guarantee candidate generation or measurable improvement.

So the current real four-way evidence set is now:

1. no skill:
   - `firmware2-wireless-none-20260812c`
2. weak seed skill:
   - `firmware2-wireless-seed-20260812a`
3. wrong skill:
   - `firmware2-wireless-wrong-20260812h`
4. current live skill:
   - `firmware2-wireless-live-20260812i`

The most important research conclusion after all four runs is:

1. the remote blind firmware loop is real,
2. selected skill recording is real,
3. handoff into Evolve is real,
4. replay gate validation is real,
5. but positive skill gain is still not established,
6. and skill necessity is still not established.

### 6.1.5 Why `validated_pair_queue.closed_sessions_waiting_feedback` still showed `2`

After the August 12 follow-up, `GET /status` on Evolve still showed:

- `closed_sessions_waiting_feedback = 2`
- `stale_closed_sessions_without_feedback = 24`

This looked suspicious, but the concrete records show the two waiting sessions are historical no-skill runs created before the no-skill handoff fix:

- `firmware2-wireless-none-20260812a`
  - client/session id:
    - `55d9d14d-3234-5952-8947-f2aa08f5da85`
  - segment id:
    - `b5684e91-b53d-4c81-b191-097cda93bd86`
- `firmware2-wireless-none-20260812b`
  - client/session id:
    - `1f359299-3e40-5b67-b4ea-21368e6dec5f`
  - segment id:
    - `a3b6b98d-799b-414a-b1c2-44a66ad9ed98`

These segment ids still exist under:

- `skillspace/share/default/sessions/`

but they do not have matching run-feedback envelopes under:

- `skillspace/share/default/run_feedback/`

So the current reading is:

1. the `2` waiting sessions are not evidence that the new `20260812c` no-skill control failed,
2. they are legacy unmatched sessions from before the no-skill control handoff fix,
3. the new no-skill control path no longer leaves fresh runs in that broken state.

### 6.1.6 2026-08-12 service-start incident was not a code regression

One local restart attempt on August 11/12 failed with:

- `WinError 10048`
- address already in use on `0.0.0.0:8787`

This was not a logic bug in the new evolve flow. It was a duplicate local `evolve_server` instance attempting to bind the same port while an older process was still listening.

Current verified listener state after cleanup:

- SkillClaw proxy:
  - `127.0.0.1:30000`
- Evolve server:
  - `0.0.0.0:8787`
- Dashboard:
  - `127.0.0.1:3788`

So later agents should treat that incident as a process-management issue, not as evidence that the recent handoff changes broke startup.
