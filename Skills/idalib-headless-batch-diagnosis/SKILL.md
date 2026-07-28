---
name: idalib-headless-batch-diagnosis
description: "Operational debugging procedures for headless IDA Pro 9.x batch analysis via idalib/idapro when output is empty, silent, or ambiguous. Covers license verification, exit-code checking, and raw log inspection before applying grep/tail filters. NOT for interactive GUI analysis, non-batch single-binary sessions where output is already confirmed, or any task not involving headless IDA batch execution anomalies."
category: general
---

## Headless IDA Batch Execution Diagnostics

When running automated batch analysis with IDA Pro 9.x idalib, empty or missing output is ambiguous: it may indicate no findings, a Python exception, or a silent IDA license/initialization failure.

### Execution Rules
1. **Always run unfiltered first.** Execute the batch command without `grep`, `tail`, or stdout redirection to preserve stderr and exception traces. Capture both stdout and stderr: `cmd 2>&1 | tee /tmp/ida_batch_raw.log`.
2. **Check the exit code immediately.** After the command, run `echo $?`. Non-zero exits indicate crashes or unhandled exceptions even if filtered output looks empty.
3. **Smoke-test IDA headless before batch runs.** Verify the environment with a minimal one-off Python script that imports the IDA bundled package (e.g., `idapro`/`idalib`), attempts to load a small ELF database headlessly, and exits cleanly. If this fails, the batch will fail silently.

### Common Silent Failure Modes
- **License checkout failure:** IDA headless still requires a valid license. Errors appear in stderr as `License: ...` or silent exit.
- **Missing display/Xvfb:** Some IDA builds need `DISPLAY` or `xvfb-run` even in headless mode.
- **Wrong idapro wheel:** Using PyPI/GitHub idalib instead of `<ida_dir>/idalib/python/idapro-<ver>-py3-none-any.whl` causes import or API mismatches.
- **Database lock/timeout:** Concurrent IDA processes may stall on license or database locks.

### Recovery Steps
If batch output is empty and exit code is non-zero or suspicious:
- Run the batch script on a single known-good binary with full verbosity.
- Inspect `/tmp/ida_batch_raw.log` for Python tracebacks or IDA license messages.
- Verify the idapro wheel path matches the installed IDA version.
- Ensure the batch script handles `idalib`/`idapro` initialization exceptions and prints them rather than swallowing them.
