## giflib Confirmation Compare - 2026-07-01

### Compared Runs

- SkillClaw:
  `experiment_records/remote_runs/giflib-confirmation-20260701/giflib-skillclaw-confirmation-20260701-postvalidate3-final.json`
- Direct baseline:
  `experiment_records/remote_runs/giflib-confirmation-20260701/giflib-direct-confirmation-20260701-final.json`

### Summary Table

| Mode | Model | Score | CVE | File | Function | Artifact Exists | Artifact Exec | ASan |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| `skillclaw-inline-guarded` | `skillclaw-model` | `10/10` | `CVE-2016-3977` | `util/gif2rgb.c` | `DumpScreen2RGB` | passed | passed | passed |
| `direct-deepseek-guarded` | `deepseek-v4-pro` | `10/10` | `CVE-2016-3977` | `util/gif2rgb.c` | `DumpScreen2RGB` | passed | passed | passed |

### Key Observation

Both runs succeeded on the full confirmation chain:

1. source-level localization,
2. trigger artifact presence,
3. artifact execution with expected crash,
4. ASan-backed dynamic confirmation.

This means the updated confirmation contract is strong enough to elicit
reproducible trigger artifacts from both the SkillClaw path and the direct
baseline on this case.

### Why This Result Matters

This is still a positive milestone for the framework, but it also changes
how we should interpret the case:

- `giflib` is now a **confirmation-capable benchmark** rather than just a
  localization benchmark;
- however, it is **not currently separating SkillClaw from the direct
  baseline**, because both systems can complete the full task successfully.

In other words, this run validates the new artifact-aware evaluation
pipeline, but it does **not** provide evidence that SkillClaw is better than
the direct baseline on this particular confirmation task.

### Research Takeaway

The main value of this result is methodological:

- it confirms that our framework can measure
  `artifact_generated`, `artifact_execution_passed`, and sanitizer-backed
  confirmation in a real case;
- it also shows that some cases may become "too easy" once the confirmation
  contract is explicit, so future comparative experiments should use:
  - harder confirmation tasks,
  - tighter artifact constraints,
  - or revised skills whose gains are expected in more selective dimensions.

### Next Step

Use `giflib` as the first completed confirmation baseline, then move the
comparative part of the study back to a case with stronger separation
potential, such as:

- `libxml2` for template-driven revision and CVE calibration, or
- a new confirmation case where trigger construction is less directly guided.
