---
name: firmware-cwe120-result-lookup
description: "When asked about analysis status or findings for a binary inside an extracted firmware rootfs (e.g., paths under ./extracted/analysis_fs/), query the persisted Phase 1 and IDA scan JSON artifacts before claiming the file is inaccessible or unanalyzed. NOT for: requesting new scans, analyzing binaries outside a firmware extraction context, or general conversation."
category: general
---

When a user asks whether a specific binary in a firmware extraction has been analyzed, or wants its CWE-120 findings, assume local scan artifacts exist and query them immediately.

1. **Resolve the canonical path.** A binary may be referenced via a symlink or hardlink (e.g., `./extracted/analysis_fs/bin/x11vnc` vs `./extracted/analysis_fs/usr/bin/x11vnc`). Check inode equality or use `readlink -f` to find the path that was actually scanned.
   bash
   stat -c "%i %n" <path1> <path2>
   

2. **Query Phase 1 scan summary.** Load `phase1_cwe120_scan.json` and match the resolved relative path (e.g., `extracted/analysis_fs/usr/bin/x11vnc`). Extract:
   - `risk_score`, `risk_level`
   - `protections` (PIE, canary, fortify)
   - `functions` summary (raw vs fortified sink counts)

3. **Query IDA deep-scan results.** Load `cwe120_all_ida_results_merged.json` and match by `relative_path`. Extract:
   - `analysis_time_sec`, `total_findings`
   - `critical_no_guard` findings (sink type, address, function, disassembly, pcode context)
   - Prioritize `strcpy` and `strcat` calls in `main` or top-level functions for immediate attention.

4. **Synthesize and report.** Present findings in a concise table. If the binary is not found in either artifact, only then proceed with new analysis or inform the user that no prior scan exists.

Do not claim you cannot access the local file system when these JSON artifacts are present in the working directory.
