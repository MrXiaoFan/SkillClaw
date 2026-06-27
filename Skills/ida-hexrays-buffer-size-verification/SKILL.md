---
name: ida-hexrays-buffer-size-verification
description: "When using IDA Pro headless (idalib) with Hex-Rays for CWE-120 buffer-overflow verification, decompiler local-variable array sizes (e.g., char buf[16]) are heuristic inferences, not ground-truth allocations. Use this skill to cross-check apparent mismatches between sink size arguments and decompiler buffer types against actual stack frame layout before confirming vulnerabilities. NOT for: general IDA scripting or non-CWE-120 analysis workflows."
category: general
---

# IDA Hex-Rays Buffer Size Verification for CWE-120

## Core Rule
Never confirm a buffer-overflow vulnerability based solely on Hex-Rays decompiler output showing `char buf[N]` when the sink argument is larger than `N`. The decompiler infers array dimensions from access patterns; actual stack allocation may be substantially larger.

## Verification Procedure

When you see a decompiler line like:
c
char s[16]; // [rsp+40h] [rbp-940h]
fgets(s, 4096, stream);


1. **Trust the stack offset, not the type size.** The comment `[rbp-940h]` indicates the real frame usage.
2. **Query the frame size programmatically:**
python
import ida_frame, ida_funcs
func = ida_funcs.get_func(call_ea)
print("Frame size:", ida_frame.get_frame_size(func))

3. **Cross-check with assembly stack setup (mandatory):**
   - Look at the function prologue: `sub rsp, 0xNNN`
   - Measure bytes between the buffer start (`lea rax, [rbp-0xNNN]`) and the canary/saved registers.
   - If the span is >= the sink size argument, the call is likely safe.
   - Look for `mov rax, fs:28h` (canary load) and calculate distance.
4. **Mandatory exclusion check:**
   - If the buffer is a pointer argument (not a stack local), trace it back to `malloc`, `alloca`, or the caller's frame.
   - If the decompiler shows `char *s` but the assembly reveals a large `sub rsp`, the local is actually a big array.

## Common False-Positive Pattern
- **Decompiler:** `char s[16]; fgets(s, 4096, stream);`
- **Reality:** Stack frame allocates 0x400+ bytes for `s`, but Hex-Rays truncated the type because only the first 16 bytes were accessed in other code paths.
- **Action:** Verify via frame size / disassembly before reporting.
