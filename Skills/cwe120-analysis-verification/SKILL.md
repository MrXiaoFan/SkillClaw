---
name: cwe120-analysis-verification
description: "Use when verifying CWE-120 buffer-overflow findings in ELF binaries. Guides confirmation of dangerous PLT calls, mitigation checks (PIE/Canary/FORTIFY), and exploitability assessment at specific call sites. NOT for: initial source-code scans or non-ELF formats."
category: vulnerability-research
---

# CWE-120 Analysis Verification

Verify buffer-overflow (CWE-120) findings in ELF binaries by confirming dangerous function usage in `.text`, assessing mitigations (PIE, Canary, FORTIFY), and evaluating exploitability at specific call sites.

## Phase 1: Reconnaissance & Mitigation Check
bash
readelf -h "$BINARY" | grep -E "Type:|Machine:"
readelf -l "$BINARY" | grep -E "GNU_STACK|GNU_RELRO"
readelf -s "$BINARY" | grep -E "__stack_chk_fail|__libc_start_main"
readelf --relocs "$BINARY" | grep -E "strcpy|strcat|sprintf|memcpy|gets|fgets"


## Phase 2: Dangerous Call-Site Enumeration
**Do not rely solely on custom Capstone scripts to parse section headers and disassemble `.text`.** Manual ELF parsing is fragile; prefer `objdump`/`readelf` for robust analysis.

**PIE Binary Calling Convention:** Modern PIE binaries typically use `E8 xx xx xx xx` (relative `CALL`) to reach PLT stubs. Do not only scan for `FF 15` (RIP-relative indirect calls through GOT). Both patterns may appear.

Enumerate dangerous calls in `.text`:
bash
objdump -dr -j .text "$BINARY" | grep -E "call.*<(strcpy|strcat|sprintf|gets|fgets|memcpy)@plt>"


If programmatic extraction is required, parse `objdump` output rather than raw Capstone:
python
import subprocess, re
out = subprocess.run(["objdump", "-dr", "-j", ".text", binary], capture_output=True, text=True).stdout
for line in out.splitlines():
    if "call" in line and any(f in line for f in ["strcpy", "strcat", "sprintf", "gets", "fgets", "memcpy"]):
        print(line)


## Phase 3: Context & Control-Flow Analysis
Extract 20-30 instructions around each dangerous call to assess buffer allocation and input control:
bash
objdump -d -j .text --start-address=0xSTART --stop-address=0xSTOP "$BINARY"


Key indicators:
- Buffer size from `sub $IMM,%rsp` or `mov $IMM,%REG`
- Source register/operand origin (socket read, file read, argv, etc.)
- Presence of length checks (`cmp`, `test`, `jbe`) before the call

## Phase 4: Evidence Verification
A finding is valid only if all below are true:
1. **Present in `.text`:** The dangerous function is called in an executable section, not merely listed in GOT/JUMP_SLOT relocations.
2. **No FORTIFY:** The binary uses raw `strcpy`/`sprintf`/etc., not `__strcpy_chk` variants.
3. **Reachable:** The containing function is called from `main`, a network handler, or another entry point reachable by an attacker.
4. **Unbounded:** At least one call site lacks an explicit length constraint before the dangerous function.

## Reporting
Document each verified finding with:
- Binary path, architecture, base address
- Exact call-site virtual address and PLT target
- Disassembly snippet showing buffer setup and source control
- Mitigation status summary
- Feasibility assessment (exploitable / needs trigger / informational)

