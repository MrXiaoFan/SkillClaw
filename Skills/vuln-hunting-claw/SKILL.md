---
name: vuln-hunting-claw
description: "Firmware CWE-120 buffer-overflow hunting workflow for extracted Linux rootfs images. Use when asked to perform static analysis for CWE-120 on firmware filesystems or ELF binary collections, especially when IDA Pro deep analysis is requested. NOT for: Windows PE analysis, source-code audits, or runtime dynamic analysis."
category: firmware-security
---

# vuln-hunting-claw

Firmware CWE-120 buffer-overflow hunting workflow for extracted Linux rootfs images.

## Trigger
Use when asked to perform static analysis for CWE-120 (buffer overflow) on extracted firmware filesystems, embedded Linux rootfs, or collections of ELF binaries, especially when IDA Pro deep analysis is requested. NOT for Windows PE, source-code audits, or runtime dynamic analysis.

## Phase 1: Enumeration & Triage
1. **Filesystem structure**: In most firmware rootfs, `bin/`, `sbin/`, `lib/`, and `lib64/` are symlinks to their counterparts under `usr/`. Only enumerate and scan under `usr/` to avoid duplicate analysis.
2. **ELF enumeration**: Use `find ./extracted/analysis_fs/usr -type f \( -executable -o -name "*.so*" \) -exec sh -c 'file "$1" | grep -q ELF && echo "$1"' _ {} \; > elf_list.txt` to build the target list.
3. **Delegate to sub-skills**: Invoke `elf-cwe120-static-scan` and `elf-cwe120-firmware-triage` for batch readelf/objdump scanning. These skills handle canary detection, FORTIFY checks, and filtering of false-positive-prone binaries.
4. **Modern PLT caveat**: Many x86-64 firmware binaries use `.plt.sec` instead of legacy `.plt`. Simple `objdump` greps for `call.*func@plt` will return zero results even when the binary imports dangerous functions. For quick triage, use `readelf -r` to inspect `JUMP_SLOT` relocations. If calculating PLT stub addresses manually, use GOT index × stub size + PLT base.

## Phase 2: IDA Pro 9.3 Headless Deep Analysis
1. **Setup**:
   - IDA Pro 9.3 is located at `~/ida-pro-9.3`.
   - Install the bundled wheel: `pip3 install ~/ida-pro-9.3/idalib/python/idapro-0.0.7-py3-none-any.whl`
   - Activate idalib: `python3 ~/ida-pro-9.3/idalib/python/py-activate-idalib.py -d ~/ida-pro-9.3`
   - Always set `IDADIR` environment variable to `~/ida-pro-9.3` before importing `idapro`.
2. **Idalib API constraints**:
   - Do **not** import `ida_nam`; this module does not exist in the bundled idalib distribution.
   - `idc.get_name_ea_simple("strcpy")` resolves to the **GOT entry**, not the PLT stub, on `.plt.sec` binaries. A single `XrefsTo` on this address yields the PLT stub; a second `XrefsTo` on the PLT stub address yields the actual `.text` call sites. Implement this two-level xref resolution.
3. **Prioritization**: Focus Phase 2 on network-facing daemons (e.g., `dnsmasq`, `sshd`) that lack stack canaries and FORTIFY but contain raw `strcpy`/`strcat`/`memcpy` JUMP_SLOT entries. Delegate detailed idalib patterns to `idalib-headless-elf-sink-analysis` if needed.

## Output Artifacts
- Phase 1 results: `./cwe120_results/phase1/`
- Phase 2 IDA results: `./cwe120_results/phase2/`
- Final report: `./cwe120_results/CWE120_ANALYSIS_REPORT.md`
