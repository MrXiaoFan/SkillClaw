# Case CVE Backfill Audit (2026-08-25)

## Summary

- Audited empty `ground_truth.cves` cases: 19
- Backfilled this round: 18
- Left empty on purpose: 1

## Counts

- By project: F1202=2, F453=4, F456=1, F9K1122=4, FH451=5, i12=2
- By CVE year: 2024=1, 2025=1, 2026=16
- By vulnerability type: authentication bypass via path traversal=1, embedded httpd cgi command injection=3, embedded httpd stack-based buffer overflow=9, embedded httpd stack-based buffer overflow via credential decoding=1, embedded webs stack-based buffer overflow=4
- By assigner: VulDB=17, mitre=1

## Reporter Distribution

- (none listed): 1
- Jimi (VulDB User): 1
- LtzHust (VulDB User): 4
- LtzHust2 (VulDB User): 3
- LtzHuster (VulDB User): 6
- LtzHuster2 (VulDB User): 2
- panda_0x1 (VulDB User): 1

## Detailed Table

| case_file | CVE | assignerOrgId | assigner | reporter | note |
|---|---|---|---|---|---|
| f1202-httpd-cmdinject-formWriteFacMac.json | CVE-2024-30637 | 8254265b-2729-46b6-b9e3-3dfca2d5bfca | mitre | - | Exact function match: formWriteFacMac command injection. |
| f1202-httpd-overflow-fromAdvSetWan.json | CVE-2025-7527 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | panda_0x1 (VulDB User) | Public record commonly labels model as FH1202; local dataset uses F1202. |
| f453-httpd-cmdinject-formWriteFacMac.json | CVE-2026-4554 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust (VulDB User) | Exact function match: formWriteFacMac command injection. |
| f453-httpd-overflow-formWrlsafeset.json | CVE-2026-3273 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust (VulDB User) | Exact function match: formWrlsafeset. |
| f453-httpd-overflow-fromqossetting.json | CVE-2026-3378 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust2 (VulDB User) | Exact function match: fromqossetting. |
| f453-httpd-overflow-fromRouteStatic.json | CVE-2026-3166 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust (VulDB User) | Exact function match: fromRouteStatic. |
| f456-httpd-cmdinject-formWriteFacMac.json | CVE-2026-7102 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster (VulDB User) | Exact function match: formWriteFacMac command injection. |
| f9k1122-webs-overflow-formCrossBandSwitch.json | CVE-2026-5042 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster2 (VulDB User) | Exact function match: formCrossBandSwitch. |
| f9k1122-webs-overflow-formSetPassword.json | - | - | - | - | Local file already marks this case as a duplicate/invalid dataset copy; leave ground_truth.cves empty. |
| f9k1122-webs-overflow-formSetSystemSettings.json | CVE-2026-5044 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster2 (VulDB User) | Exact function match: formSetSystemSettings. |
| f9k1122-webs-overflow-formWISP5G.json | CVE-2026-4566 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust (VulDB User) | Exact function match: formWISP5G. |
| f9k1122-webs-overflow-formWlanSetup.json | CVE-2026-5608 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust2 (VulDB User) | Exact function match: formWlanSetup. |
| fh451-httpd-overflow-formQuickIndex.json | CVE-2026-3679 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster (VulDB User) | Exact function match: formQuickIndex. |
| fh451-httpd-overflow-formWrlExtraSet.json | CVE-2026-4534 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster (VulDB User) | Exact function match: formWrlExtraSet. |
| fh451-httpd-overflow-fromAdvSetWan.json | CVE-2026-3678 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster (VulDB User) | Public helper name differs slightly from local notes, but endpoint/param/function match. |
| fh451-httpd-overflow-fromSetCfm.json | CVE-2026-3677 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster (VulDB User) | Local file uses fromSetCfm; public naming may appear as formSetCfm. |
| fh451-httpd-overflow-WrlclientSet.json | CVE-2026-4535 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHuster (VulDB User) | Exact function match: WrlclientSet. |
| i12-httpd-overflow-formexeCommand.json | CVE-2026-4041 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | Jimi (VulDB User) | Exact endpoint/function match: /goform/exeCommand, cmdinput, vos_strcpy. |
| i12-httpd-path-traversal-r7webs.json | CVE-2026-5849 | 1af790b2-7ee1-4545-860a-a788eba489b5 | VulDB | LtzHust2 (VulDB User) | Exact handler match: R7WebsSecurityHandler path traversal. |
