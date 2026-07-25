---
name: verify-rootfs-full-enumeration
description: "Use during static analysis of an extracted firmware rootfs (e.g., after `extract-rootfs`) when preparing Phase 2 deep-dive (e.g., IDA or Hopper sink analysis on discovered binaries). NOT for: source-code auditing, source-level vulnerability scanning, CVE discovery, web application testing, memory-safety analysis of individual C projects, single-ELF/binary analysis, or any task that does not involve an extracted firmware rootfs."
category: general
---

After Phase 1 scanning of an extracted rootfs, do NOT proceed to Phase 2 deep analysis until you verify coverage of all standard directories.

- Check that the enumeration includes binaries and libraries from: `bin/`, `sbin/`, `lib/`, `lib64/`, `usr/bin/`, `usr/sbin/`, `usr/lib/`, `usr/libexec/`, and `opt/`.
- If the Phase 1 report only contains paths under `usr/`, stop and re-run enumeration on the missing root-level directories.
- Confirm root-level assets were found with:
  bash
  find ./extracted/analysis_fs -type f | grep -E '^./extracted/analysis_fs/(bin|sbin|lib|lib64)/'
  
- When a user asks to analyze "all files under ./extracted/analysis_fs", explicitly scan all directories; do not default to `usr/` out of convenience.
- Before merging new deep-analysis rounds into a master findings file, validate that the master includes at least one binary from each major rootfs category (root-bin, root-sbin, root-lib, usr-bin, usr-lib). If any category is missing, flag the coverage gap to the user.
- If resuming a previous session, inspect the prior Phase 1 artifact list for directory coverage before continuing; do not assume earlier rounds were complete.

