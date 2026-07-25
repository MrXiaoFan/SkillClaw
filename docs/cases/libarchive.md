# libarchive Current

- Target: `libarchive-3.8.0 / CVE-2025-60753`
- Ground truth: `tar/subst.c / apply_substitution`
- Current status: stable behavior-backed confirmation case

## Current result

- The generated rule and wrapper reliably reproduce the empty global substitution
  no-progress loop under a short timeout.
- The main confirmation markers are:
  - `TIMEOUT_CONFIRM_OK libarchive-empty-global-substitution`
  - `expected_rc=124`
  - `out_tar_size=0`

## What this case adds

- It broadens the benchmark beyond parser and memory-safety cases.
- It is the cleanest current example of a non-crashing, utility-level
  denial-of-service confirmation path.

## Reporting use

This case is suitable for current benchmark reporting as long as its evidence
label is kept explicit as behavior-backed rather than sanitizer-backed.
