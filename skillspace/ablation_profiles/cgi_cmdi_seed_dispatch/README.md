## Seed Firmware CGI Skill Profile

This profile contains a deliberately weak seed version of the firmware CGI command-injection
skill. It is meant for evolve experiments:

- strong enough to be selected for embedded CGI blind cases
- weak enough that it should still miss the exact vulnerable branch on hard cases
- generic enough not to encode case-specific oracle details

Use this profile when comparing:

- no skill
- weak seed skill
- evolved seed skill
