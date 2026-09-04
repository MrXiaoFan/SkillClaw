# 02. Engineering Architecture and Workflow

This file is the shortest accurate map from code to workflow.

## A. Main runtime path

### 1. Skill selection and injection

- File: [../../skillclaw/skill_manager.py](../../skillclaw/skill_manager.py)
- Key functions:
  - `format_skills_for_prompt`
  - `build_skills_section`
  - `build_injection_prompt`
- Role:
  - build inline-injected skill text;
  - build catalog-style available-skill text;
  - provide the server-side representation that will be attached to the upstream model
    request.

### 2. Server request handling and session recording

- File: [../../skillclaw/api_server.py](../../skillclaw/api_server.py)
- Relevant behavior:
  - stores conversation records in `runtime/records/conversations.jsonl`
  - records `selected_skill_names`
  - assigns `session_id` and `session_segment_id`
  - supports multiple controlled conditions: server-side lexical inline injection,
    model-side catalog lazy loading, and server-side catalog selection
- Role:
  - receive model traffic;
  - attach skill injection metadata;
  - archive a run so it can later be scored and consumed by evolve.

### 3. Case prompt rendering and blind workspace preparation

- Files:
  - [../../evaluation/utils/render_case_prompt.py](../../evaluation/utils/render_case_prompt.py)
  - [../../evaluation/utils/prepare_blind_workspace.py](../../evaluation/utils/prepare_blind_workspace.py)
- Role:
  - construct the actual blind-analysis task text from a benchmark case definition;
  - create the workspace visible to the remote agent while hiding oracle-only files.

### 4. Run execution

- Files:
  - [../../evaluation/runs/run_remote_case.py](../../evaluation/runs/run_remote_case.py)
  - [../../evaluation/runs/run_single_case.py](../../evaluation/runs/run_single_case.py)
- Role:
  - drive remote or local benchmark execution;
  - collect raw output and structured result files.

### 5. Finalization and scoring

- Files:
  - [../../evaluation/postprocess/finalize_record.py](../../evaluation/postprocess/finalize_record.py)
  - [../../evaluation/runs/score_case_output.py](../../evaluation/runs/score_case_output.py)
- Role:
  - merge raw run output with case metadata and conversation record;
  - score the answer against the benchmark ground truth.

### 6. Oracle-side checking

- Files:
  - [../../evaluation/confirmation/core.py](../../evaluation/confirmation/core.py)
  - [../../evaluation/validation/core.py](../../evaluation/validation/core.py)
- Role:
  - run oracle-side structural or artifact-level checks;
  - produce validator-style evidence for post-run assessment.

### 7. Feedback construction

- File: [../../evaluation/reporting/feedback/build_feedback_bundle.py](../../evaluation/reporting/feedback/build_feedback_bundle.py)
- Role:
  - convert finalized runs into the structured bundle that evolve consumes.

### 8. Candidate generation and validated publish flow

- File: [../../evolve_server/engines/workflow.py](../../evolve_server/engines/workflow.py)
- Relevant methods:
  - `_load_feedback_bundle`
  - `_load_validated_pairs`
  - `_queue_validation_job`
  - `_handle_no_skill_sessions`
- Role:
  - group sessions and feedback;
  - call the LLM to create or evolve candidate skills;
  - decide whether to route a candidate into validated gating rather than direct
    publish.

### 9. Gate and replay/rerun validation

- File: [../../skillclaw/replay_gate_worker.py](../../skillclaw/replay_gate_worker.py)
- Relevant behavior:
  - replay message construction
  - candidate/baseline comparison
  - acceptance modes such as `strict_improvement`
- Role:
  - compare baseline and candidate branches;
  - decide whether a candidate is accepted for live publication.

## B. Skill storage layout

- Live runtime skill library: `skillspace/live/`
- Shared/evolve-side storage: `skillspace/share/`
- Candidate and gate artifacts: under `skillspace/share/default/...`

The physical split exists for a reason:

1. `live/` is what the server injects into future runs;
2. `share/` is where evolve and gate keep candidate/history artifacts;
3. keeping them separate avoids accidentally treating every candidate as a production
   skill.

## C. Benchmark case structure

Each benchmark case typically contains:

- target metadata and remote/local source roots,
- blind workspace rules,
- ground truth,
- validators,
- recommended prompts.

Examples copied into this package are under [cases/](cases/).

## D. Most important current limitation

The chain is real, but the last step still has a research problem:

- a candidate skill can be generated,
- a candidate can even be published,
- but publication is not yet strong evidence that the live library has truly improved
  future blind analysis.

That is why the paper should emphasize publication control and evidence quality, rather
than pretending that the system has already solved autonomous skill improvement.
