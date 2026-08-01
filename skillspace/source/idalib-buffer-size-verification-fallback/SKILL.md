---
name: idalib-buffer-size-verification-fallback
description: "Determine exact stack and heap buffer sizes in IDA headless (idalib) when Hex-Rays decompilation string output is empty, truncated, or omits variable declarations during CWE-120 analysis. Use `cfunc.get_lvars()` type info or fall back to `ida_frame` stack frame APIs instead of fragile string parsing. NOT for: interactive IDA Pro GUI usage or general decompilation troubleshooting unrelated to buffer sizing."
category: general
---

When verifying buffer allocations for CWE-120 in IDA headless (idalib), do not rely solely on parsing `str(cfunc)` output. If the decompiled text is empty, truncated, or omits the target variable declaration, use the following structured fallbacks.

**1. Query local variable objects directly**
If `ida_hexrays.decompile(ea)` returns a valid `cfunc` object, extract type and size from the local variable list instead of regex-parsing text:
python
cfunc = ida_hexrays.decompile(func_ea)
for lv in cfunc.get_lvars():
    if lv.name == "s":          # target variable
        size = lv.type.get_size()
        # If the type is a pointer/array, inspect lv.type details
        # or compare its pointed-to size against usage

This avoids brittle string splitting and works even when `str(cfunc)` is incomplete.

**2. Fall back to stack frame structures**
If decompilation returns None or omits the variable entirely, inspect the function's stack frame directly via `ida_frame.get_frame(func_ea)` and iterate frame members with `ida_struct` APIs to map offsets to allocation sizes.

**3. Heap allocation tracing**
For buffers assigned from heap calls (e.g., `name = malloc(0x803)`), trace the allocation argument constant in the caller block. Compare the allocated size directly against the sink limit (e.g., `fgets` size parameter).

**4. Pointer reassignment awareness**
When code reassigns a pointer (`p_s = &s;`), always verify the size of the underlying storage `s` (stack frame member or global), not the pointer variable `p_s`.

Cross-check the final derived size against the sink's size argument to confirm CWE-120 exploitability.
