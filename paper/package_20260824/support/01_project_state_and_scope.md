# 01. Project State and Scope

## Research goal

The current research direction is not just "use skills in vulnerability analysis", but
"let a vulnerability-analysis agent evolve reusable skills from real blind runs".

The target lifecycle is:

1. run a blind vulnerability-analysis task in a remote environment;
2. record what skill was selected and what conclusion the model produced;
3. score and externally check the result on the local side;
4. turn the run into structured feedback;
5. let the evolution service propose a candidate skill update;
6. gate that candidate before it can enter the live skill library.

The paper should therefore focus on the combination of:

- blind vulnerability analysis,
- reusable skill injection,
- run-derived feedback,
- candidate generation,
- publication control.

## Engineering goal

The engineering target is a confirmation-aware extension on top of the original
SkillClaw workflow. The core added value is not only "retrieve a skill and inject it",
but "decide whether a completed run should change the reusable skill library".

## Current status

### What is already done

- The remote blind-analysis chain has been run for real on source-code and firmware
  cases.
- The repository now has benchmark case definitions, blind workspace preparation,
  scoring, postprocessing, feedback construction, evolve-side candidate generation, and
  gate-side validation/publish logic.
- Firmware experiments have already shown that changing the skill condition can change
  which vulnerable function the model lands on.
- A curated paper draft already exists and can be continued from a research angle.

### What is not solved yet

- Candidate generation does not yet imply real improvement.
- Gate acceptance still does not provide strong enough evidence that a published skill
  will help future blind runs.
- Some historical experiments were later found to be too optimistic or partly polluted,
  so the paper must separate old supporting evidence from newer cleaner evidence.

## Difference from original SkillClaw

The original SkillClaw mostly provides:

- a local proxy/API server,
- a skill manager and live skill directory,
- a sharing/evolve mechanism,
- a dashboard.

This project extends it with a benchmark-driven vulnerability-analysis layer:

- `benchmarks/cases/`: explicit vulnerability-analysis cases and ground truth
- `evaluation/utils/`: blind workspace and prompt generation
- `evaluation/runs/`: local/remote experiment execution and scoring
- `evaluation/postprocess/`: run finalization into structured records
- `evaluation/reporting/feedback/`: feedback and gate-report generation
- `evaluation/confirmation/` and `evaluation/validation/`: oracle-side checks
- evolve-side validated publish flow for candidate skills

## Current paper position

The strongest honest claim today is:

1. the problem setting is real and underexplored;
2. the repository contains a working prototype for this lifecycle;
3. blind firmware experiments show that skill choice can materially alter vulnerability
   localization outcomes;
4. the hard part is no longer "can we generate candidate skills at all", but "how can
   we decide which candidate skill should actually become live".

That is enough for a first arXiv-style "claim the problem and path" manuscript, but not
enough yet for a strong final paper claiming stable autonomous skill improvement.
