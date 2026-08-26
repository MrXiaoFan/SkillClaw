# 04. Paper Status, Completed Work, and TODO

## A. Current draft set

### 1. arXiv-stage concept paper

- File: [../skill_evolution_blind_vulnerability_analysis_arxiv.tex](../skill_evolution_blind_vulnerability_analysis_arxiv.tex)
- Role:
  - claim the research path;
  - explain why blind vulnerability-analysis agents need skill evolution rather than
    only static skill retrieval;
  - stay honest about what is and is not solved.

### 2. older `elsarticle` systems draft

- File: [../skillclaw_confirmation_feedback_elsarticle.tex](../skillclaw_confirmation_feedback_elsarticle.tex)
- Role:
  - preserve the more complete systems-style structure and older technical wording;
  - useful as a source of sections and phrasing, but not the best current paper line.

## B. What is already written well enough to reuse

- Problem framing: blind vulnerability analysis plus evolving reusable skills.
- Prototype lifecycle: run -> score -> feedback -> candidate -> gate -> publish.
- Honest limitation framing: candidate generation is easier than deciding publication.
- Related-work baseline around agent skill learning, self-improvement, and vulnerability
  analysis.

## C. What still needs to be improved in the manuscript

### 1. Benchmark protocol wording

The paper still needs a very clean explanation of the difference between:

- all historical repository cases,
- currently trusted main firmware experiments,
- auxiliary older experiments kept only as supporting context.

### 2. Experiment hierarchy

The manuscript still needs one explicit section that says:

- which experiments are main evidence,
- which are diagnostic or historical,
- why some earlier experiments were superseded by later cleaner reruns.

### 3. Failure analysis

The paper still needs sharper writing around:

- decoy drift,
- family dependence,
- why FH451 becomes worse under a more discriminative skill,
- why gate/publish cannot yet be used as proof of stable improvement.

### 4. Final claims discipline

The paper should not say:

- stable autonomous skill improvement is solved,
- published candidate skills are already validated gains,
- the system currently discovers unknown vulnerabilities end-to-end.

It can say:

- the research problem is real and underexplored,
- the lifecycle can be instantiated in a working prototype,
- skill conditions materially affect blind-analysis outcomes,
- publication control is a first-class research problem.

## D. Recommended next writing steps

1. Keep the arXiv draft as the primary active manuscript.
2. Pull only useful structural pieces from the older `elsarticle` draft.
3. Replace generic experiment descriptions with the frozen necessity and
   family-dependent evidence now copied into this package.
4. Add one compact benchmark table and one compact result table based on the files in
   [03_experiment_index_and_key_results.md](03_experiment_index_and_key_results.md).
5. Add a short "what is still unsolved" subsection near the end of the experiments or
   discussion section.

## E. Recommended next engineering steps tied to the paper

1. tighten the gate story so the paper can describe a clearer publication rule;
2. reduce noisy historical artifacts and live-skill clutter so experiment provenance is
   easier to defend;
3. if new experiments are run, append them under `paper/materials_YYYYMMDD/` rather than
   scattering them back across the repository first.
