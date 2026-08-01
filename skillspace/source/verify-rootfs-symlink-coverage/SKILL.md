---
name: verify-rootfs-symlink-coverage
description: "When analyzing extracted firmware or rootfs images and the user challenges whether bin/, lib/, sbin/, or lib64/ directories were missed. Use this to verify whether apparent coverage gaps are caused by usr-merge symlinks rather than incomplete file enumeration. NOT for: general filesystem audits outside firmware extraction contexts, or resolving permission-denied coverage gaps unrelated to symlink semantics."
category: general
---

## Firmware rootfs symlink coverage verification

When enumerating files in an extracted firmware or rootfs image, do not assume that missing paths under `bin/`, `lib/`, `sbin/`, or `lib64/` mean incomplete coverage. Modern Linux rootfs images often use usr-merge symlinks (e.g., `bin -> usr/bin`, `lib -> usr/lib`).

### Verify before conceding gaps

1. **Check for symlinks in the rootfs root:**
   bash
   ls -la ./extracted/analysis_fs/bin ./extracted/analysis_fs/lib ./extracted/analysis_fs/sbin ./extracted/analysis_fs/lib64
   

2. **Understand `find` behavior:**
   - `find ./extracted/analysis_fs/ -type f` traverses into symlinked directories but returns the **physical target path** (e.g., `usr/bin/foo`), not `bin/foo`.
   - `find -L ./extracted/analysis_fs/ -type f` follows symlinks and returns **both** `bin/foo` and `usr/bin/foo`, inflating counts with duplicates. Expect filesystem-loop errors on `bin/X11` and permission errors on `lib/ssl/private`.

3. **Confirm duplication with inode comparison:**
   bash
   stat -c%i ./extracted/analysis_fs/bin/bash ./extracted/analysis_fs/usr/bin/bash
   
   Matching inodes mean the same physical file. The true unique file count is the count of distinct inodes, not paths.

4. **Compute canonical unique coverage:**
   bash
   # Canonical physical-path ELF list
   find ./extracted/analysis_fs/ -type f | xargs file | grep -E 'ELF.*LSB' | awk -F: '{print $1}' | sort > elf_physical.txt
   
   # Unique inode count (ground truth)
   find ./extracted/analysis_fs/ -type f | xargs stat -c%i 2>/dev/null | sort -u | wc -l
   

5. **Decision rule:** If the physical-path ELF list covers the unique inode count, coverage is complete. Do not concede missing `bin/` or `lib/` coverage until symlink duplication is disproven by inode mismatch.

### Workspace cleanup
Before saving new intermediate artifacts, list the working directory, identify stale files from previous rounds (old scanner scripts, logs, superseded JSON/txt reports), and remove them. Retain only the current analysis set.
