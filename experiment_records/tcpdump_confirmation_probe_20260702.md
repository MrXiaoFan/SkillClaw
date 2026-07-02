# tcpdump confirmation probe (2026-07-02)

This probe upgrades `tcpdump-4.9.1-cve-2017-13031` from a pure localization
case into a behavior-backed confirmation case.

## What changed

- Added a repo-maintained PoC generator:
  - `experiment_cases/pocs/tcpdump-4.9.1-cve-2017-13031/make_poc.py`
- Expanded the case with:
  - `expected_artifacts`
  - `repro.build`
  - `repro.run`
  - `artifact_exists`
  - `artifact_exec`

## Probe setup

Remote root:

```text
~/skillclaw-eval/tcpdump-4.9.1
```

Generated artifact:

```text
artifacts/poc-cve-2017-13031.pcap
```

Wrapper artifact:

```text
artifacts/run_tcpdump_frag6_poc.sh
```

Validator record:

- [tcpdump_confirmation_validator_20260702.json](/d:/Code/SkillClaw/SkillClaw/experiment_records/remote_runs/tcpdump-confirmation-probe-20260702/tcpdump_confirmation_validator_20260702.json)

## Result

Case-level validation passed.

Key signals:

- `generated-poc-input-exists`: `passed`
- `generated-poc-input-executes`: `passed`
- matched markers:
  - `next-header Fragment (44)`
  - `[|frag]`

## Interpretation

This is now a working **behavior-backed confirmation** case:

```text
generate pcap
-> run tcpdump
-> hit frag6 parser path
-> observe truncation marker
-> validator passes
```

It is **not yet** a crash-backed confirmation case. The full tcpdump CLI path
still does not produce a stable ASan crash for CVE-2017-13031, so
`asan_command` remains disabled for this case.
