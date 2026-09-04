# Server-catalog versus inline lexical — F9K WISP5G

## Controlled comparison status

Both conditions used the same F9K WISP5G case, remote VM, model, live skill count (36), and
three-repeat structure. The experiment is still a single-case comparison and is not sufficient
for a general effectiveness claim.

| Condition | Runs | Scores | Mean | Selected skill pattern |
| --- | ---: | --- | ---: | --- |
| `server-catalog` | 5 (`r1`–`r5`) | 2.0, 2.0, 2.0, 2.0, 2.0 | 2.0 | command-injection skill, stable but wrong domain |
| `server-inline-lexical` (`inline`) | 3 (`r1`–`r3`) | 4.5, 2.0, 2.0 | 2.833 | `windows-dotnet-cmd-injection-triage`, stable but wrong domain |

## Interpretation

- `inline` produced a higher mean on this case, but its first run was an outlier; the other two
  runs matched the server-catalog score.
- Neither condition selected the expected F9K buffer-overflow skill or recovered the target
  function/evidence consistently.
- The result currently demonstrates selection instability/mismatch, not superiority of either
  method.
- The `server-catalog` final artifacts include auditable selector traces. The `inline` artifacts
  record server-side lexical injection metadata but have no model selector trace by design.

## Next experiment

Repeat the same matrix on an additional case family, preferably one where the expected skill is
known and differs clearly from the command-injection skills. Keep the current F9K results as a
negative diagnostic rather than tuning the method against this case alone.
