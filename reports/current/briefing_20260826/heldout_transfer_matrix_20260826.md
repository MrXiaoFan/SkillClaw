# Held-Out Transfer Matrix (2026-08-26)

| Source case | Held-out case | Source CVE | Held-out CVE | Candidate skill | no-skill mean | seed-skill mean | candidate-skill mean | Candidate function hit | Candidate evidence hit | Candidate root-cause hit | Readout |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `fh451-httpd-overflow-formQuickIndex` | `fh451-httpd-overflow-formWrlExtraSet` | `CVE-2026-3679` | `CVE-2026-4534` | `elf-cwe120-firmware-triage` | 3.50 | 3.00 | 3.00 | 0/3 | 3/3 | 0/3 | negative transfer |
| `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formWlanSetup` | `CVE-2026-5042` | `CVE-2026-5608` | `elf-cwe120-firmware-triage` | 2.00 | 2.00 | 3.67 | 2/3 | 2/3 | 0/3 | partial function-level improvement |
| `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formSetSystemSettings` | `CVE-2026-5042` | `CVE-2026-5044` | `elf-cwe120-firmware-triage` | 5.50 | 5.50 | 5.00 | 3/3 | 3/3 | 0/3 | neutral / slightly worse |
| `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formWISP5G` | `CVE-2026-5042` | `CVE-2026-4566` | `elf-cwe120-firmware-triage` | 2.83 | 2.83 | 4.50 | 3/3 | 3/3 | 0/3 | strongest function-level transfer |

## Immediate conclusion

These four runs support a narrow but real statement:

- the current evolved candidate can change future blind analysis on unseen
  firmware tasks from the same family

They do not yet support the stronger statement:

- the current pipeline already evolves publish-safe skills that reliably improve
  root-cause correctness on future tasks
