# 02 Paper Frame and Manuscript State

## 1. Most viable paper idea now

The most viable paper is **not**:

- "we already proved evolved skills improve vulnerability discovery,"
- or "we already proved a single skill is necessary for a firmware exploit."

The most viable paper **is**:

**an evidence-grounded skill evolution framework for vulnerability analysis, plus pilot evidence about what the lifecycle can already do and what still blocks real publication.**

This framing is viable because the current repository already supports four strong claims:

1. blind analysis tasks can be run through SkillClaw with auditable skill exposure,
2. results can be externally checked through structured validators or confirmation chains,
3. run results can be transformed into run-skill feedback and candidate revisions,
4. unsafe or weak candidate revisions can be blocked before they affect live skills.

That is already a coherent systems-and-method paper.

## 2. What the paper should claim now

### 2.1 Claims that are supportable now

The manuscript can currently claim:

1. a full vulnerability-oriented skill lifecycle exists end to end,
2. the system records more than conversation logs: it records skill exposure, scored outcomes, external evidence, and gate results,
3. changing skill exposure changes blind-analysis behavior on firmware CGI cases,
4. the publication gate prevents low-confidence or mismatched revisions from contaminating the live skill library.

### 2.2 Claims that should not be made yet

The manuscript should not yet claim:

1. evolved skills already improve held-out tasks,
2. skill contribution has been causally proven,
3. the framework already generalizes to arbitrary firmware targets with little case engineering,
4. the current feedback loop already performs stable autonomous live-skill upgrades.

## 3. Recommended paper structure

### Section 1. Introduction

Explain the real problem:

- LLM vulnerability agents can sound plausible even when wrong.
- In this domain, conversation success is too weak as a learning signal.
- Therefore skill evolution must be tied to external evidence.

### Section 2. Problem Formulation

Define the unit of learning as:

- task input,
- selected skills,
- agent trajectory,
- final answer,
- external evidence,
- run-skill feedback outcome.

The key distinction is between:

- task correctness,
- confirmation strength,
- and skill relevance.

### Section 3. Framework

Describe the lifecycle:

1. blind task execution,
2. skill selection and injection,
3. scoring and external confirmation,
4. finalized run record,
5. feedback bundle,
6. candidate revision,
7. validation gate,
8. live publication or rejection.

This section is the core contribution.

### Section 4. Prototype Realization

Map the framework to real modules:

- `skillclaw/`
- `evolve_server/`
- `evaluation/`
- `skillspace/`
- `reports/`

The point is not to enumerate files mechanically, but to show the separation between:

- analysis plane,
- evidence plane,
- evolution plane,
- and live skill space.

### Section 5. Experimental Methodology

The methodology should be honest about current maturity.

It should include two evidence sets:

1. **core six-case remote blind runset**
2. **firmware skill-ablation study**

The immediate RQs should be:

- RQ1: can the framework close the loop from blind analysis to gated skill revision?
- RQ2: does changing exposed skill content change blind-analysis quality?
- RQ3: what currently prevents candidate revisions from becoming live skills?
- RQ4: what experiments are still needed to prove necessity and held-out transfer?

This is better aligned with current evidence than a premature before/after-improvement claim.

### Section 6. Current Evidence

Split this section into two parts:

1. six-case current runset:
   - shows task quality, evidence class, and candidate/gate outcomes
2. firmware ablation:
   - shows that different skill profiles produce measurably different blind-analysis behavior

### Section 7. Discussion

The discussion should explicitly say:

- the current contribution is the lifecycle and its observability,
- not yet a proven post-evolution performance gain.

This is where to discuss:

- candidate/live separation,
- mismatch filtering,
- skill attribution,
- cost of confirmation engineering,
- and the need for stricter necessity experiments.

### Section 8. Threats and Limits

Important threats to keep:

- answer leakage,
- small benchmark scope,
- attribution ambiguity,
- validator/oracle engineering cost,
- lack of accepted live publication examples so far.

### Section 9. Conclusion

End with the right scope:

- the framework already creates trustworthy evolution artifacts,
- the next milestone is to prove accepted publication and held-out improvement.

## 4. What was changed in the current paper draft

The paper draft is:

- `paper/skillclaw_confirmation_feedback_elsarticle.tex`

The draft was updated in this session to better match current evidence.

The intended changes are:

1. move the framing toward an evidence-grounded lifecycle paper,
2. replace outdated "three representative runs" framing with current six-case + firmware-ablation framing,
3. make the methodology and claims more conservative,
4. explicitly preserve the distinction between:
   - feedback generated,
   - candidate produced,
   - gate accepted,
   - live skill published.

## 5. How the current manuscript should be used

The current manuscript should be treated as a **research framing draft**, not a final camera-ready paper.

Its job is to:

- lock the correct story,
- prevent overclaiming,
- and define exactly which experiments are still missing.

## 6. Next paper-facing experiments needed

Priority order:

1. get at least one candidate revision to pass the gate and become a published live skill,
2. freeze a before snapshot and an after snapshot of the live skill library,
3. rerun a held-out set under:
   - no skill,
   - baseline live skill,
   - evolved live skill,
4. run a stricter firmware necessity experiment:
   - target skill,
   - no skill,
   - wrong skill,
   - degraded target skill,
5. measure both task quality and acceptance/publication outcomes.

Without these experiments, the paper can argue lifecycle realism, but not evolution efficacy.

## 7. Instruction to the next agent

If you continue paper work, do not start by adding more prose.
Start by checking whether the manuscript claims are exactly consistent with:

- `reports/current/runset.md`
- `reports/current/result_matrix.md`
- `reports/current/briefing_20260805/summary.md`
- `reports/current/briefing_20260805/closed_loop_proof.csv`

The paper should follow the evidence, not the other way around.
