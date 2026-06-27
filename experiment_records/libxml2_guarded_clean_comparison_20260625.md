# libxml2 Guarded Clean Comparison - 2026-06-25

## Case

Benchmark case: `libxml2-2.9.4-cve-2017-8872`.

Target vulnerability: an out-of-bounds read in the libxml2 HTML parser state machine. Ground truth is `HTMLparser.c::htmlParseTryOrFinish`, where the parser checks an insufficient `avail` bound before reading lookahead bytes such as `in->cur[2]` and `in->cur[3]`.

## Compared Runs

### SkillClaw Inline Guarded Clean, Low Budget

- Run id: `libxml2-skillclaw-guarded-clean-20260625-184107`
- Session id: `782586fd-3c20-4cf3-b63c-04a1228d4266`
- Budget: `$0.35`
- Result: budget exhausted before final answer
- Cost: `$0.376386`
- Turns: `12`
- Score: `0.0 / 10.0`

This run did not produce a scoreable final JSON answer. It is treated as an execution-control failure, not as an incorrect localization result.

### SkillClaw Inline Guarded Clean, High Budget

- Run id: `libxml2-skillclaw-guarded-clean-highbudget-20260625-184613`
- Session id: `2d51c367-df63-4fae-8405-99403b464c06`
- Budget: `$0.80`
- Result: completed successfully
- Cost: `$0.418271`
- Turns: `16`
- Score: `8.0 / 10.0`

Injected and pinned skills:

```text
source-parser-state-machine-oob
elf-cwe120-firmware-triage
vuln-hunting
```

The answer correctly identified `HTMLparser.c`, `htmlParseTryOrFinish`, the insufficient `avail` guard, and the `in->cur[2]` / `in->cur[3]` lookahead-read pattern. It missed the exact CVE identity, predicting `CVE-2016-1839` and `CVE-2015-7942` instead of `CVE-2017-8872`.

### Direct DeepSeek Guarded Clean, Low Budget

- Run id: `libxml2-direct-guarded-clean-20260625-185708`
- Session id: `1b5523df-81a4-4a0d-b717-29244da4befc`
- Budget: `$0.35`
- Result: budget exhausted before final answer
- Cost: `$0.366069`
- Turns: `9`
- Score: `0.0 / 10.0`

This run also failed because it did not produce a final answer before the budget limit.

### Direct DeepSeek Guarded Clean, High Budget

- Run id: `libxml2-direct-guarded-clean-highbudget-20260625-185907`
- Session id: `630a0706-576f-4eef-a666-1a0e69e31929`
- Budget: `$0.80`
- Result: completed successfully
- Cost: `$0.304523`
- Turns: `11`
- Score: `10.0 / 10.0`

The direct run correctly identified the CVE, target file, target function, evidence pattern, and root cause. It found the same insufficient `avail < 2` guard before reads of `in->cur[2]` and `in->cur[3]`.

## Interpretation

This case is a useful counterexample to a simple "SkillClaw is always better" claim. Under the low-budget setting, both SkillClaw and direct DeepSeek failed to produce a final answer. Under the high-budget setting, direct DeepSeek achieved `10/10`, while SkillClaw achieved `8/10` because it localized the bug correctly but predicted the wrong CVE family.

The result suggests that current SkillClaw injection can help structure analysis, but it may also bias the model toward neighboring vulnerability patterns or older learned examples. For research framing, this is more valuable than a one-sided win: it shows that skill quality should be evaluated not only by whether the answer looks detailed, but also by whether the injected skill improves exact localization and CVE calibration against a baseline.

## Research Implications

Current evidence supports a more cautious research question:

```text
When do task-specific injected skills improve vulnerability localization, and when do they bias the agent toward plausible but wrong vulnerability identities?
```

The next engineering step is to make the validation loop report this kind of negative signal automatically: if an injected skill helps file/function/root-cause localization but hurts CVE identity, the feedback should not simply mark the skill as positive. It should flag "localization positive, identity calibration negative" so that later skill evolution can refine the skill instead of blindly promoting it.

## Matrix Files

The comparable runs are summarized in:

```text
experiment_records/experiment_matrix_20260625.md
experiment_records/experiment_matrix_20260625.csv
```
