---
name: idalib-headless-elf-sink-analysis
description: "Use when automating headless static analysis of Linux ELF binaries with IDA Pro 9.x idalib to locate true call sites of imported dangerous functions (e.g., strcpy, memcpy) in stripped firmware. Covers the bundled idapro wheel installation, idalib activation, headless database loading, and the two-level xref resolution required because naive XrefsTo on imported symbols returns PLT-internal references instead of real .text callers. NOT for: interactive IDA GUI scripting, Windows PE analysis, or non-ELF firmware formats."
category: general
---

## idalib Headless ELF Sink Analysis (IDA Pro 9.x)

### 1. Environment Setup
Do NOT install `idapro-mcp` or `idalib` from PyPI/GitHub. IDA Pro 9.x bundles its own Python package inside the installation tree.
- Install the wheel: `pip install <ida_dir>/idalib/python/idapro-<ver>-py3-none-any.whl`
- **Headless activation:** Before importing `idapro` in a headless script, set the `IDADIR` environment variable to the IDA installation directory (the directory containing `libidalib.so`):
  python
  import os
  os.environ["IDADIR"] = "<ida_dir>"
  
  Alternatively, run the bundled activation script: `python3 <ida_dir>/idalib/python/py-activate-idalib.py -d <ida_dir>`

### 2. Headless Load & Auto-Analysis
The `idapro` module only exposes database lifecycle helpers (`open_database`, `close_database`, etc.). The actual analysis APIs (`idc`, `idaapi`, `idautils`, `ida_funcs`, `ida_segment`, etc.) are separate imports that become available once `idapro` is loaded.
python
import os
os.environ["IDADIR"] = "<ida_dir>"
import idapro, ida_auto
idapro.open_database(binary_path, run_auto_analysis=True)
ida_auto.auto_wait()
# ... analysis ...
idapro.close_database()


### 3. Resolve Real Call Sites for Imported Sinks (Stripped ELFs)
In stripped binaries, `idc.get_name_ea_simple('strcpy')` resolves to the GOT/PLT entry. Naive `idautils.XrefsTo(got_ea)` returns references from inside the PLT stub and `.got.plt`, **not** the actual callers in `.text`.

Use two-level resolution:
python
import ida_funcs, idautils, idc, ida_segment

got_ea = idc.get_name_ea_simple('strcpy')  # or memcpy, sprintf, etc.
for xref in idautils.XrefsTo(got_ea):
    # xref.frm is inside the PLT stub (e.g., the jmp *GOT)
    plt_func = ida_funcs.get_func(xref.frm)
    if not plt_func:
        continue
    # Find xrefs into the PLT stub start from executable code
    for xref2 in idautils.XrefsTo(plt_func.start_ea):
        seg = ida_segment.getseg(xref2.frm)
        seg_name = idc.get_segm_name(seg.start_ea) if seg else ''
        if '.text' in seg_name or '.init' in seg_name:
            caller = ida_funcs.get_func(xref2.frm)
            caller_name = caller.name if caller else f"sub_{xref2.frm:x}"
            print(f"Real call to strcpy at {hex(xref2.frm)} from {caller_name}")


### 4. Key Points
- Always verify the referencing segment is `.text` (or `.init`/`.fini`) to discard linker artifacts.
- If the binary is fully stripped and IDA did not name the import, identify the PLT stub by its segment (`.plt.sec` or `.plt`) and scan for `call` instructions targeting that range as a fallback.

