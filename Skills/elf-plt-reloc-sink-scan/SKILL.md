---
name: elf-plt-reloc-sink-scan
description: "Use `readelf -r` relocation entries (R_X86_64_JUMP_SLOT) instead of `--dyn-syms` to detect imported CWE-120 sink functions in stripped ELF binaries during firmware triage. NOT for: analyzing exported symbols, non-ELF formats, or source-level debug builds where symbol tables are intact."
category: general
---

When scanning ELF binaries for imported CWE-120 sink functions, always use the relocation table (`readelf -r`) rather than the dynamic symbol table (`readelf --dyn-syms`).

## Why `--dyn-syms` fails
- `readelf --dyn-syms` lists symbols present in `.dynsym`, which includes both imports **and** exports (e.g., libc re-exporting `read`).
- On stripped binaries it can show symbols that are not actually called via PLT, producing false positives.
- It cannot reliably pair raw sinks with their FORTIFY `__*_chk` counterparts because exported `__memcpy_chk` from libc may appear even when the binary does not import it.

## Why `-r` is correct
- `readelf -r` enumerates dynamic relocations (e.g., `R_X86_64_JUMP_SLOT`).
- These entries correspond exactly to PLT slots the binary uses to call external functions.
- Stripped binaries retain relocations because the dynamic linker needs them at runtime.

## Concrete commands
bash
# List imported raw sinks (Category A/B/C)
readelf -r "$binary" | grep -E "(strcpy|strcat|memcpy|fgets|read|recv|recvfrom|fread|pread|sprintf|scanf|gets)@"

# Detect FORTIFY hardened variants
readelf -r "$binary" | grep -E "__(strcpy|strcat|memcpy|snprintf|sprintf|scanf|gets)_chk@"


## FORTIFY scoring rule
If a binary shows `strcpy@GLIBC` in relocations but **no** `__strcpy_chk@GLIBC`, the binary uses the unprotected raw sink. If both appear, FORTIFY is active for that sink.

## Important glibc caveat
Category C sinks (`read`, `recv`, `recvfrom`, `fread`, `pread`) generally **do not have** FORTIFY wrappers in glibc. Expect zero `__read_chk` or `__recv_chk` relocations even in hardened builds; absence of `_chk` for these sinks is normal and not a false negative.
