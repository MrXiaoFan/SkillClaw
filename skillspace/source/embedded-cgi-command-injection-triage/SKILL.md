---
name: embedded-cgi-command-injection-triage
description: "Triage command-injection vulnerabilities in compiled CGI binaries on embedded Linux appliances running lighttpd or uhttpd. Use when dynamically testing firmware-derived web interfaces returns HTTP errors or when hunting for injectable parameters in .cgi ELF backends. NOT for: interpreted CGI scripts (PHP/Python), non-embedded targets, or buffer-overflow analysis."
category: general
---

- Enumerate CGI endpoints from the rootfs: list `/cgi-bin/` and paths defined in `lighttpd.conf`/`uhttpd.conf`, and grep HTML/JS for `<form action="...">` tags to discover all valid `.cgi` targets.
- Inspect the matching frontend form to determine the exact HTTP method, `enctype` (e.g., `multipart/form-data` for uploads), and required input names. Replicate the request precisely before fuzzing; HTTP 500 on embedded CGIs typically means missing required parameters or wrong `Content-Type`.
- Analyze the CGI ELF binary directly: run `strings`, `grep -a -E 'system|popen|execl|eval'`, and available ELF static-analysis tools on the `.cgi` file to locate command-execution sinks and their data sources (e.g., `getenv("QUERY_STRING")`, `CONTENT_LENGTH`, `stdin`).
- Once a sink and its parameter source are identified, craft injection payloads using shell metacharacters (`;cmd|`, `` `cmd` ``, `$(cmd)`) and deliver them through the correctly structured request matching the frontend form contract.
