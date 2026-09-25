# Section 5 (Experiments) Restructure — Storyline Discussion

## Motivating idea

The original paper's spine is **asymmetric substitution**: semantic naming quality
compensates for missing structure, but structural metadata does not compensate for
opaque names. The new sections extend this same substitution question to two more
levers — **inference-time method** and **model capacity** — asking whether either of
them can play the compensating role that semantics plays, or whether the same asymmetry
reappears. This gives Section 5 one throughline instead of three independent studies
sharing a paper.

## Section order

1. **5.1 Main Results** — core L×S compensation finding

   Question: does semantic and structural representation compensate for each other?

   Spider + BIRD main results.

   Paragraphs:

     -- comparing two axes
     -- semantics compensates for structure
     -- effects across difficulty
     -- robustness across databases

2. **5.2 Error Taxonomy and Annotation** — shared error instrument for 5.3/5.4

   Question: what errors does each L×S condition face, and does moving up an axis trade off error types instead of reducing them?

   Human-annotated samples calibrate an LLM classifier.

    update this section with human-annotated error samples, and an LLM-tuned categorisation based on the annotated sample.

3. **5.3 Stronger Text-to-SQL Methods** — fewshot, CoT, evidence, reflexion, dense retrieval, DIN-SQL

   Original framing: this section focuses on experiments using different text-to-SQL systems — prompting methods, demonstration, retrieval, self-correction; show results for fewshot/CoT/evidence/reflexion/dense retrieval/DIN-SQL, add sparse and grep retrieval later; do analysis on error types, what errors each method resolves.

   Question: does the asymmetric substitution pattern reproduce across methods?

   Secondary: do methods specialize — does each one fix a different error category (DIN-SQL → join-plan/wrong-table via schema linking, dense retrieval → wrong-table via retrieval, reflexion → logic/literal via self-correction, CoT → none/negative) — or do they all act on the same errors?

4. **5.4 Model Capacity and Error Composition** — scaling curve + error-resolution order + method×scale interaction

   Question: does the asymmetric substitution pattern reproduce across model scale?

   Secondary: what's the error-resolution order as scale increases (which categories vanish first, which are scale-invariant), and does the best-performing method change with scale (e.g. a small model too weak to execute DIN-SQL's decomposition vs. a large model that benefits fully)?

   needs a more detailed analysis than one paragraph — error analysis for different model sizes, and even different model sizes for different prompting methods (additional experiments, not free reslicing).