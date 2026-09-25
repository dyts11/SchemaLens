# Paper Revision Plan — Rebuttal Response Actions

Action items for every section other than Section 5 (see `section5_restructure_plan.md`
for that), derived from the rebuttal responses. Three reviewers' weaknesses are labeled
R1/R2/R3 below (their W-numbers overlap/repeat across reviewers, so re-numbered here for
traceability):

- **R1**: W1 L1/L2 eval setting, W2 benchmark scope, W3 stronger text2sql systems, W4 LLM
  error-annotation validation, W5 anonymity in S1.
- **R2**: W1 single-benchmark scope, W2 few-shot generalisation, W3 L1/L2 eval validity.
- **R3**: W1 novelty, W2 goes-beyond-schema-linking, W3 schema-transformation clarity.

## Abstract
- Tighten the contribution claim per R3-W1: this is a controlled cross-axis compensation
  test, not a restatement of "names matter" — the asymmetric substitution result is
  directional and non-obvious, not assumed.
- Consider one clause noting the finding survives stronger prompting methods and a second
  benchmark (Spider), once 5.1/5.3 land — makes the abstract match the strengthened paper.

## 1. Introduction
- Sharpen the contribution bullets per R3-W1 into explicit non-obvious findings, not just
  "we vary two axes": (a) 1NF does not beat 3NF despite removing joins — semantic grounding
  is a bigger bottleneck than join generation; (b) metadata layered on top of 3NF (types,
  keys, FKs, join paths) gives little benefit vs. the normalisation step itself; (c) most
  semantic gain comes from S1→S2, with S2→S3 diminishing returns — nuances Wretblad et al.
  (2024)'s claim that richer metadata consistently helps.
- State plainly (per R3-W1[1]) that prior single-axis work *cannot* test cross-axis
  compensation, which is why the two-axis factorial design is necessary, not incidental.

## 2. Related Work
- Add an explicit paragraph distinguishing the semantic axis from schema-linking sensitivity
  per R3-W2: prior work shows naming affects grounding; this paper asks whether *structure*
  can rescue *weakened* grounding — a different, untested question. Cite the asymmetric
  answer (L6·S1 still fails, L1·S3 still succeeds) as the distinguishing result.
- Add a few supporting references to sharpen this distinction (R3-W2[3] promises "several
  additional references" — source these before the revision).

## 3. Methodology
- **§3.2 Benchmark Setup (database filtering)** — per R1-W2: state explicitly that
  `card_games`/`codebase_community` were excluded because denormalisation causes
  multiplicative row growth from independent one-to-many child tables (tens-of-GB
  intermediate tables, infeasible materialisation/query cost) — not selective omission. Add
  the complexity-variance argument: schema complexity is driven by table/column/FK count,
  not row count, so the exclusion does not reduce structural variance (Table 3 already
  shows this range).
- **§3.3.2 Semantic Axis (S1 definition)** — per R1-W5: reframe S1 explicitly as
  *minimally-semantic-but-realistic*, not content-free — column order is preserved because
  real anonymised exports typically preserve a consistent column order too. Also fix the
  ambiguous sentence "columns without a predefined mapping retain original BIRD names" —
  clarify this applies only to the S2/S3 abbreviation-mapping process (e.g. untranslatable
  domain terms), not to S1, where every identifier is anonymised. This was flagged as a
  real source of reviewer confusion.
- **Appendix addition** — per R3-W3: add an illustrative table showing the *same* schema
  transformed across all L1–L6 × S1–S3 conditions side by side (normalisation, metadata,
  relationships, join paths, naming) — concrete worked example, not new methodology.

## 4. Evaluation Protocol
- Per R1-W1 and R2-W3 (same underlying concern, both reviewers): add the execution-based
  fairness argument explicitly — EX compares result sets, not surface SQL, so 1NF/2NF/3NF
  predictions are judged by the same standard regardless of denormalisation-induced
  duplicate rows.
- Cite the 60-sample manual error analysis as direct evidence: failures are genuine model
  errors or inherent database challenges (e.g. duplicated rows the model must handle), not
  artifacts of comparing across schema forms.
- **Open tension to resolve before writing this**: the rebuttal's line ("L1/L2 accuracies
  are not underestimated and should not be treated as lower bounds") is a harder claim than
  what's in the existing docs notes (`docs/error_analysis/gemini_L1S3_wrong_answer_sample50.md` categorises
  ~33% of Gemini L1·S3 failures as "unrecoverable eval artefact"). Pick one consistent
  framing: either (a) reclassify those as "genuine model-facing difficulty from denormalised
  data" rather than "evaluation artifact" — matching the rebuttal and R1-W4's category table
  (Irrecoverable denorm failure 10%, Missing DISTINCT 8.4% — real but modest, and framed as
  the model's problem to solve, not the metric's), or (b) keep the lower-bound caveat but
  soften its weight. Recommend (a) — it's the more defensible, already-drafted position and
  avoids conceding a methodological flaw.

## Limitations
This section absorbs most of the rebuttal — nearly every "weakness" maps to a Limitations
rewrite rather than a new claim elsewhere:
- L1/L2-as-lower-bound caveat → revise per the resolved framing above (R1-W1, R2-W3):
  state the manual analysis found no systematic evaluation bias.
- Single-benchmark limitation → soften per R1-W2/R2-W1: Spider reproduces the qualitative
  trend (same monotonic L1→L6 rise, same S1→S2 jump then plateau, same model ranking) —
  already scoped into 5.1 per the Section 5 plan; keep a residual caveat that magnitude may
  still vary with schema complexity.
- Two excluded databases → strengthen with the computational-infeasibility + complexity-
  variance argument from R1-W2, rather than leaving it as a bare exclusion note.
- Zero-shot-only design → keep as a stated deliberate choice (isolating schema
  representation cleanly), now backed by the methods-ablation result (R1-W3/R2-W2): the
  core conclusions hold under fewshot/DIN/reflexion/dense retrieval too.
- S1 ordering-leak caveat → reframe per R1-W5 as an intentional realism choice with
  evidence it doesn't materially affect conclusions (large S1 vs. S2/S3 gap persists),
  rather than purely a weakness to apologise for.

## Appendix
- Schema-transformation worked example table (R3-W3).
- Full ablation-method result tables (fewshot/DIN/reflexion/dense retrieval by L and by S)
  from R1-W3, if not promoted to main text by the Section 5 plan.
- Full Spider vs. BIRD comparison table (R1-W2/R2-W1) if not promoted to main text.
- Error-category validation table (R1-W4: wrong table 11.7%, wrong column 26.7%, wrong join
  plan 0%, wrong query logic 55.0%, missing DISTINCT 8.4%, irrecoverable denorm failure
  10%) with a short paragraph on the manual-then-LLM-classifier validation procedure —
  ties directly into 5.2's taxonomy section from the Section 5 plan.

## Conclusion
- No new content needed beyond what's already in the Section 5 plan's Conclusion bullet
  (reproduces across benchmarks/methods/scale); just make sure the wording there reflects
  the resolved L1/L2 framing above.
