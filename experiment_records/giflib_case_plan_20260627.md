# giflib 5.1.2 / CVE-2016-3977 Case Plan

## Purpose

This is the third lightweight C memory-safety benchmark case for the
SkillClaw-vs-direct-LLM study. It complements the existing `tcpdump` and
`libxml2` cases with a source-level heap-overflow pattern involving a
missing index-range check rather than protocol-parser length checks.

## Ground Truth

- Case id: `giflib-5.1.2-cve-2016-3977`
- Target: `giflib` `5.1.2`
- Utility: `util/gif2rgb`
- Source file: `util/gif2rgb.c`
- Function: `DumpScreen2RGB`
- Vulnerability type: heap-based buffer overflow / out-of-bounds color-map access

The relevant data flow is:

1. `ScreenBuffer[0][i]` is initialized with `GifFile->SBackGroundColor`.
2. Later, `DumpScreen2RGB` reads each pixel index from `GifRow[j]`.
3. The code uses that value as `ColorMap->Colors[GifRow[j]]`.
4. If the GIF background color index is outside the active color map, the
   color lookup can read/write outside the intended color table.

The expected answer should therefore identify the CVE, `util/gif2rgb.c`,
`DumpScreen2RGB`, and the missing validation between `SBackGroundColor` and
`ColorMap->ColorCount`.

## Current Artifacts

Added case file:

```text
experiment_cases/giflib-5.1.2-cve-2016-3977.json
```

The case includes:

- `content_match` validator for final answer scoring.
- `source_contains` validator for the ground-truth source location.
- `command` validator to check that `util/gif2rgb` exists on a real Linux VM.
- disabled `asan_command` placeholder for a future crafted GIF PoC.

The repository smoke test now includes this case. It verifies source-pattern
validation with a synthetic fixture, but it does not prove the real giflib
binary or ASan PoC yet.

## Remote VM Preparation

On the remote VM:

```bash
cd ~/skillclaw-eval
git clone --depth 1 --branch 5.1.2 https://github.com/nesbox/giflib.git giflib-5.1.2
cd giflib-5.1.2
make
file util/gif2rgb
```

Then run the preflight check from a checkout of this repository:

```bash
python3 experiment_scripts/check_experiment_env.py \
  experiment_cases/giflib-5.1.2-cve-2016-3977.json \
  --root ~/skillclaw-eval/giflib-5.1.2 \
  --expected-provider skillclaw \
  --skillclaw-url http://10.12.189.47:30000 \
  --skillclaw-key sk-skillclaw-lab \
  --expected-skill-count 35
```

## Planned Comparison

Run at least two guarded-clean modes:

```text
skillclaw-inline-guarded-clean-budget035
direct-deepseek-guarded-clean-budget035
```

If both fail or both succeed, repeat with a higher budget:

```text
skillclaw-inline-guarded-clean-budget080
direct-deepseek-guarded-clean-budget080
```

The key research question for this case is whether SkillClaw improves
source-level index-validation reasoning, or whether injected skills bias the
model toward unrelated parser/CWE-120 patterns.

## Status

Prepared but not yet executed on the remote VM.
