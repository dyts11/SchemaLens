# Future Work & Experiment Plan

**Paper:** *Disentangling Structure and Semantics: How Schema Representation Affects LLM-Based SQL Generation*  
**Purpose:** Ordered roadmap for revision experiments that address metric validity, generalization, prompting, confounds, and model coverage.

---

## Overview

| Phase | Focus | Primary model(s) | Est. new generations | Blocks |
|-------|--------|------------------|----------------------|--------|
| **1** | L1/L2 error taxonomy (fan-out, NULL padding) | Qwen-14B | 0 (analysis only) | - |
| **2** | L1/L2 calibrated gold (50 Q) | Qwen-14B | 0 (re-score existing predictions) | Phase 1 sample set |
| **3** | Spider generalization (L3-L6 x S1-S3) | Qwen-14B | 4,800 (12 x 200 Q) | - |
| **4** | Few-shot and CoT (full 18 conditions) | Qwen-14B | 14,292 (18 x 397 x 2 variants) | Optional: Phase 3 |
| **5** | Denormalization-notice ablation | Qwen-14B | 1,588 (L1-S3 + L2-S3 x 2 arms; arm C optional +794) | - |
| **6** | GPT-4o-mini (full 18 conditions) | GPT-4o-mini | 7,146 (18 x 397) | Phase 3 DBs for Spider add-on |

---

**Phase 1-2 shared cohort (50 questions):**  
Fixed seed **42**, stratified across:

- at least 2 databases (e.g. `financial`, `formula_1`, `student_club`)
- Query types: retrieval, `COUNT`, `SUM`/`AVG`, `GROUP BY`
- Both **L1** and **L2** where applicable (same Q IDs)

Document final IDs in `data/calibration_l1l2_50q.json`.

---

## Phase 3 - Spider generalization

### Objective

Test whether **semantic vs structural asymmetry** replicates on **Spider** without L1/L2 materialisation - clean EX on native schemas.

### Motivation

Addresses "single benchmark family" / BIRD-only limitation. Corners and marginals on **3NF-only** cells are statistically valid.

### Design

| Step | Action |
|------|--------|
| 3.1 | Select **1-2 Spider databases** with moderate size (e.g. 5-15 tables, no extreme width). |
| 3.2 | Subsample **~150-250 questions** total (all Q for 1 DB, or split across 2 DBs). |
| 3.3 | Build **S1-S3** mappings (reuse pipeline: anonymous / abbreviated / descriptive from Spider column names). |
| 3.4 | Run **12 conditions**: **L3-L6 x S1-S3** only (no L1/L2). |
| 3.5 | Map structural levels to Spider prompt format (same ladder as BIRD: names, then types/PK, then FK, then join paths). |
| 3.6 | Primary contrasts: marginal S at L3; marginal L at S2; corners **L3-S3 vs L6-S1** (clean substitution on same DB). |

### Models and conditions

| Model | Grid | Questions | Generations |
|-------|------|-------------|-------------|
| Qwen2.5-Coder-14B | L3-L6 x S1-S3 | ~200 | 12 x 200 = **2,400** |
| Gemini 2.5 Flash | L3-L6 x S1-S3 | ~200 | **2,400** |

### Results - execution accuracy (fill in)

*Format: accuracy as fraction or percent (e.g. `0.42` or `42.0%`). One table per model; optional margin in parentheses.*

#### Qwen2.5-Coder-14B - Spider subset (n = TBD)

|       | **S1** | **S2** | **S3** |
|-------|--------|--------|--------|
| **L3** | TBD | TBD | TBD |
| **L4** | TBD | TBD | TBD |
| **L5** | TBD | TBD | TBD |
| **L6** | TBD | TBD | TBD |

**Corner gaps (pp):** L3-S3 minus L6-S1 = TBD | L1-S3 vs L6-S1: N/A on Spider

### Deliverables

- [ ] `data/spider_subset.json` + per-DB semantic mappings  
- [ ] `src/spider_schema_builder.py` (or extend `schema_builder.py`)  
- [ ] `docs/spider_replication_results.md` - heatmap / corner gaps  
- [ ] Paper: subsection "Replication on Spider" + figure  

---

## Phase 4 - Few-shot and chain-of-thought

### Objective

Test whether **in-context learning** or **explicit reasoning** changes the **full 6x3** schema-effect landscape - not only corner cells.

### Motivation

Main paper is zero-shot; reviewers will ask if leaderboard-style few-shot or CoT erases the asymmetry across all structural and semantic levels.

### Design

#### 4A - Few-shot

| Setting | Value |
|---------|--------|
| Conditions | **All 18** (L1-L6 x S1-S3) |
| k | 3 (single setting; document if k=1 added later) |
| Examples | Fixed per `db_id`, dev-safe demos (no overlap with eval Q) |
| Template | Extend `src/prompt_builder.py` - `## Examples` block before question |
| Baseline | Reuse existing zero-shot CSVs where available |

#### 4B - Chain-of-thought

| Setting | Value |
|---------|--------|
| Conditions | **All 18** (L1-L6 x S1-S3) |
| Instruction | "Reason step by step about tables and joins, then output SQL on final line." |
| Parsing | Extract last `SELECT ...` block or line after `SQL:` |

### Models and conditions

| Model | Grid | Prompting | Questions | Generations |
|-------|------|-----------|-------------|-------------|
| Qwen2.5-Coder-14B | L1-L6 x S1-S3 | Few-shot k=3 | 397 | 18 x 397 = **7,146** |
| Qwen2.5-Coder-14B | L1-L6 x S1-S3 | CoT | 397 | 18 x 397 = **7,146** |

### Results - execution accuracy (fill in)

#### Few-shot k=3 - Qwen2.5-Coder-14B (n = 397 per cell)

|       | **S1** | **S2** | **S3** |
|-------|--------|--------|--------|
| **L1** | TBD | TBD | TBD |
| **L2** | TBD | TBD | TBD |
| **L3** | TBD | TBD | TBD |
| **L4** | TBD | TBD | TBD |
| **L5** | TBD | TBD | TBD |
| **L6** | TBD | TBD | TBD |

#### Change vs zero-shot (optional summary)

| Prompting | Mean change over 18 cells (pp) | Max gain (cell) | Max drop (cell) |
|-----------|-------------------------------|-----------------|-----------------|
| Few-shot k=3 | TBD | TBD (L__-S__) | TBD (L__-S__) |
| CoT | TBD | TBD (L__-S__) | TBD (L__-S__) |

### Deliverables

- [ ] `prompts/few_shot_examples/{db_id}.json`  
- [ ] `docs/prompting_ablation_results.md`  
- [ ] Paper: table "Zero-shot vs few-shot vs CoT" (marginals or selected cells)  

---

## Phase 5 - Denormalization notice ablation

### Objective

Isolate how much L1/L2 performance comes from the **long denormalisation notice** vs the **wide schema itself**.

### Motivation

Confound control: notice is ~3 pages of task-specific rules (Appendix A.2) - may dominate L1/L2 more than normalization.

### Design

| Arm | L1/L2 prompt | Questions |
|-----|----------------|-----------|
| **A - Full** (baseline) | Current notice (`prompt_builder.py`) | 397 |
| **B - None** | Schema + question only; no notice | 397 |
| **C - Minimal** (optional) | One sentence: "Tables may contain duplicate rows per logical entity; deduplicate when needed." | 397 |

Semantic level: **S3** only.  
Structural levels: **L1-S3**, **L2-S3**.  
Model: **Qwen2.5-Coder-14B**.

### Models and conditions

| Model | Levels | Arms | Generations |
|-------|--------|------|-------------|
| Qwen2.5-Coder-14B | L1-S3, L2-S3 | A, B | 2 x 397 x 2 = **1,588** |
| Qwen2.5-Coder-14B | L1-S3, L2-S3 | C (optional) | +794 |

*Arm A: reuse existing CSVs if already run with full notice.*

### Results - execution accuracy (fill in)

#### Qwen2.5-Coder-14B - L1-S3 (n = 397)

| Arm | Notice | Accuracy | Change vs A (pp) |
|-----|--------|----------|------------------|
| **A** | Full | TBD | - |
| **B** | None | TBD | TBD |
| **C** | Minimal (optional) | TBD | TBD |

#### Qwen2.5-Coder-14B - L2-S3 (n = 397)

| Arm | Notice | Accuracy | Change vs A (pp) |
|-----|--------|----------|------------------|
| **A** | Full | TBD | - |
| **B** | None | TBD | TBD |
| **C** | Minimal (optional) | TBD | TBD |

### Success criteria

- If **B much lower than A**: headline L1/L2 numbers are **not** pure structure effects - revise claims.  
- If **B similar to A**: notice is not driving the main L2-to-L3 gap story (still report).  

### Deliverables

- [ ] `src/prompt_builder.py` flags: `denorm_notice=full|none|minimal`  
- [ ] `docs/denorm_notice_ablation.md`  
- [ ] Paper: grouped bar L1/L2 x {full, none, minimal}  

### Dependencies

- Best interpreted together with Phase 2 (calibrated EX on same 50 Q).

---

## Phase 6 - GPT-4o-mini

### Objective

Add a **non-Qwen, non-Gemini** API model on the **full 18-condition** BIRD grid (and Spider subset if Phase 3 is complete).

### Design

| Setting | Value |
|---------|--------|
| Benchmark | BIRD (9 DBs, 397 Q) - same as main study |
| Grid | **L1-L6 x S1-S3** (18 conditions) |
| Model | `gpt-4o-mini` (pin API snapshot in run log) |
| Decoding | temperature = 0, 1 sample |

**Generations:** 18 x 397 = **7,146**

*Optional add-on after Phase 3:* same 12-cell Spider grid x ~200 Q = **2,400** additional runs.

### Results - execution accuracy (fill in)

#### GPT-4o-mini - BIRD (n = 397 per cell)

|       | **S1** | **S2** | **S3** |
|-------|--------|--------|--------|
| **L1** | TBD | TBD | TBD |
| **L2** | TBD | TBD | TBD |
| **L3** | TBD | TBD | TBD |
| **L4** | TBD | TBD | TBD |
| **L5** | TBD | TBD | TBD |
| **L6** | TBD | TBD | TBD |

#### Corner summary (pp)

| Contrast | GPT-4o-mini | Qwen-14B (ref.) | Gemini (ref.) |
|----------|-------------|-----------------|----------------|
| L1-S3 minus L6-S1 | TBD | TBD | TBD |
| L3-S3 minus L6-S1 | TBD | TBD | TBD |
| S1 to S2 at L3 | TBD | TBD | TBD |
| L3 to L6 at S2 | TBD | TBD | TBD |

#### GPT-4o-mini - Spider subset (optional; n = TBD per cell)

|       | **S1** | **S2** | **S3** |
|-------|--------|--------|--------|
| **L3** | TBD | TBD | TBD |
| **L4** | TBD | TBD | TBD |
| **L5** | TBD | TBD | TBD |
| **L6** | TBD | TBD | TBD |

### Deliverables

- [ ] `results/gpt-4o-mini__*.csv`  
- [ ] `docs/gpt4o_mini_results.md` - full grid + corner gaps vs Qwen/Gemini  
- [ ] Paper: extend cross-model corner figure / appendix table  

---

*Last updated: 2026-06-03*
