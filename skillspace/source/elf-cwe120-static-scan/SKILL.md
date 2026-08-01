---
name: elf-cwe120-static-scan
description: "Batch-scan Linux ELF binaries for CWE-120 buffer-overflow candidates using readelf and objdump. Trigger when analyzing firmware images, extracted filesystems, or binary collections for unsafe strcpy/sprintf/gets/memcpy usage without FORTIFY_SOURCE. NOT for: Windows PE analysis, source-code audits, or when IDA Pro/Ghidra decompilation is already available and working."
category: general
---

## ELF CWE-120 Static Scan Pipeline

Use this when tasked with finding buffer-overflow (CWE-120) candidates across a Linux filesystem, firmware image, or binary collection where IDA/Ghidra decompilation is unavailable or impractical.

### Phase 1: Fast Batch Enumeration & Screening

1. **Enumerate ELF executables** (skip libraries unless instructed):
   bash
   find "$TARGET_FS" -type f -executable -exec sh -c 'file "$1" | grep -q ELF && echo "$1"' _ {} \; > /tmp/elf_list.txt
   
   > **Path stability:** Use an absolute path for `$TARGET_FS` so saved lists remain valid if the working directory changes during batch processing.

2. **Scan relocation tables for dangerous functions** via `readelf -r`. Match the **symbol name column** for:
   - Raw: `strcpy@GLIBC`, `sprintf@GLIBC`, `gets@GLIBC`, `strcat@GLIBC`, `memcpy@GLIBC`, `memmove@GLIBC`
   - Fortified: `__strcpy_chk@GLIBC`, `__sprintf_chk@GLIBC`, `__memcpy_chk@GLIBC`, etc.

   > **Note:** `readelf` may truncate the relocation type column (e.g., `R_X86_64_JUMP_SLOT` → `R_X86_64_JUMP_SLO`). Match on `funcname@GLIBC` rather than the relocation type string.

3. **Distinguish raw vs FORTIFY_SOURCE.** If a binary links `strcpy@GLIBC` but **not** `__strcpy_chk@GLIBC`, the `strcpy` calls are raw (unprotected). Record counts per binary as `[raw:N chk:M]`.

4. **Check exploit mitigations:**
   bash
   readelf -s "$binary" | grep -q '__stack_chk_fail' && echo "Canary=yes" || echo "Canary=no"
   readelf --dyn-syms "$binary" | grep -q '__.*_chk' && echo "Fortify=yes" || echo "Fortify=no"
   

> **CRITICAL PITFALL:** `grep gets` matches `fgets`, `sgetspent`, etc. Always use exact symbol matching:
> bash
> readelf -r "$binary" | grep -w '^gets@'
> 
> Cross-check with `strings "$binary" | grep -w '^gets$'` before reporting "raw gets".

### Phase 2: Call-Site Localization (High-Priority Binaries)

Filter to binaries that are **Canary=no** and/or **Fortify=no** with raw dangerous functions.

1. **Find PLT stub addresses** from `readelf -r` (e.g., `strcpy@GLIBC_2.2.5` at `0x13e48`). On modern x86-64 PIE binaries, the executable PLT stubs reside in `.plt.sec` and `objdump` may not annotate them as `@plt`.

2. **Map to call instructions** in `.text`. Do NOT rely solely on `objdump | grep "call.*strcpy@plt"`—modern PIE binaries often omit `@plt` annotations.
   - Use `objdump -d -j .text "$binary"` (limiting to `.text` avoids counting PLT stubs as calls).
   - Search for calls to the `.plt.sec` stub address or the corresponding GOT slot address:
     bash
     objdump -d -j .text "$binary" | grep -E "call.*0x<PLT_STUB_ADDR>"
     
   - If exact address matching is difficult because of RIP-relative encoding, use `objdump -dr -j .text "$binary"` and look for `R_X86_64_PLT32` relocations against the target symbol to identify call sites.

3. **Extract caller context** (20–30 instructions before the `call`) to identify buffer destination (`rdi`) and source (`rsi`) registers for manual taint analysis.

> **Counting pitfall:** `readelf -r` counts PLT slots (usually one per imported function), not dynamic call sites. A binary may import `strcpy` once but call it 50 times. Always count actual `call` instructions in `.text`.

### Risk Sorting

Report findings in this order:
1. **Critical**: No Canary + No Fortify + raw `strcpy` / `sprintf` / `gets`
2. **High**: No Fortify + raw `strcpy` / `memcpy`
3. **Medium**: Canary present but raw `strcpy` / `sprintf`
