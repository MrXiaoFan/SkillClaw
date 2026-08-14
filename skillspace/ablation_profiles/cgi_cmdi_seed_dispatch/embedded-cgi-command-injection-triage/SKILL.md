---
name: embedded-cgi-command-injection-triage
description: "Seed workflow for locating HTTP-reachable command-injection paths in compiled embedded CGI binaries. Use when the workspace contains firmware-derived .cgi ELF programs or lighttpd/uhttpd web roots. Prefer dispatch-to-sink tracing over generic vulnerability summaries."
category: general
---

- Start from the request router, not from a global sink list. Look for dispatcher variables such as `page`, `action`, `mode`, or `cmd`, then enumerate the branch values they control.
- For each branch, record the parameter names it reads and the helper functions used to extract them from POST bodies, query strings, or CGI environment variables.
- Within the same branch, look for shell-command construction patterns such as `sprintf`, `snprintf`, `vsprintf`, command templates ending in `.sh`, and wrappers that later call `system` or `popen`.
- Prefer the single branch with the most complete path: request parsing -> parameter extraction -> command string construction -> command execution.
- In the final answer, prioritize one concrete source-to-sink path instead of listing many possible sinks across the whole binary.
