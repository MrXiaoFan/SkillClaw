# Confirmation Portfolio 2026-07-05

## Scope

This table tracks which vulnerability cases have an executable confirmation
path today. It is a case-engineering view, not a skill-effectiveness view.

## Portfolio

| case_id | target | confirmation type | validator status | executable evidence | final agent record |
| --- | --- | --- | --- | --- | --- |
| `giflib-5.1.2-cve-2016-3977` | `gif2rgb` | crash-backed | passed | generated GIF + ASan/crash path | yes |
| `tcpdump-4.9.1-cve-2017-13031` | `tcpdump` / `frag6_print` | behavior-backed | passed | generated frag6 pcap + wrapper + marker validation | yes |
| `tcpdump-4.9.1-cve-2018-14469` | `tcpdump` / `ikev1_n_print` | behavior-backed | passed | generated IKEv1 notification pcap + wrapper + marker validation | no |
| `libxml2-2.9.4-cve-2017-8872` | `xmllint` / `htmlParseTryOrFinish` | logic-backed | passed | source match + local-lib binding + push-harness confirmation | yes |

## Key distinction

- `validator status = passed` means the case has a runnable confirmation chain.
- `final agent record = yes` means this case has at least one scored experiment
  record that can participate in `skill_feedback` and skill-evolution analysis.
- Therefore, `tcpdump-4.9.1-cve-2018-14469` is already part of the confirmation
  portfolio, but it is not yet part of the skill-feedback portfolio.

## Current engineering reading

1. The confirmation portfolio now covers four cases across three styles:
   - crash-backed
   - behavior-backed
   - logic-backed
2. The weakest remaining gap is no scored agent run yet for
   `tcpdump-4.9.1-cve-2018-14469`.
3. The next honest milestone is not “more summary files”; it is one real
   SkillClaw run and one direct-baseline run on this new case.
