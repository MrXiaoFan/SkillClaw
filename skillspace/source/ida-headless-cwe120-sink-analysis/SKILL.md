---
name: ida-headless-cwe120-sink-analysis
description: "Operational guide for running CWE-120 deep static analysis with IDA Pro 9.3 in headless mode. Covers mandatory environment variables, .i64 database pre-generation with idat -B when Hex-Rays fails, patching idalib-mcp typing/pydantic compatibility issues, and the correct two-level xref traversal (.text → .plt → extern) for discovering sink call sites. NOT for: interactive GUI analysis, non-ELF firmware, or vulnerability exploitation."
category: general
---

## Pre-flight: Environment Variables
Before importing `idapro` in any headless script, set these exactly:
bash
export IDADIR="$HOME/ida-pro-9.3"
export HOME="$HOME"


## Database Preparation
If `ida_hexrays.init_hexrays_plugin()` returns `False` or the database opens with a non-zero status:
1. Remove any existing incomplete `.i64` file.
2. Generate a complete database with batch-mode IDA:
   bash
   ~/ida-pro-9.3/idat -B -o/path/to/binary.i64 /path/to/binary
   
3. Open the `.i64` directly in your script with `run_auto_analysis=False`.

## idalib-mcp Compatibility (if using MCP)
The `idalib-mcp` server may crash with `typing.TypedDict` / pydantic errors on Python < 3.12.
- Patch `mcp-plugin.py` in the UV site-packages directory: move the `TypedDict` import from `typing` to `typing_extensions`.
- Delete `server_generated.py` and re-import `ida_pro_mcp.server` to regenerate it.
- For batch analysis, prefer the direct `idapro` Python API over the MCP SSE server to avoid protocol overhead.

## Sink Discovery: Two-Level Xref Traversal
Do not scan the full address space. Calls to dangerous functions in stripped ELFs route through PLT stubs.
1. Locate sinks by scanning `idautils.Names()` for the sink name, `.plt` prefixes, or `j_` stubs.
2. For each PLT address, collect xrefs with `idautils.XrefsTo(ea)`.
3. Filter xrefs to those in `.text` segments — these are the real callers.
4. Decompile the `.text` caller function to inspect buffer allocation and guards.

## Execution Context
Run scripts with the Python interpreter from the `ida-pro-mcp` UV tool environment to ensure compatible `pydantic` and `typing-extensions` versions:
bash
$HOME/.local/share/uv/tools/ida-pro-mcp/bin/python3 /tmp/script.py /path/to/binary

