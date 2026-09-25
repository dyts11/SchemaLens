# Paper Rewrite Plan

Section-by-section plan for the rewrite, following the paper's own structure.

## Abstract
- Tighten the contribution claim: this is a controlled cross-axis compensation test, not a
  restatement of "names matter" — the asymmetric substitution result is directional and
  non-obvious.
- Add a clause noting the finding survives stronger prompting methods and reproduces on a
  second benchmark (Spider).

## 1. Introduction
- Sharpen the contribution bullets into explicit non-obvious findings: (a) 1NF does not
  beat 3NF despite removing joins — semantic grounding is a bigger bottleneck than join
  generation; (b) metadata layered on top of 3NF (types, keys, FKs, join paths) gives
  little benefit vs. the normalisation step itself; (c) most semantic gain comes from
  S1→S2, with S2→S3 diminishing returns — nuances the claim that richer metadata
  consistently helps (Wretblad et al., 2024).
- State plainly that prior single-axis work cannot test cross-axis compensation, which is
  why the two-axis factorial design is necessary, not incidental.

- **Differentiating from schema linking** — frame the research question bidirectionally,
  not as "can structure fill the semantic gap" in isolation, since that phrasing alone
  sounds like an obvious yes/no:
  - State it as: does compensation between structure and semantics run both ways, one
    way, or neither? Three live prior possibilities (symmetric, asymmetric favouring
    semantics, asymmetric favouring structure) — only a crossed two-axis design can
    distinguish them, and asymmetry itself is the finding, not either half alone.
  - Schema linking asks "how much does accuracy degrade as identifiers get harder to
    link?" — a single-axis robustness question. This paper asks whether a *different*
    lever (relational structure) can substitute when linking is impaired, and vice versa
    — a compensation question no single-axis perturbation study can answer.
  - "Structure can't compensate" is not an obvious a priori answer: it contradicts the
    design premise of relational-graph schema-linking architectures (RAT-SQL, IRNet,
    LGESQL), which encode FK/relational structure specifically to help resolve ambiguous
    identifiers, and it contradicts a naive extrapolation of "richer metadata helps"
    (Wretblad et al., 2024).
  - The magnitude is the non-obvious part even where the direction feels guessable: the
    result is closer to near-total nullification (the same structural sweep yields a
    real gradient under S2/S3 but almost nothing under S1) than the partial compensation
    a reasonable prior would predict.
  - Structural metadata does not become vacuous under anonymised names — it still
    encodes topology/type information usable for valid joins/predicates independent of
    naming. Evidence: within S1, accuracy still rises with L (0.0%→9.8%, L1→L5) rather
    than staying flat, proving the two axes stay separable rather than collapsing into a
    single degenerate "schema linking" condition.
  - Foreshadow that the same "shouldn't this already be solved" objection gets sharper in
    §5.3/§5.4: DIN-SQL has an explicit schema-linking module by design, yet only
    partially recovers S1 accuracy; model scale is broadly assumed to fix such gaps, yet
    the S1→S2 gap grows with scale rather than shrinking — both push against specific,
    articulable priors, not a strawman.

## 2. Related Work
- Open with prior methods that improve text-to-SQL performance, sorted into three
  categories — this motivates the two-axis design (A/B) and previews §5.3's methods
  ablation (C):

  **A. Semantic-improving methods**
  - SNAILS (Luoma and Kumar, 2025) — identifier naturalness has a statistically
    significant effect on accuracy.
  - Dr.Spider (Chang et al., 2023) — renaming/abbreviation perturbations cause large
    accuracy drops.
  - Wretblad et al. (2024) — LLM-generated column descriptions consistently improve
    performance, even when redundant to human annotators.

  **B. Structural-improving methods** — emphasise claims of gains under weak/poor naming,
  since these are the prior expectations the paper's finding pushes against:
  - IRNet (Guo et al., 2019) — schema linking plus an intermediate structural
    representation, explicitly motivated by "the challenge in predicting columns caused
    by the large number of out-of-domain words" (vocabulary/naming mismatch).
  - Global reasoning over database structures (Bogin, Gardner, and Berant, 2019) —
    GNN message-passing over the schema graph specifically because "the local nature of
    decoding" fails to select correct constants; 39.4%→47.4% on Spider. Strongest single
    citation for "structure claimed to fix weak local/lexical grounding."
  - RAT-SQL (Wang et al., 2020) — relation-aware self-attention over PK/FK schema
    relations to resolve column-mention alignment; +8.7% absolute over prior best on
    Spider. (Hybrid — see note below.)
  - LGESQL (Cao et al., 2021) — line-graph-enhanced encoding of local/non-local schema
    relations. Cited from memory at moderate confidence; verify before finalising.
  - DAIL-SQL (Gao et al., 2023) — the most directly comparable prompted-LLM-era prior
    work: explicitly tested FK-in-prompt and found *mixed* results (helps some prompt
    formats/LLMs, hurts others) — even prior prompted-LLM work hadn't settled this,
    motivating a controlled test.
  - Kohita (2025) — 1NF–3NF normalisation levels.
  - Note: RAT-SQL and IRNet are technically hybrid architectures (a lexical/semantic
    linking score combined with structural relation encoding in one mechanism) — cited
    here specifically for the claim that their structural component is designed to
    compensate for weak grounding, not as pure single-axis work.

  **C. Both (semantic + structural combined)** — resolves where the pipeline/
  inference-time systems belong; also previews §5.3's methods ablation directly, since
  none of these change the schema representation itself, only how it's used:
  - DIN-SQL (Pourreza and Rafiei, 2023) — explicit schema-linking module plus
    decomposition/classification and self-correction.
  - RESDSQL (Li et al., 2023) — decouples schema linking (semantic ranking/filtering)
    from skeleton parsing (structural) as two explicit stages.
  - XiYan-SQL (Gao et al., 2024) — multi-generator ensemble combining schema
    representation choices with multiple generation strategies.
  - Chang and Fosler-Lussier (2023) — co-varies structural and semantic prompt
    attributes together, uncontrolled.

- State plainly: A and B each optimise one representation lever in isolation; C combines
  both but never as independently controlled, crossed variables. None tests whether the
  two axes interact, substitute, or complement — the direct motivation for the two-axis
  factorial design.
- Within A, concede that the semantic axis operationalises the same naming-quality
  property SNAILS/Dr.Spider study, but don't stop there — draw the research-paradigm
  distinction between A and B explicitly:
  - A (SNAILS, Dr.Spider, Wretblad et al.) intervenes on the *input*: rewrite the schema
    text (naming, descriptions) while the model/architecture stays fixed.
  - B (IRNet, RAT-SQL, LGESQL) intervenes on the *model*: build an explicit mechanism
    (a linking module, a relation-aware encoder) that processes a fixed schema
    representation differently.
  - Be precise about what this buys you: it shows A and B are different research
    designs, not that the underlying grounding-difficulty phenomenon they each address
    is necessarily different — that stronger claim rests on the persistence-at-S3
    evidence (Schema linking is still 23.6% of failures at L3·S3, the best naming
    condition tested), not on this paradigm distinction alone.
  - Bonus mechanism point, also worth cross-referencing in Limitations/Discussion:
    RAT-SQL/IRNet/LGESQL's "structure helps resolve ambiguous grounding" claim was
    established via *learned, architectural* access to structure (a relation-aware
    encoder trained on FK/PK edges) — a mechanism unavailable to a frozen, prompted
    LLM. L4–L6 can only deliver structure as *text* in the prompt, which the model must
    parse, retain, and apply through general in-context reasoning with no dedicated
    pathway. So the finding is not "RAT-SQL's premise was wrong" but "the benefit
    structure provides via a purpose-built learned mechanism doesn't transfer when the
    same facts are instead delivered as prompt text to a frozen model" — more precise
    than a flat contradiction, and it scopes the paper as testing something these
    architectures never tested (text-serialised structure in zero-shot prompted LLMs).
  - The contribution remains orthogonal to A regardless: crossing naming with an
    independently manipulated structural axis is a design no naming-only study
    produces, regardless of how "schema linking" is defined.
- Nuance Wretblad et al. (2024)'s "richer metadata helps" finding with the structural-axis
  result: metadata helps when it carries lexical/semantic content (generated
  descriptions), not when it's purely relational/topological (types, FKs, join paths) —
  which is what L4–L6 add and what the results show gives little benefit beyond
  normalisation itself.
- State the precise methodological gap in formal terms: none of A/B/C — single-axis,
  hybrid, or co-varying — can isolate an *interaction effect* between structure and
  semantics; only a crossed factorial design can. Name this as the contribution.
- Close with the concrete open question this fills: whether the two axes substitute for,
  complement, or act independently of each other.

## 3. Methodology
- **§3.2 Benchmark Setup (database filtering)** — state explicitly that
  `card_games`/`codebase_community` were excluded because denormalisation causes
  multiplicative row growth from independent one-to-many child tables (tens-of-GB
  intermediate tables, infeasible materialisation/query cost) — not selective omission.
  Add the complexity-variance argument: schema complexity is driven by table/column/FK
  count, not row count, so the exclusion doesn't reduce structural variance (Table 3
  already shows this range).
- **§3.3.2 Semantic Axis (S1 definition)** — reframe S1 explicitly as
  minimally-semantic-but-realistic, not content-free: column order is preserved because
  real anonymised exports typically preserve a consistent column order too. Fix the
  ambiguous sentence "columns without a predefined mapping retain original BIRD names" —
  clarify this applies only to the S2/S3 abbreviation-mapping process (e.g. untranslatable
  domain terms), not to S1, where every identifier is anonymised.
- **Appendix addition** — add an illustrative table showing the same schema transformed
  across all L1–L6 × S1–S3 conditions side by side (normalisation, metadata,
  relationships, join paths, naming) — a concrete worked example.

## 4. Evaluation Protocol
- Add the execution-based fairness argument explicitly: EX compares result sets, not
  surface SQL, so 1NF/2NF/3NF predictions are judged by the same standard regardless of
  denormalisation-induced duplicate rows.
- Cite the manual error analysis as direct evidence: failures are genuine model errors or
  inherent database challenges (e.g. duplicated rows the model must handle), not
  artifacts of comparing across schema forms.
- Resolve the L1/L2 framing: treat previously-flagged "eval artefact" failures as genuine
  model-facing difficulty from denormalised data (irrecoverable denorm failure ~10%,
  missing DISTINCT ~8.4% — real but modest, framed as the model's problem to solve, not
  the metric's) rather than a measurement flaw — drop/soften the "lower bound" framing
  accordingly.

## 5. Experiments

1. **5.1 Main Results** — core L×S compensation finding

   Question: does semantic and structural representation compensate for each other?

   Spider + BIRD main results (1–2 sentences on Spider as corroboration).

   - Comparing two axes
   - Semantics compensates for structure — unchanged
   - Effects across difficulty — trimmed to a sentence
   - Robustness across databases
   - Denormalisation ablation test

2. **5.2 Error Taxonomy and Annotation** — shared error instrument for 5.3/5.4

   Question: what errors does each L×S condition face, and does moving up an axis trade off
   error types instead of reducing them?

   Human-annotated samples calibrate an LLM classifier (report agreement); document the
   validation procedure and the resulting category table; must precede 5.3/5.4 so later
   claims aren't forward references to an undefined taxonomy.

3. **5.3 Stronger Text-to-SQL Methods** — fewshot, CoT, evidence, reflexion, dense
   retrieval, DIN-SQL (sparse/grep retrieval possibly later)

   Question: does the asymmetric substitution pattern reproduce across methods?

   Secondary: do methods specialise — does each one fix a different error category
   (DIN-SQL → join-plan/wrong-table via schema linking, dense retrieval → wrong-table via
   retrieval, reflexion → logic/literal via self-correction, CoT → none/negative) — or do
   they all act on the same errors?

4. **5.4 Model Capacity and Error Composition** — scaling curve + error-resolution order +
   method×scale interaction

   Question: does the asymmetric substitution pattern reproduce across model scale?

   Secondary: what's the error-resolution order as scale increases (which categories
   vanish first, which are scale-invariant), and does the best-performing method change
   with scale (e.g. a small model too weak to execute DIN-SQL's decomposition vs. a large
   model that benefits fully)? Operationalise via a reduced per-method-per-size sweep
   (e.g. zero-shot, DIN-SQL, evidence-hints across the full size ladder) rather than the
   full grid, to bound compute cost — this needs new experiments.

## 6. Conclusion
- Asymmetric substitution reproduces across benchmarks, methods, and model scale, and is
  mechanistically traceable to naming-hallucination errors that vanish exactly at the
  L2→L3 (3NF) transition.
- Reflect the resolved L1/L2 framing from §4 — no systematic evaluation bias.

## Appendix
- Schema-transformation worked example table (same schema across all 18 conditions).
- Full ablation-method result tables (fewshot/DIN/reflexion/dense retrieval by L and by
  S) if not promoted to main text by §5.3.
- denormalisation notice prompt
- Error-category validation table with a paragraph on the manual-then-LLM-classifier
  validation procedure, tying directly into §5.2.

## Minor fixes to carry along
- Fig. 1 caption says "across four models" but shows one model.
- Table 6 references sub-items (d)/(e) that don't exist.
- `docs/schema_size_1nf_2nf_3nf.md` is an empty stub, never filled in.




# Paper rewrite

## Related work
Prompt-based LLM pipelines now dominate Text-to-SQL leaderboards on Spider \citep{yu2018spider} and BIRD \citep{li2023can}, with systems such as DIN-SQL \citep{pourreza2023din}, DAIL-SQL \citep{gao2024dail}, and XiYan-SQL \citep{gao2024preview} relying on the serialised schema as their primary view of the database, and recent surveys \citep{liu2025survey} documenting the shift to this paradigm. \citep{chang2023prompt} systematically vary how the schema is rendered in the prompt, serialisation format, inclusion of sample content, and demonstration design, but co-vary structural and semantic attributes, so the contribution of each cannot be isolated.

Prior work that targets a single representation lever falls into two lines. On the structural side, several architectures are built on the explicit premise that relational structure can compensate for weak lexical grounding: IRNet \citep{guo2019irnet} introduces schema linking together with an intermediate structural representation specifically to address column-prediction failures caused by vocabulary mismatch between question and schema; \citep{bogin2019global} use graph-neural message-passing over the database schema precisely because purely local, lexically-driven decoding fails to select correct constants, raising Spider accuracy from 39.4\% to 47.4\%; RAT-SQL \citep{wang2020ratsql} encodes primary- and foreign-key relations via relation-aware self-attention to resolve column-mention alignment; and LGESQL \citep{cao2021lgesql} extends this with local and non-local schema relations via a line-graph encoder. \citep{kohita2025exploring} examines normalisation levels from 1NF to 3NF across eight LLMs, finding a query-type-dependent trade-off: denormalised schemas favour simple retrieval while normalised schemas better handle aggregation. In the prompted-LLM setting specifically, \citep{gao2024dail} test adding foreign-key metadata to the prompt and find the effect inconsistent — helping some prompt formats and models while hurting others — so even recent evidence has not settled whether structural metadata reliably compensates for weak identifier semantics.

On the semantic side, robustness benchmarks such as Dr.Spider \citep{chang2023drspider} show that even minor schema perturbations, abbreviating or renaming columns, cause large accuracy drops, implicitly implicating identifier semantics as a fragility source; SNAILS \citep{luoma2025snails} demonstrates that identifier naturalness has a statistically significant effect on accuracy across multiple LLMs and prompting workflows; and \citep{wretblad2024synthetic} show that augmenting prompts with LLM-generated column descriptions consistently improves performance, with richer metadata helping even when human annotators consider it redundant.

A smaller set of systems combines both levers without isolating either. DIN-SQL \citep{pourreza2023din} pairs an explicit schema-linking module with decomposition and self-correction; RESDSQL \citep{li2023resdsql} decouples schema linking from skeleton parsing as two separate stages but never manipulates either as an independently controlled variable; and XiYan-SQL \citep{gao2024preview} combines schema representation choices with a multi-generator ensemble. None of this work — single-axis or combined — crosses structure and semantics as two independently manipulated variables, so none can isolate whether the two interact: whether richer structure can rescue weakened semantic grounding, whether meaningful identifiers can compensate for weak structural exposure, or neither. We address this gap by crossing both axes in a single factorial design over a fixed BIRD-derived question set, with materialised 1NF/2NF variants to support the lowest structural levels.


## Emprical findings

### semantic axis

Figure~\ref{fig:qwen_heatmap} reveals that the semantic axis consists of two qualitatively different transitions. Our expectation is that each step of increasing semantic richness, from anonymous to abbreviations and from abbreviations to descriptive names, should yield further performance improvements.

\paragraph{Basic semantic grounding drives major gains.} Moving from anonymous column names ($S_1$) to curated abbreviations ($S_2$) produces a substantial improvement across nearly all structural levels. On BIRD, introducing basic semantic cues improves accuracy by approximately $20\%$ on average, with similar gains observed on Spider. This aligns with the expectation that anonymised schemas remove the lexical signals needed for schema linking.

\paragraph{Additional semantic richness add limited improvement.} In contrast, moving from curated abbreviations ($S_2$) to descriptive column names ($S_3$) provides only marginal improvements despite introducing richer natural language information. This result is unexpected, as more descriptive names should provide additional lexical signals that help the model resolve schema references. On BIRD, the additional semantic detail improves accuracy by only around $1\%$ across structural levels, and Spider exhibits the same trend. This suggests that once a schema provides sufficient semantic grounding for linking question concepts to columns, additional lexical richness provides limited benefits.

### structural axis

Figure~\ref{fig:qwen_heatmap} also reveals distinct patterns along the structural axis. Our expectation is that denormalised schemas (1NF) should outperform normalised schemas (3NF) due to reduced join complexity, while progressively adding structural metadata should further improve performance. This advantage of denormalisation is also expected to diminish when strong semantic naming is available.

\paragraph{Normalised Structure Provides the Large Structural Gain.} In practice, the dominant improvement comes from moving from denormalised and partially normalised schemas (1NF and 2NF) to a fully normalised schema with explicit table structure (3NF). On BIRD, this transition improves accuracy by approximately 8–10 percentage points under semantic settings ($S_2$–$S_3$), with similar gains observed on Spider. This suggests that explicit relational structure, even with the need for joins, provides a clearer organisational signal than flattened representations.

\paragraph{Metadata Benefits Vary Across Schema Settings.} In contrast, adding structural metadata beyond 3NF provides limited additional benefit on BIRD, with changes typically within 0–3 percentage points. However, Spider exhibits a different pattern: introducing foreign key relationships (L5) yields a substantial improvement of more than 10 percentage points, with smaller gains from explicit join paths (L6). This difference is consistent with the fact that Spider frequently uses non-identical column names for primary–foreign key pairs across tables, making join relationships harder to infer from naming alone. In such cases, explicit structural signals compensate for weaker lexical alignment, enabling more accurate schema linking across tables.

We next examine whether structural information can compensate for missing semantics by contrasting the two extreme corners of the design space. Figure~\ref{fig:diagonal} compares $L_1!\cdot!S_3$ (denormalised structure with descriptive names) against $L_6!\cdot!S_1$ (fully normalised structure with maximal metadata but anonymous names). Across both datasets, $L_1!\cdot!S_3$ consistently outperforms $L_6!\cdot!S_1$ by a substantial margin. This shows that semantic information and structural information are not interchangeable: meaningful column names allow the model to recover implicit relationships even in flattened schemas, whereas structural signals alone, including foreign keys and explicit join paths, are insufficient when no lexical grounding is available. The substitution is therefore one-directional, with semantics compensating for missing structure, but not vice versa.

