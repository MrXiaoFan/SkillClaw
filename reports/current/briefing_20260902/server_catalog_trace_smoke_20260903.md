# Server-catalog trace smoke — 2026-09-03

## Result

After restarting SkillClaw with the latest code, one real local request completed successfully
through `server-catalog` and produced an auditable selection record.

```text
mode=server-catalog
catalog_count=36
trace_status=ok
selected=cwe120-analysis-verification
unknown=[]
truncated=False
```

The API request returned HTTP 200. This is an instrumentation and end-to-end delivery smoke
check only; it is not included as a formal downstream effectiveness sample.

## Significance

The server now records enough selector information to distinguish a valid selection from an
unknown-name filter, top-3 truncation, malformed response, service error, or missing call-path
trace. Formal comparison remains pending under the controlled protocol.

## Post-cache regression smoke

After the server-catalog session-cache fix, two request-level runs were checked:

| Case | History turns | Injection modes | Stable actions | Final selected skill |
| --- | ---: | --- | --- | --- |
| WlanSetup | 8 | all `server-catalog` | all `server-select` | `elf-cwe120-firmware-triage` |
| WISP5G | 5 | all `server-catalog` | all `server-select` | `elf-cwe120-firmware-triage` |

Both traces were `ok`. No history turn reused the lexical `inline` cache. These runs are
engineering regression checks, not additional formal effectiveness samples. The earlier v4
benchmark results remain useful for selection-quality diagnosis, but their multi-turn metadata
should not be treated as cache-consistent formal evidence without rerunning the benchmark.
