# Server-catalog controlled experiment protocol — 2026-09-03

## Scope

This protocol evaluates whether server-side catalog selection improves skill choice and
downstream blind-task performance. It does not treat Claude's internal skill-selection behavior
as observable white-box evidence.

The arXiv concept manuscript may proceed independently. Until this protocol is completed, the
manuscript should describe `server-catalog` as implemented infrastructure and an open evaluation
question, not as a demonstrated improvement.

## Conditions

Use the same case, task text, upstream model, skill snapshot, and repeat count for every condition.

| Condition | Selector owner | Body delivery | Role |
| --- | --- | --- | --- |
| `no-skill` | none | none | lower baseline |
| `server-inline-lexical` (`inline`) | SkillClaw server rules/topK | server injects bodies | current retrieval baseline |
| `model-side-catalog` | downstream model | model lazy-loads from catalog | compatibility/ablation baseline |
| `server-catalog` | SkillClaw server selector | server injects selected bodies | main research condition |
| `server-catalog-fallback` | server selector, then lexical fallback | server injects bodies | robustness condition |

Do not mix `model-side-catalog` and `server-catalog` under one label named simply `catalog`.
The experimental label `server-inline-lexical` maps to the actual configuration
`skills.injection_mode=inline`.

## Required per-turn record

The existing `skill_injection` record should contain or be accompanied by:

- `injection_mode`
- `selection_source`
- `available_skill_count`
- `selected_skill_names`
- `server_catalog_trace.status`
- `server_catalog_trace.raw_selected_skill_names`
- `server_catalog_trace.unknown_selected_skill_names`
- `server_catalog_trace.truncated`
- skill prompt hash and character count
- downstream task outcome and scoring fields

## Primary metrics

1. Selection Precision@1 and Recall@3 against a predeclared relevant-skill label set.
2. Downstream CVE, file, function, root-cause, and evidence hit rates.
3. Overall score, prompt size, selector latency, selector error rate, and fallback rate.

## Interpretation rules

- Correct delivery with an irrelevant selected skill is not evidence of effective selection.
- A stable wrong selection is still a selection failure.
- Downstream improvement without improved selection metrics must be reported as an ambiguous result.
- Results from old 159-run aggregates remain historical preservation evidence and are not silently
  reclassified as this controlled comparison.

## Current known result

The F9K WISP5G rerun established that `server-catalog` delivery works end-to-end, but selected
`embedded-cgi-command-injection-triage` for a buffer-overflow task and scored 2.0/10 in all three
runs. It is therefore an implementation/negative-observation result, not evidence of improvement.
