# tcpdump Guarded Clean Comparison - 2026-06-25

## Case

Benchmark case: `tcpdump-4.9.1-cve-2017-13031`.

Target vulnerability: IPv6 fragmentation header parser buffer over-read. Ground truth is `print-frag6.c::frag6_print`, with insufficient `ND_TCHECK` coverage before later reading `ip6f_ident`.

## Compared Runs

### SkillClaw Inline Guarded Clean

- Run id: `tcpdump-skillclaw-guarded-clean-20260625-152601`
- Session id: `9e7e45c8-6f15-49cb-9d0a-4d69c4e0770b`
- Output: `experiment_records/remote_runs/tcpdump-skillclaw-guarded-clean-20260625-152601.claude.json`
- Budget: `$0.35`
- Result: completed successfully
- Cost: `$0.271084`
- Turns: `9`
- Score: `8.0 / 10.0`

Injected and pinned skills:

```text
source-parser-state-machine-oob
elf-cwe120-firmware-triage
vuln-hunting
```

The answer correctly found `print-frag6.c`, `frag6_print`, the insufficient `ND_TCHECK` guard, and the `ip6f_offlg` to `ip6f_ident` over-read pattern. It missed the exact CVE id, predicting `CVE-2017-13005` instead of `CVE-2017-13031`.

### Direct DeepSeek Guarded Clean

- Run id: `tcpdump-direct-guarded-clean-20260625-153929`
- Session id: `16c9e882-a86d-4f17-8a41-adc1e99f337a`
- Output: `experiment_records/remote_runs/tcpdump-direct-guarded-clean-20260625-153929.claude.json`
- Budget: `$0.35`
- Result: budget exhausted before final answer
- Cost: `$0.351918`
- Turns: `10`
- Score: `0.0 / 10.0`

The direct run used the same clean-room and final-answer guard constraints, but did not produce a final JSON prediction before hitting the budget. This is scored as an execution-control failure rather than a wrong localization answer.

### Direct DeepSeek Guarded Clean With Higher Budget

- Run id: `tcpdump-direct-guarded-clean-highbudget-20260625-170940`
- Session id: `942c0ad4-188c-48a5-9eb3-de9e6879158f`
- Output: `experiment_records/remote_runs/tcpdump-direct-guarded-clean-highbudget-20260625-170940.claude.json`
- Budget: `$0.80`
- Result: completed successfully
- Cost: `$0.270181`
- Turns: `7`
- Score: `8.0 / 10.0`

The high-budget direct run found the same file, function, and root cause pattern as the SkillClaw run, but also missed the exact CVE id. It predicted `CVE-2017-12932` instead of `CVE-2017-13031`.

### Excluded Invalid Direct Run

The earlier run `tcpdump-direct-guarded-clean-20260625-153656` is excluded. Remote `print_case_prompt.py` had not yet been updated, so `direct-deepseek-guarded` was not recognized and the generated prompt was incomplete.

## Interpretation

This comparison gives a narrow but useful result:

```text
Under the same target, VM, Claude Code interface, guarded prompt style, and $0.35 budget, SkillClaw produced a scoreable vulnerability-localization answer while direct DeepSeek did not. With a higher direct budget, DeepSeek also produced a scoreable answer and reached the same 8/10 localization score.
```

The result should not be overclaimed. The strongest current evidence is not that SkillClaw is universally better at vulnerability reasoning, but that session-stable injected skills can improve task steering and answer production under constrained budgets. Both SkillClaw and direct DeepSeek still failed CVE identity calibration while correctly identifying the vulnerability location and root cause.

## Research Implications

This supports a research question around controlled skill injection:

```text
Can task-specific, session-stable skill injection improve vulnerability localization efficiency and evidence quality under constrained agent budgets, even when the base model can solve the same case with more relaxed execution conditions?
```

The next step should repeat this pattern on `libxml2-2.9.4-cve-2017-8872` and at least one additional target. The tcpdump result now separates "cannot solve" from "less efficient or less reliable under the same budget."

## Matrix Files

The three comparable runs are summarized in:

```text
experiment_records/experiment_matrix_20260625.md
experiment_records/experiment_matrix_20260625.csv
```
