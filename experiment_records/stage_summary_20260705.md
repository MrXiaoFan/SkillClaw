# Stage Summary 2026-07-05

## Current confirmation status

| case | target | confirmation level | current status | key evidence |
| --- | --- | --- | --- | --- |
| `giflib-5.1.2-cve-2016-3977` | `gif2rgb` | crash-backed | passed | generated PoC + sanitizer/crash-oriented validation |
| `tcpdump-4.9.1-cve-2017-13031` | `tcpdump` / `frag6_print` | behavior-backed | passed | targeted packet + file/function/evidence validation |
| `tcpdump-4.9.1-cve-2018-14469` | `tcpdump` / `ikev1_n_print` | behavior-backed | passed | generated IKEv1 notification pcap + runnable wrapper + output-marker validation |
| `libxml2-2.9.4-cve-2017-8872` | `xmllint` / `htmlParseTryOrFinish` | logic-backed | passed | source match + local-lib binding + push-harness state-window confirmation |

## What changed today

1. `libxml2` confirmation was upgraded from "manual probe notes" to an executable case-level validator.
   - Added `experiment_cases/pocs/libxml2-2.9.4-cve-2017-8872/confirm_logic_window.sh`.
   - Wired it into `experiment_cases/libxml2-2.9.4-cve-2017-8872.json` as `push-harness-logic-confirmation`.
   - Remote `run_dynamic_case.py` now returns `status: passed` for this case.

2. The `libxml2` validation chain now checks three different layers together.
   - `source_contains`: confirms `HTMLparser.c / htmlParseTryOrFinish / in->cur[2] / in->cur[3] / avail`.
   - `binary-links-local-libxml2`: confirms `xmllint_asan` resolves `./.libs/libxml2.so.2` instead of the system library.
   - `push-harness-logic-confirmation`: confirms representative chunk sequences reach `CONTENT`, `PROLOG`, and `MISC` windows with the expected `avail` and parser outcomes.

3. The engineering claim is now narrower and more accurate.
   - We can say the case has a reproducible dynamic/logic confirmation path.
   - We cannot yet say it has a stable sanitizer-crash PoC.
   - The likely blocker is that end-adjacent lookahead remains inside readable slack storage, so plain ASan may not fire even when the logical guard is weak.

4. A second tcpdump confirmation case is now executable end to end.
   - Added `experiment_cases/tcpdump-4.9.1-cve-2018-14469.json`.
   - Added `experiment_cases/pocs/tcpdump-4.9.1-cve-2018-14469/make_poc.py`.
   - Added `experiment_cases/pocs/tcpdump-4.9.1-cve-2018-14469/prepare_artifacts.sh`.
   - Remote `run_dynamic_case.py` now returns `status: passed` for `CVE-2018-14469`, with all source, artifact, and artifact-exec checks passing.

## Current architecture shape

The validation/evolution loop is now effectively split into four layers:

1. `experiment_cases/*.json`
   - case metadata, ground truth, scoring, validators, prompt variants

2. `experiment_cases/pocs/*`
   - case-specific repro helpers, generators, harnesses, and confirmation scripts
   - now includes explicit artifact preparation for behavior-backed tcpdump confirmation

3. `experiment_validation/*`
   - reusable validator runtime: `content_match`, `source_contains`, `command`, `artifact_exec`, `asan_command`, `bundle_script`

4. `experiment_scripts/*`
   - orchestration and reporting: `run_eval_case.py`, `run_dynamic_case.py`, `build_result_record.py`, feedback/bundle summaries

## Immediate next steps

1. Rebuild final records and feedback summaries so `skill_feedback_latest.*` reflects `giflib + tcpdump frag6 + tcpdump isakmp + libxml2`.
2. Add the next confirmation case outside the current four, with priority on a case that can support PoC generation or executable confirmation.
3. Continue `libxml2` only if we choose to pursue crash-level confirmation specifically; otherwise keep it as the canonical logic-confirmation case.
