---
name: elf-cwe120-firmware-triage
description: "Use when analyzing extracted Linux firmware or rootfs ELF binaries for CWE-120 buffer-overflow vulnerabilities. Prevents duplicate scanning across symlinked directories like `bin/` → `usr/bin/` and suppresses false-positive floods from memcpy-only or coreutils binaries. NOT for: Windows PE malware analysis, source-code audits, or general memory-safety reviews where build flags are known."
category: general
---

When triaging extracted firmware/rootfs ELF binaries for CWE-120 (buffer overflow), follow this prioritization to avoid false-positive avalanches and redundant work:

1. **Check for symlink duplication first**
   Before deep-scanning `./extracted/analysis_fs/bin`, verify if it is a symlink to `usr/bin/`:
   bash
   ls -la ./extracted/analysis_fs/bin
   readlink ./extracted/analysis_fs/bin
   
   If it resolves to `usr/bin`, reuse existing `usr/bin` scan results instead of treating it as a separate corpus.

2. **Prioritize true CWE-120 sinks**
   Rank raw (unfortified) function indicators by severity:
   - **High signal**: `strcpy`, `strcat`, `sprintf`, `gets` — these almost always indicate missing bounds checking.
   - **Low signal**: `memcpy` — requires proof that the destination size or source length is attacker-controlled. Do not flag `memcpy`-only binaries as "high priority" without call-site context.

3. **Filter out benign missing mitigations**
   GNU coreutils and standard system utilities frequently ship with `CANARY=0` and `FORTIFY=0` by design. Treat these as low risk unless the binary also meets one of the following:
   - Has `setuid`/`setgid` bits
   - Listens on network interfaces or handles remote data (e.g., `ssh-agent`, `x11vnc`, `tcpdump`)
   - Parses complex attacker-controlled file formats (e.g., `unzip`, `unzipsfx`)

4. **Quick triage command**
   After initial `readelf`/`objdump` scans, filter the candidate list with:
   bash
   # True high-value targets: raw string-copy funcs + no canary + no FORTIFY
   grep -E "strcpy|strcat|sprintf|gets" ./cwe120_results/phase1/*.txt | grep "CANARY=0" | grep -v "FORTIFY=YES"
   
   Only escalate binaries matching these criteria to deep disassembly and PLT/GOT analysis.

5. **Map the sink to the exact network handler**
   For an embedded web-service binary, a `strcpy`/`sprintf` hit is only a candidate, not the
   final finding. Enumerate nearby CGI/form handler symbols and use disassembly or cross-reference
   evidence to connect the user-controlled parameter to the specific call site and destination
   buffer. Report the exact handler, parameter, sink, and destination together; do not substitute a
   different handler merely because it is in the same binary or appears near the same string table.
   Keep command-execution sinks (`system`, `popen`, `execl`) separate from CWE-120 findings unless
   the same call path independently proves both vulnerability mechanisms.

6. **Require a reproducible identity bundle**
   Before naming a CVE or claiming a target function, record at least two independent identity
   signals: the handler/function symbol or decompiled label, the input parameter, and the unsafe
   call or destination buffer. If only a generic sink is visible, report the finding as a candidate
   and continue localizing instead of promoting a nearby handler or known CVE.
