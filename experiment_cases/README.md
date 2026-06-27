# SkillClaw Case-Level Validation MVP

This directory contains small benchmark cases for checking whether a SkillClaw
skill actually improves vulnerability localization.

## Validator Framework Roles

The MVP now has a small validator framework:

- `ValidationContext`: passes the case, target root, optional agent output, and execution flags to validators.
- `ValidatorRegistry`: maps validator types to implementations.
- `content_match`: checks the final agent answer for ground-truth CVE/file/function/evidence.
- `source_contains`: checks source files for required symbols or guard patterns.
- `command`: runs a normal shell command.
- `asan_command`: runs PoC/ASan/UBSan dynamic execution. For vulnerable
  builds, a non-zero exit can be `passed` when sanitizer/crash markers and the
  expected source file/function appear in output.
- `bundle_script`: runs a script shipped with a skill bundle.
- `build_feedback`: converts score + validation + injected skills into positive/neutral/negative feedback.

This separates the roles:

1. The LLM/Agent proposes a vulnerability location.
2. The validators collect evidence with different tools.
3. The feedback layer decides whether the skill helped, hurt, or needs more cases.

The workflow is intentionally minimal:

1. Run Claude Code in one of the experiment modes.
2. Ask the model to output JSON with predicted CVE/file/function/root cause.
3. Score that JSON against the case ground truth.
4. Run case-level validators to attach source, binary, PoC, or ASan evidence.
5. Extract SkillClaw server-side injection metadata from `records/conversations.jsonl`.

## Local Smoke Test

Before running a remote VM experiment, verify that the repository-local case
files, bundle scripts, and validator registry still work:

```bash
python experiment_scripts/smoke_validate_framework.py
```

Expected output:

```text
libxml2-2.9.4-cve-2017-8872: passed
tcpdump-4.9.1-cve-2017-13031: passed
```

This command does not call an LLM and does not require the real vulnerable
source trees. It creates tiny synthetic fixtures and only checks that the
validation framework itself is intact.

## Remote VM Usage

First check that the VM, target tree, Claude Code configuration, and SkillClaw
proxy are consistent:

```bash
python3 experiment_scripts/check_experiment_env.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  --root ~/skillclaw-eval/libxml2-2.9.4 \
  --expected-provider skillclaw \
  --skillclaw-url http://10.12.189.47:30000 \
  --skillclaw-key sk-skillclaw-lab \
  --expected-skill-count 35
```

For a direct DeepSeek baseline, switch Claude Code to the direct key first and
run the same check with:

```bash
python3 experiment_scripts/check_experiment_env.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  --root ~/skillclaw-eval/libxml2-2.9.4 \
  --expected-provider deepseek
```

From the target project directory on the remote VM:

```bash
cd ~/skillclaw-eval/libxml2-2.9.4
claude --dangerously-skip-permissions
```

Print the prompt from the case file:

```bash
python3 experiment_scripts/print_case_prompt.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  --mode skillclaw-inline
```

Paste that prompt into Claude Code, then save the final JSON answer:

```bash
mkdir -p ~/skillclaw-eval/results
nano ~/skillclaw-eval/results/libxml2-skillclaw-output.json
```

Copy the `experiment_cases` and `experiment_scripts` directories to the VM, or
run the scripts from a checkout of this repository.

Score the answer:

```bash
python3 experiment_scripts/score_agent_output.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  ~/skillclaw-eval/results/libxml2-skillclaw-output.json \
  --mode skillclaw-inline \
  --result-out ~/skillclaw-eval/results/dynamic_results.jsonl
```

Run the semi-dynamic validators:

```bash
python3 experiment_scripts/run_dynamic_case.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  --root ~/skillclaw-eval/libxml2-2.9.4 \
  --agent-output ~/skillclaw-eval/results/libxml2-skillclaw-output.json \
  --result-out ~/skillclaw-eval/results/libxml2-validation.jsonl
```

Alternatively, use the integrated runner. It writes the prompt, raw agent
output, score, validation result, preflight report, and final record into one
run directory:

```bash
python3 experiment_scripts/run_eval_case.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  --mode skillclaw-inline-guarded \
  --root ~/skillclaw-eval/libxml2-2.9.4 \
  --output-dir ~/skillclaw-eval/results \
  --preflight \
  --expected-provider skillclaw \
  --skillclaw-url http://10.12.189.47:30000 \
  --skillclaw-key sk-skillclaw-lab \
  --expected-skill-count 35
```

Build one consolidated result record:

```bash
python3 experiment_scripts/build_result_record.py \
  experiment_cases/libxml2-2.9.4-cve-2017-8872.json \
  ~/skillclaw-eval/results/libxml2-skillclaw-output.json \
  --mode skillclaw-inline \
  --model skillclaw-model \
  --validation-json ~/skillclaw-eval/results/libxml2-validation.jsonl \
  --out ~/skillclaw-eval/results/final_records.jsonl
```

The libxml2 case also invokes a bundled checker:

```text
experiment_cases/skill_bundles/source-parser-state-machine-oob/scripts/check_avail_guard.py
```

This is the first executable skill-bundle bridge: the textual skill can point to
a script, and the case validator can run it to attach machine-readable evidence.

If a stable PoC/ASan command is added later, enable the `asan_command`
validator in the case JSON. Use `expect_crash: true` for vulnerable builds and
`expect_crash: false` for fixed/regression builds.

## SkillClaw Injection Audit

On the SkillClaw server machine:

```powershell
.\.venv\Scripts\python.exe experiment_scripts\extract_skill_injection.py `
  records\conversations.jsonl `
  --session-id <SESSION_ID> `
  --jsonl-out experiment_results\skill_injection_audit.jsonl
```

The key fields are:

- `selected_skill_names`
- `injection_mode`
- `skill_prompt_hash`
- `available_skill_count`

These fields should be copied into the final experiment result record.

## Current Cases

- `giflib-5.1.2-cve-2016-3977.json`: lightweight heap-overflow case in
  `gif2rgb`, used to test source-level color-map index validation reasoning.
- `libxml2-2.9.4-cve-2017-8872.json`: main parser state-machine case.
- `tcpdump-4.9.1-cve-2017-13031.json`: targeted IPv6 fragmentation parser case.

The tcpdump and giflib cases are intentionally targeted and should not be used
alone to claim SkillClaw improves broad vulnerability discovery.
