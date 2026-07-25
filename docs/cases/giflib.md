# giflib Current

- Target: `giflib-5.1.2 / CVE-2016-3977`
- Ground truth: `util/gif2rgb.c / DumpScreen2RGB`
- Current status: confirmed dynamic-validation case

## Current result

- SkillClaw run: `10/10`
- Direct baseline run: `8/10`
- Main difference: both localized the bug, but the direct run missed exact CVE
  calibration while SkillClaw hit the correct CVE and source-level evidence.

## Confirmation evidence

- A generated malformed GIF drives `gif2rgb_asan` into a real
  `heap-buffer-overflow`.
- The stack hits `DumpScreen2RGB` and matches the expected background-color
  index / color-map OOB path.
- This case is therefore beyond text-only validation and already has runnable
  dynamic confirmation.

## Reporting use

This is currently one of the cleanest end-to-end confirmation cases for the
 framework: prompt -> localization -> scoring -> dynamic confirmation.
