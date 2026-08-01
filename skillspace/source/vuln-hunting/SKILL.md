---
name: vuln-hunting
description: "Orchestrated reverse-engineering vulnerability hunting for compiled binary artifacts (firmware images, ELF executables, CGI binaries, embedded Lua bytecode) using IDA Pro MCP static analysis, specialist routing, and structured evidence chains. Use ONLY when the task explicitly requires reverse-engineering of compiled binary artifacts where source code is unavailable or insufficient, and the binary is the primary analysis target (not just a compile artifact for a source audit). STRICTLY EXCLUDED: source-code-only audits, source-level vulnerability research (including CVE investigations of libraries like giflib or libpng), tasks where source code is the main deliverable even if a test binary exists, live web/API penetration testing without binary context, network service fuzzing without binary context, generic CVE lookups, and any memory-safety or vulnerability discovery task that relies solely on source code without a compiled binary file."
category: general
---

# vuln-hunting

## Required Flow

1. Read `references/specialist-routing.md` and select the primary specialist for the target.
2. Read `references/adapters/{module}-adapter.md` for the requested module.
3. Read `references/upstream-map.md`.
4. Output the **Module Decision** block:
   - `vuln-hunting` → submodule: `{module}`
   - Selected primary specialist
   - Loaded upstream snapshot path
   - Upstream workflow steps to follow
5. Attempt to load the upstream snapshot at `upstreams/{module}.md`.
   - **If the file does not exist**, use the adapter description and upstream-map as the authoritative workflow. Do not halt; proceed with IDA MCP-assisted enumeration directly.
6. Execute the workflow in two phases:
   - **Phase A – Surface Map**: Enumerate endpoints, routes, and handlers. Limit this phase; stop once the top 20–30 candidate interfaces and their entry points are identified.
   - **Phase B – Deep Trace**: Immediately transition to tracing attacker-controlled data to sinks using the upstream workflow or IDA MCP. Do not substitute structured binary analysis with exhaustive Bash `strings`/`grep` sweeps on large binaries **unless IDA MCP string tools are timing out or unavailable**. When MCP is unstable, targeted Bash `strings` with narrow regex filters is the required fallback for surface mapping. For each candidate, validate the vulnerability pattern and close the evidence chain before proceeding to the next candidate.
7. Document findings using `references/evidence-schema.md` and `references/templates/finding-template.md`.

## IDA MCP Output Management

The IDA Pro MCP `list_strings_filter` can return multi-megabyte results that exceed token limits, or time out on large binaries.

- Always start with a small `count` (e.g., 20–50) and use `offset` to paginate.
- If the tool returns a "maximum allowed tokens" error, the output is saved to a file path in the error message. Use `bash` with `jq` or `grep` to extract entries instead of reading the file directly.
- Example: `cat <saved-path> | jq -r '.result.data[] | "\(.address)|\(.string[0:200])"' | head -n 40`
- **If `list_strings_filter` times out repeatedly (even with `count` ≤ 50), treat it as an MCP stability issue and fall back to Bash `strings` with targeted regex filters immediately.** Do not keep retrying IDA MCP for bulk string enumeration.
- **File-offset vs. IDA address**: `strings -t x` outputs file offsets. These are NOT valid IDA virtual addresses and must not be passed to `read_memory_bytes`. To inspect content around a file offset, use Bash (`dd` or Python) to read the raw file at that offset. Only use `read_memory_bytes` with addresses returned by IDA MCP tools (e.g., `list_functions`, `get_function_by_name`, or successful `list_strings_filter` results).
- For firmware binaries larger than ~100 MB, prefer IDA MCP over Bash `strings`/`grep` for string and symbol enumeration **only when MCP is responsive**. If MCP times out, Bash extraction is the authoritative fallback for initial surface mapping.

## Tracing Data-Section References

When `get_function_by_address` returns "No function found", the address is in a data section.

1. Use `read_memory_bytes` on the data address and its xrefs to inspect surrounding context.
2. Trace data xrefs back to code by reading memory at xref locations; look for function prologues or call patterns.
3. For embedded Lua strings, prioritize tracing to `HTTP_GET_PARAM*` family calls, `io.open`, `os.execute`, `loadfile`, and `dofile` sinks.

## Evidence Chain

Close every confirmed or candidate finding with the full chain from `references/evidence-schema.md`:

text
entry or exposed interface
-> attacker-controlled source
-> data construction or state transition
-> validation or missing validation
-> sink or security decision
-> output, privilege, data exposure, or other security effect
