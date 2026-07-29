# Remote VM Live Log

## 2026-07-25

This file records remote VM synchronization and test operations, including
executed commands and key outputs.

### 1. SSH connectivity

Command:

```powershell
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "hostname; whoami; pwd"
```

Output:

```text
li-virtual-machine
li
/home/li
```

### 2. Remote repo status before sync

Command:

```powershell
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "cd ~/skillclaw-eval/SkillClaw && git branch --show-current && git status --short && git remote -v"
```

Key result:

- Remote repo was still on the old `experiment_*` layout.
- Remote working tree was already dirty.

### 3. Sync local refactor to remote VM

Local archive:

```text
C:\Users\Fan\AppData\Local\Temp\skillclaw-sync-20260725.tar.gz
```

Commands:

```powershell
scp -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes "C:\Users\Fan\AppData\Local\Temp\skillclaw-sync-20260725.tar.gz" li@192.168.1.4:~/skillclaw-eval/skillclaw-sync-20260725.tar.gz
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "cd ~/skillclaw-eval && tar -czf backups/SkillClaw_repo_.tar.gz SkillClaw && cd SkillClaw && find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} + && tar -xzf ../skillclaw-sync-20260725.tar.gz -C ."
```

Key result:

- Remote tree now contains the new layout:
  - `benchmarks/`
  - `docs/`
  - `evaluation/`
  - `reports/`
  - `runtime/`
  - `scripts/`

Note:

- Backup succeeded, but the timestamp fragment in the backup filename was eaten by local PowerShell interpolation, so the actual backup file became:

```text
/home/li/skillclaw-eval/backups/SkillClaw_repo_.tar.gz
```

### 4. Remote preflight for giflib case

Command:

```powershell
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "cd ~/skillclaw-eval/SkillClaw && python3 -m evaluation.utils.check_case_runtime benchmarks/cases/giflib-5.1.2-cve-2016-3977.json --json"
```

Key result:

- `status: passed`
- `source_root`: `/home/li/skillclaw-eval/giflib-5.1.2`
- `target_binary`: `/home/li/skillclaw-eval/giflib-5.1.2/util/gif2rgb`
- Remote Claude config provider: `skillclaw`

### 5. Remote blind workspace preparation

Command:

```powershell
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "cd ~/skillclaw-eval/SkillClaw && python3 -m evaluation.utils.prepare_blind_workspace benchmarks/cases/giflib-5.1.2-cve-2016-3977.json"
```

Key result:

- Blind workspace:

```text
/home/li/skillclaw-eval/blind_workspaces/giflib-5.1.2-cve-2016-3977
```

- Neutral sample generated:

```text
samples/sample_1.gif
```

### 6. Remote blind prompt rendering

Command:

```powershell
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "cd ~/skillclaw-eval/SkillClaw && python3 -m evaluation.utils.render_case_prompt benchmarks/cases/giflib-5.1.2-cve-2016-3977.json --mode recommended_blind_skillclaw > ~/skillclaw-eval/manual_runs/giflib_blind/prompt.txt"
```

Generated prompt:

```text
/home/li/skillclaw-eval/manual_runs/giflib_blind/prompt.txt
```

### 7. Remote manual Claude blind run

Command logic:

- Run `claude -p --dangerously-skip-permissions --output-format text`
- Feed `prompt.txt` from the remote VM
- Save output as a timestamped raw file

Final saved raw output:

```text
/home/li/skillclaw-eval/manual_runs/giflib_blind/raw_20260725-154638.txt
```

Key result:

- Claude identified:
  - `CVE-2016-3977`
  - file `util/gif2rgb.c`
  - function `DumpScreen2RGB`
- Claude also mentioned upstream helper path `lib/dgif_lib.c`

### 8. First remote full validation result

Initial finding:

- Full validator failed even though the blind analysis was good.
- Root cause was not the model output.
- Root cause was a path bug in validator / case command wiring:

```text
python3: can't open file '/home/li/skillclaw-eval/giflib-5.1.2/../benchmarks/confirmations/giflib-5.1.2-cve-2016-3977/generate_confirmation_input.py'
```

This showed that remote-first validation was still relying on brittle `../benchmarks/...` assumptions.

### 9. Fix applied after remote test

Changes made locally, then incrementally synced back to VM:

- `evaluation/validation/checks.py`
  - inject `SKILLCLAW_REPO_ROOT`, `SKILLCLAW_CASE_PATH`, `SKILLCLAW_CASE_DIR`, `SKILLCLAW_TARGET_ROOT` into validator subprocess environments
- `benchmarks/cases/*.json`
  - replace brittle `../benchmarks/...` calls with `$SKILLCLAW_REPO_ROOT/benchmarks/...`
- `benchmarks/confirmations/exiv2-0.26-cve-2017-17725/prepare_confirmation_artifacts.sh`
  - make generated wrapper source helpers from `SKILLCLAW_REPO_ROOT`
- `benchmarks/confirmations/libxml2-2.9.4-cve-2017-8872/*.sh`
  - make confirmation harness / wrapper resolve repo scripts robustly

### 10. Remote giflib full validation after fix

Command:

```powershell
ssh -i $HOME\.ssh\skillclaw_vm -o IdentitiesOnly=yes li@192.168.1.4 "python3 -m evaluation.runs.run_case_validation ~/skillclaw-eval/SkillClaw/benchmarks/cases/giflib-5.1.2-cve-2016-3977.json --agent-output ~/skillclaw-eval/manual_runs/giflib_blind/raw_20260725-154638.txt"
```

Result:

```text
status: passed
```

Important passed checks:

- `ground-truth-source-location`
- `gif2rgb-binary-present`
- `generated-poc-input-exists`
- `generated-poc-input-executes`
- `asan-poc-cve-2016-3977`

### 11. Saved remote artifacts for this run

Prompt:

```text
/home/li/skillclaw-eval/manual_runs/giflib_blind/prompt.txt
```

Raw blind output:

```text
/home/li/skillclaw-eval/manual_runs/giflib_blind/raw_20260725-154638.txt
```

Saved score output:

```text
/home/li/skillclaw-eval/manual_runs/giflib_blind/score_remote_blind_20260725.json
```

Saved validation output:

```text
/home/li/skillclaw-eval/manual_runs/giflib_blind/validation_remote_blind_20260725.json
```

### 12. Current conclusion

- Remote-first blind analysis for `giflib-5.1.2 / CVE-2016-3977` is now runnable.
- Remote manual Claude run succeeded.
- Remote validator full chain now passes after fixing repo-path wiring.
- Automatic injection of this run into the current local `reports/current/skill_feedback_bundle.json` and evolve flow is not yet demonstrated by this manual path.
- So the current engineering state is:
  - `analysis -> validation` is now working on remote VM for this case
  - `validation -> evolve feedback publish` still needs an explicit connected run record path

## 2026-07-29: validated evolution handoff deployment

### 13. Remote repository inspection

Command executed from Windows:

```powershell
ssh -i C:\Users\Fan\.ssh\skillclaw_vm -o BatchMode=yes li@192.168.1.4 "cd /home/li/skillclaw-eval/SkillClaw && git status --short && git branch --show-current && git rev-parse --short HEAD && git remote -v"
```

Result:

```text
branch: dev
commit: ba05afe
remote: origin -> https://github.com/MrXiaoFan/SkillClaw.git
working tree: previous evaluation/ and benchmarks/ sync files were modified; one confirmation adapter was untracked
```

The modified files were not deleted or overwritten.

### 14. Preserve remote changes and fast-forward to the shared dev commit

Command executed from Windows:

```powershell
ssh -i C:\Users\Fan\.ssh\skillclaw_vm -o BatchMode=yes li@192.168.1.4 "cd /home/li/skillclaw-eval/SkillClaw && git stash push -u -m 'pre-sync-20260729' && git pull --ff-only origin dev && git rev-parse --short HEAD && git status --short && git stash list | head -n 3"
```

Result:

```text
Saved working directory and index state On dev: pre-sync-20260729
Updating ba05afe..9adc039
Fast-forward
54 files changed, 3579 insertions(+), 800 deletions(-)
commit: 9adc039
working tree: clean
stash@{0}: On dev: pre-sync-20260729
```

The VM, Codeup `dev`, GitHub `dev`, and the local repository now use commit `9adc039`.
