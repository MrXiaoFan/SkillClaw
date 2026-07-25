# tcpdump Current

- Targets:
  - `tcpdump-4.9.1 / CVE-2017-13031`
  - `tcpdump-4.9.1 / CVE-2018-14469`
- Current status: two confirmation-style cases are available

## 2017-13031 result

- Ground truth: `print-frag6.c / frag6_print`
- SkillClaw and direct baseline both localized the right file/function.
- The main failure mode was CVE-number drift rather than source localization.

## 2018-14469 result

- Ground truth: `print-isakmp.c / ikev1_n_print`
- Added artifact generation and confirmation chain:
  - `generate_confirmation_input.py` creates a semantic IKEv1 notification pcap
  - `prepare_confirmation_artifacts.sh` materializes the pcap and runner script
  - case metadata records target binary, function, and artifact paths
- Dynamic case runner currently returns `status: passed`.

## What tcpdump now gives us

- one source-parser localization case (`13031`)
- one PoC/artifact-driven confirmation case (`14469`)

Together they make tcpdump the clearest proof that the framework can support
both localization scoring and executable confirmation.

