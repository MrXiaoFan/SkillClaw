# tcpdump direct confirmation rerun (2026-07-02)

## Target

- Case: `tcpdump-4.9.1-cve-2017-13031`
- Mode: `direct-deepseek-guarded`
- Root: `/home/li/skillclaw-eval/tcpdump-4.9.1`

## Result

- score: `10/10`
- exact CVE: `CVE-2017-13031`
- file/function: `print-frag6.c` / `frag6_print`
- validation: `passed`
- artifact exists: `passed`
- artifact exec: `passed`
- ASan: `skipped`

The generated pcap and wrapper reproduced the expected behavior-backed
confirmation path:

```text
generate truncated IPv6 fragment pcap
-> run tcpdump on the artifact
-> hit Fragment (44) path
-> emit [|frag]
-> validator passes
```

## Archived files

- `experiment_records/remote_runs/tcpdump-confirmation-20260702b-direct/tcpdump-4.9.1-cve-2017-13031-direct-deepseek-guarded-20260702-094727-final.json`
- `experiment_records/tcpdump_confirmation_skillclaw_vs_direct_20260702.json`
- `experiment_records/tcpdump_confirmation_skillclaw_vs_direct_20260702.md`

## Interpretation

This rerun completes the `tcpdump` confirmation line on both sides:

- SkillClaw confirmation run: `10/10`, confirmation passed
- Direct DeepSeek confirmation run: `10/10`, confirmation passed

So `tcpdump` is now no longer only a localization case; it is a working
behavior-backed confirmation case with a matched SkillClaw/direct baseline.
