---
name: elf-cwe120-plt-analysis
description: "Identify unfortified CWE-120 dangerous calls in stripped x86-64 ELF binaries by correlating PLT relocations with Capstone disassembly. Use when objdump shows raw call addresses instead of @plt names, especially on modern binaries using .plt.sec instead of .got.plt. NOT for: Go/Rust binaries with non-C memory models, source-level analysis, or when IDA Pro decompilation is already available and working."
category: general
---

# ELF CWE-120 PLT/Capstone Analysis for Stripped Binaries

## 1. PLT Reconnaissance
Check relocations for dangerous vs fortified functions:
bash
readelf -r <binary> | grep -E "strcpy|strcat|memcpy|sprintf|gets|fgets"

- **Raw**: `strcpy@GLIBC`, `memcpy@GLIBC` → flag for deep inspection.
- **Fortified**: `__strcpy_chk@GLIBC`, `__memcpy_chk@GLIBC` → hardened.
- If a binary contains both, it has partial FORTIFY coverage.

## 2. PLT Stub Addresses
Dump PLT stubs. Modern binaries may use `.plt.sec` instead of `.plt`:
bash
objdump -d -j .plt <binary>
objdump -d -j .plt.sec <binary>

Record stub addresses. In stripped output, names may still appear in the PLT section if relocation info exists.

## 3. Resolve Calls in Stripped Code
When `objdump -d` shows `call 0xcc10` without names, use Capstone to match call targets to PLT stubs:

python
from capstone import *
import struct

def load_elf_sections(path):
    with open(path, 'rb') as f:
        data = f.read()
    shoff = struct.unpack('<Q', data[40:48])[0]
    shent = struct.unpack('<H', data[58:60])[0]
    shnum = struct.unpack('<H', data[60:62])[0]
    shstr = struct.unpack('<H', data[62:64])[0]
    # parse section headers, return dict name->(addr, off, size)
    ...

# Map PLT stub index -> symbol name via .rela.plt and .dynsym/.dynstr
# Disassemble .text; for each CALL, if target matches a dangerous PLT stub, record address.


Key ELF64 parsing facts:
- `.rela.plt` entry size = 24 bytes. Symbol index = `r_info >> 32`.
- `.dynsym` entry size = 24 bytes. `st_name` offsets into `.dynstr`.

## 4. Prioritize Call Sites
For each raw dangerous call, inspect the preceding 64–128 bytes:
- **HIGH priority**: No `cmp`/`test`/`jbe` length checks; source register appears attacker-controlled (e.g., buffer from `fgets` passed to `strcpy`).
- **MEDIUM**: Checks exist but buffer bounds remain ambiguous.
- **LOW**: Fortified `__*_chk` or bounded operations like `snprintf`.

## 5. Exclusions
- Skip Go binaries (identifiable by `.go.buildinfo` or `.gopclntab` sections).
- If a binary is >100 MB and causes OOM, fall back to `objdump -d | grep -E 'call.*0x'` combined with PLT address ranges rather than loading the entire file into Capstone.
