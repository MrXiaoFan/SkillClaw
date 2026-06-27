---
name: peplink-fiwm-firmware-analysis
description: "Guides static analysis of Peplink router firmware images that use the signed FIWM container format (e.g., MAX BR1 series with `verisign` signatures and `maxbr1c` model strings). Use when standard `binwalk` extraction fails to find squashfs/ELF signatures and the image contains cleartext Boa/CGI strings. NOT for: unpacked firmware where binwalk successfully extracts a rootfs, or non-Peplink proprietary formats."
category: general
---

Peplink firmware images (e.g., MAX BR1) use a signed FIWM container that encrypts or obfuscates the actual rootfs, causing standard extraction tools to fail.

**Identification**
- Header starts with `verisign` followed by `FIWM` metadata and device model strings such as `maxbr1c`, `MODEL`, and `VERSION` (e.g., `08.05.04`).
- `binwalk`, manual `hsqs` searches, and `unsquashfs` will not locate a filesystem because the payload is encrypted.

**Triage workflow**
1. **Abandon standard binwalk extraction.** Do not waste steps on `tar`, `unzip`, or squashfs carving across the full image.
2. **Parse the FIWM header.** Use Python or `hexdump -C` to inspect bytes immediately after the `verisign` block and model strings for size/offset fields that delimit the encrypted payload or a secondary bootloader.
3. **Search for Peplink-specific extractors.** Check the local environment for vendor-specific tools, SDK utilities, or known open-source extractors targeting Peplink FIWM before attempting manual decryption.
4. **Static strings pivot.** Even without full extraction, search for cleartext Boa web server configuration, CGI endpoint paths (`*.cgi`, `cgi-bin`), and shell command templates (`system(`, `popen(`, `uci `, `mtd`). These often reveal command-injection or authentication-bypass targets directly.
5. **Dynamic pivot.** If a live device is reachable, probe exposed Boa/CGI endpoints directly with `curl` rather than waiting for full firmware extraction.
