## giflib Confirmation Eval - 2026-07-01

### Scope

This rerun exercised the updated confirmation contract for
`giflib-5.1.2-cve-2016-3977` under `skillclaw-inline-guarded`.
The goal was to verify that the framework can now capture not only
source-level localization, but also generated trigger artifacts and
their executable confirmation path.

### Inputs

- Case: `experiment_cases/giflib-5.1.2-cve-2016-3977.json`
- Final record:
  `experiment_records/remote_runs/giflib-confirmation-20260701/giflib-skillclaw-confirmation-20260701-postvalidate3-final.json`
- Target root:
  `/home/li/skillclaw-eval/giflib-5.1.2`

### Key Outcome

The run produced a full confirmation-style positive result:

| Dimension | Result |
| --- | --- |
| Score | `10/10` |
| CVE hit | `CVE-2016-3977` |
| File hit | `util/gif2rgb.c` |
| Function hit | `DumpScreen2RGB` |
| Validation status | `passed` |
| Artifact exists | `passed` |
| Artifact exec | `passed` |
| ASan validation | `passed` |

### Confirmation Evidence

The generated artifact validators both succeeded:

1. `generated-poc-input-exists`
   - confirmed `artifacts/poc-cve-2016-3977.gif`
   - satisfied the minimum-size check

2. `generated-poc-input-executes`
   - executed `artifacts/run_giflib_poc.sh`
   - used `expect_crash: true`
   - returned code `134`
   - matched:
     - `AddressSanitizer`
     - `heap-buffer-overflow`
     - `DumpScreen2RGB`

The case-level `asan_command` validator also passed, confirming that the
reproduction path is not limited to a synthetic artifact check; the
expected ASan crash markers and target frame were observed on the actual
giflib reproduction command.

### Why This Run Matters

This is the first local result in which the framework captures all three
confirmation stages in one record:

1. analysis/localization success,
2. artifact generation and execution success,
3. sanitizer-backed dynamic confirmation success.

That makes this run the current strongest example of the project shifting
from "vulnerability localization only" toward "vulnerability confirmation."

### Next Use

This record should be used as the positive confirmation baseline when we:

- compare SkillClaw against a direct baseline on the same confirmation task,
- track `artifact_generated` and `artifact_execution_passed` in
  skill-level feedback,
- evaluate future skill revisions that aim to improve PoC/trigger support.
