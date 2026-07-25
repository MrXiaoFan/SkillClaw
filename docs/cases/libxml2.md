# libxml2 Current

- Target: `libxml2-2.9.4 / CVE-2017-8872`
- Ground truth: `HTMLparser.c / htmlParseTryOrFinish`
- Current status: localization case is stable; dynamic confirmation is still
  weaker than giflib/tcpdump confirmation cases

## Current result

- SkillClaw high-quality run localized the right file, function, and guard-style
  evidence, but CVE identity drifted.
- Direct baseline could hit the CVE name, but often gave weaker function-level
  localization and weaker code evidence.

## What this case supports

- It is a strong example for separating:
  - vulnerability localization quality
  - CVE identity calibration quality
- It also supports the claim that a task-aligned parser skill can improve
  source-level reasoning even when final CVE naming is imperfect.

## Current limitation

This case is still more valuable as a localization/comparison case than as a
fully closed dynamic-confirmation benchmark.

