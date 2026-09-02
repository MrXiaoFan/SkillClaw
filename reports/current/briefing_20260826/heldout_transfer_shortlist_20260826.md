# Held-out Transfer Shortlist (2026-08-26)

This note records the next most practical source / held-out combinations after
the first FH451 transfer run.

Selection rules:

- same project
- same binary
- same bug class
- different vulnerable functions
- recent traceable source runs available in `runtime/imports/remote_vm`

## 1. Highest-priority family: F9K1122 / `vul_file/webs`

These are attractive because:

- they have the densest recent run coverage
- they stay inside one firmware family
- they are all `buffer_overflow` cases
- they use different handler functions, so held-out separation is cleaner

Shortlist:

| Source case | Held-out case | Source CVE | Held-out CVE | Traceable runs |
| --- | --- | --- | --- | --- |
| `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formWISP5G` | `CVE-2026-5042` | `CVE-2026-4566` | 32 + 44 |
| `f9k1122-webs-overflow-formWISP5G` | `f9k1122-webs-overflow-formWlanSetup` | `CVE-2026-4566` | `CVE-2026-5608` | 44 + 31 |
| `f9k1122-webs-overflow-formSetSystemSettings` | `f9k1122-webs-overflow-formWISP5G` | `CVE-2026-5044` | `CVE-2026-4566` | 30 + 44 |

Why F9K1122 is promising:

- recent experiments already focused on distinguishing nearby firmware targets
- the family may be better suited for testing whether a candidate skill can
  learn handler-level distinctions inside the same `webs` binary
- the current first FH451 negative result suggests we should try one family
  where the drift landscape is less dominated by Tenda command-injection sinks

## 2. Second-priority family: FH451 / `vul_file/httpd`

Still useful, but riskier than F9K1122 because the model often drifts into
repeated Tenda command-execution families across cases.

Shortlist:

| Source case | Held-out case | Source CVE | Held-out CVE | Traceable runs |
| --- | --- | --- | --- | --- |
| `fh451-httpd-overflow-WrlclientSet` | `fh451-httpd-overflow-formWrlExtraSet` | `CVE-2026-4535` | `CVE-2026-4534` | 12 + 27 |
| `fh451-httpd-overflow-formWrlExtraSet` | `fh451-httpd-overflow-fromAdvSetWan` | `CVE-2026-4534` | `CVE-2026-3678` | 27 + 12 |
| `fh451-httpd-overflow-formWrlExtraSet` | `fh451-httpd-overflow-fromSetCfm` | `CVE-2026-4534` | `CVE-2026-3677` | 27 + 12 |

Why FH451 remains useful:

- the first strict held-out experiment is already built on this family
- keeping the same family makes replication cheap
- if another FH451 pair also fails, we gain stronger evidence that the current
  candidate-generation signal is overfitting the wrong sink family

## 3. Lower-priority pair: tcpdump

| Source case | Held-out case | Source CVE | Held-out CVE | Traceable runs |
| --- | --- | --- | --- | --- |
| `tcpdump-4.9.1-cve-2017-13031` | `tcpdump-4.9.1-cve-2018-14469` | `CVE-2017-13031` | `CVE-2018-14469` | 5 + 4 |

Why lower priority:

- far fewer recent traceable runs
- source-style and held-out-style may be less aligned with the current
  firmware-centered skill experiments

## 4. Recommendation

If we want the next held-out run to have the best chance of producing a clean
and interpretable result, the next choice should be:

1. `f9k1122-webs-overflow-formCrossBandSwitch`
   -> `f9k1122-webs-overflow-formWISP5G`
2. `f9k1122-webs-overflow-formWISP5G`
   -> `f9k1122-webs-overflow-formWlanSetup`
3. `fh451-httpd-overflow-WrlclientSet`
   -> `fh451-httpd-overflow-formWrlExtraSet`

The main reason to switch to F9K1122 first is not that FH451 is invalid, but
that FH451 already showed a strong wrong-family attraction. A second family
gives us a better read on whether the problem is pair-specific or structural.
