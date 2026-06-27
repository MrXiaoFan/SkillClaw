---
name: firmware-embedded-lua-shell-extraction
description: "Extract and reconstruct embedded Lua scripts from raw firmware binaries using only standard Unix shell tools when IDA/idalib or binary analysis frameworks are unavailable. Covers offset indexing, large-block carving, and plaintext handler reconstruction for WebVPN-style embedded Lua audits. NOT for: environments with functional IDA Pro, idalib, or Ghidra scripting access where automated disassembly/decompilation is preferred."
category: general
---

Use this workflow to extract embedded Lua scripts from monolithic firmware binaries when IDA/idalib or advanced RE frameworks are unavailable.

## 1. Index strings with decimal offsets
Create a searchable offset database once:
bash
strings -n 8 -t d /path/to/firmware > firmware.strings.txt


## 2. Find Lua entry points and routes
Search for script markers and Cisco/WebVPN route prefixes:
bash
grep -E '\.lua$|function\s+\w+|HTTP_GET_PARAM_BY_NAME|dofile\(' firmware.strings.txt
grep -E '/\+CSCOE\+\/|\/+webvpn\+\/|\/+CSCOCA\+\/|/CSCOSSLC/' firmware.strings.txt


## 3. Carve large contiguous blocks
From a target decimal offset, extract 32–128 KB starting ~512 bytes before the hit to capture function prologues and context:
bash
dd if=/path/to/firmware bs=1 skip=$((OFFSET - 512)) count=65535 2>/dev/null > block.bin
strings -n 4 block.bin > block.txt

Avoid small fragments; handlers and taint chains span multiple kilobytes.

## 4. Reconstruct handlers and taint sources
In `block.txt`, identify:
- Handler functions (e.g., `function files_retr_handler`)
- Parameter extraction points (`local x = HTTP_GET_PARAM_BY_NAME("y")`)
- Route-to-handler mapping by proximity of URL strings to function definitions

## 5. Handle Lua bytecode
If you encounter the `\x1bLua` magic bytes, carve from that offset until the next long null padding or entropy shift, save as `.luac`, and note it requires `luadec` or similar rather than plaintext analysis.
