# 1NF join-order methods

**Scope:** nine databases in `preprocess_data/to_1nf/specs.py`  
**Build:** `python3 -m preprocess_data.to_1nf.build_sqlite`  
**SQL:** chained **FULL OUTER JOIN** on FK keys; **COALESCE on left join keys** (same as 2NF, enabled in `to_1nf/convert.py` since 2026-05-20).

---

## Design requirements (1NF)

1. **1NF wide table** — one scalar column per source attribute; redundancy allowed.
2. **No row loss** — every source row appears in the materialised `one_nf_0` table (FOJ orphans kept).
3. **Minimize NULLs** — order `join_steps` so keys stay populated and sparse dimensions join late.

---

## Method A — Greedy overlap (legacy / automated baseline)

**Also called:** “old method” before the manual checklist pass (still useful as a baseline).

### Procedure

1. **FK graph** — tables = nodes; declared FKs = directed edges (`child.col → parent.col`).
2. **Anchor** — pick table with highest `degree + log10(row_count)` (connectivity + size).  
   *Does not* use benchmark-query participation unless you add it manually.
3. **Greedy join order** — repeatedly add the remaining table `T` that maximizes:
   - `(not sparse, num_fk_links_to_chain, max_match_ratio)`
   - **Match ratio:** fraction of `T` rows whose FK values exist in the current chain.
   - **Sparse deferral:** if `rows(T) > 10× anchor` and overlap to chain `< 1%`, score `T` last among non-sparse candidates.
4. **COALESCE** — left side of each `ON` uses `COALESCE(a0.key, a1.key, …)` for identical column names in the chain (`coalesce_join_keys=True`).
5. **Alias rewrite** — after reordering, renumber `a0`…`aN` and rewrite every `JoinOn` tuple.

### Strengths

- Repeatable from SQLite + `dev_tables.json` alone.
- Good tie-break when two tables have the same parent key.

### Weaknesses

- **Wrong anchors** on several BIRD DBs (e.g. `yearmonth` vs `customers`, `qualifying` vs `results`).
- **Ignores join path** — cannot express “join `budget` via `expense.link_to_budget` on `a2`”.
- **Sparse blind spot** — child→parent match rate can be 100% while the **dimension table** has huge orphan cardinality (e.g. `zip_code`: 41,844 rows never referenced by `member`).
- **Same-grain** sibling facts not grouped (e.g. `lapTimes` / `pitStops` vs `driverStandings` order in `formula_1`).

### Legacy join orders (Method A sequences before checklist pass)

| Database | Anchor | Join order |
|----------|--------|------------|
| `california_schools` | schools | frpm → satscores |
| `debit_card_specializing` | customers | yearmonth → transactions_1k → products → gasstations |
| `financial` | trans | account → disp → client → district → loan → order → card |
| `formula_1` | results | races → drivers → constructors → status → circuits → seasons → qualifying → driverStandings → constructorResults → constructorStandings → lapTimes → pitStops |
| `student_club` | member | **zip_code** → major → income → expense → budget → event → attendance |
| `thrombosis_prediction` | Patient | **Examination** → Laboratory |
| `superhero` | superhero | gender → alignment → publisher → race → hero_attribute → attribute → hero_power → superpower |
| `european_football_2` | Match | Country → League → Team → Team_Attributes → Player → Player_Attributes |
| `toxicology` | connected | bond → atom → molecule |

---

## Method B — Checklist hybrid (current specs)

**Also called:** “new method” / **recommended default** in `specs.py`.

### Procedure

Use Method A metrics as **signals**, then apply manual rules:

| Step | Rule |
|------|------|
| B1 | **Anchor by role** — fact / bridge / hub used in BIRD questions (`customers`, `trans`, `results`, `member`, `Match`, …), not raw row count. |
| B2 | **Encode join paths** — each `JoinOn` must reference aliases that already exist (`expense` on `a2`, `attendance` on `a0`+`a5`, …). |
| B3 | **High overlap first** — among tables that share keys with the chain, prefer higher match ratio and more shared key columns. |
| B4 | **Same-grain siblings** — race-level facts (`lapTimes`, `pitStops`) before other multi-key facts when they share `(raceId, driverId)` with the anchor. |
| B5 | **Defer sparse dimensions** — large tables with few hub references join **last** (check **orphan row count**, not only FK match rate from hub). |
| B6 | **COALESCE** — enabled on all 1NF builds (propagates keys on orphan rows once a bridge table is in the chain). |
| B7 | **Composite / unlike names** — list every key in `JoinOn`; `CDSCode` / `cds` are **not** merged by COALESCE. |

### Strengths

- Correct anchors and multi-hop paths for all nine DBs.
- Fixes known Method A failures (`zip_code` last, `loan`/`order` early on `trans`, `Laboratory` before `Examination`).

### Weaknesses

- Manual maintenance in `specs.py`.
- Overlap-sum score alone cannot rank two valid orders (many ties).

---

## Method C — Full graph method (optional extension)

Eight-step pipeline from design discussion (not fully automated):

1. FK graph  
2. Anchor (connectivity + overlap + **benchmark participation**)  
3. Join highest overlap first  
4. COALESCE propagated keys  
5. Same-grain tables before mixed-grain  
6. Delay sparse/optional tables  
7. Surrogate universal row IDs *(not implemented)*  
8. Controlled duplication *(not implemented)*  

Use **Method B** for anchors/paths; use **Method C** steps 3–6 as audit checks.

---

## Per-database analysis (2026-05-20)

**Metrics:** sum of per-step match ratios along the chain (higher = better key connectivity at join time).  
**Verdict codes:** **B** = current checklist wins; **A** = greedy legacy wins on metrics only; **B+** = hybrid tweak applied.

| Database | Overlap-sum (current / old) | First-step overlap (cur / old) | Sparse / path notes | **Recommended** |
|----------|----------------------------:|--------------------------------|---------------------|-----------------|
| `california_schools` | 1.907 / 1.907 (tie) | frpm 1.0 first vs satscores 0.91 first | frpm 100% school keys; satscores ~91% | **B+** — frpm before satscores (applied in specs) |
| `debit_card_specializing` | 1.0 / 1.0 (tie) | transactions first (hub path) vs yearmonth first | Product/gas join via `a1`; txn hub matters more than row-count greed | **B** — transactions → yearmonth → products → gasstations |
| `financial` | 7.0 / 7.0 (tie) | account first (both) | Old joins loan/order **after** disp chain → worse NULL propagation on trans-only rows; same score hides path effect | **B** — account → loan → order → disp → client → district → card |
| `formula_1` | 11.98 / 11.98 (tie) | races first (both) | Current joins lapTimes/pitStops before constructor* facts (same grain as results); old interleaves standings | **B** — lapTimes/pitStops before constructorResults/Standings |
| `student_club` | 6.89 / 6.89 (tie) | income 0.92 vs **zip_code first** | zip_code: 41,877 rows, **41,844** never used by member; member.zip 100% valid — must join zip **last** | **B** — income → expense → major → budget → event → attendance → zip_code |
| `thrombosis_prediction` | 1.09 / 1.09 (tie) | Lab **1.0** first vs Exam **0.09** first | Examination sparse (~8.7% patient overlap) | **B** — Laboratory → Examination |
| `superhero` | 7.98 / 7.98 (tie) | — | Dimensions before junction tables (`hero_attribute` before `attribute`) | **B** (unchanged; Method A = Method B) |
| `european_football_2` | 3.95 / 3.95 (tie) | — | Country/League on match; Player_Attributes after Player | **B** (unchanged) |
| `toxicology` | 2.74 / 2.74 (tie) | — | bond/atom on connected before molecule via bond | **B** (unchanged) |

### Summary verdict

| Outcome | Count | Databases |
|---------|------:|-----------|
| **Method B (current) strictly better** | 4 | debit_card, financial, student_club, thrombosis |
| **Method B+ (hybrid tweak)** | 1 | california_schools (frpm first) |
| **Tie (same metrics; B kept for path/grain)** | 4 | formula_1, superhero, european_football_2, toxicology |

**Overall:** use **Method B (checklist hybrid)** in `specs.py`. Use **Method A** only to sanity-check overlap; never trust greedy anchor or first-step order alone. **COALESCE** should stay on for both methods (now default for 1NF builds).

---

## Checklist before editing `specs.py`

```
- [ ] Anchor is the query hub (fact/bridge), not the largest table
- [ ] Each JoinOn only uses aliases already in the chain
- [ ] Direct FK children with high overlap join before sparse dimensions
- [ ] Orphan-heavy dimensions (dim rows >> hub references) are last
- [ ] Same-grain sibling facts grouped before unrelated multi-key facts
- [ ] Unlike FK column names both listed in JoinOn
- [ ] `python3 -c "from preprocess_data.to_1nf.convert import build_plan; print(build_plan('<id>', 'dev_20240627').select_sql[:500])"` (preview SQL; 1NF CLI has no `--dry-run`)
```

---

## Code references

| Item | Location |
|------|----------|
| Join plans | `preprocess_data/to_1nf/specs.py` |
| COALESCE / FOJ SQL | `preprocess_data/to_1nf/convert.py` → `_build_select_sql(..., coalesce_join_keys=True)` |
| Column equivalence | `convert.py` → `_FK_COLUMN_EQUIV` |
| 2NF analogue | `docs/to_2nf_spec_refinement.md`, `.cursor/skills/nf-specs/SKILL.md` |

---

## Related work — do the papers support this pipeline?

We **do not** implement any listed paper end-to-end. Production specs use **Method B** (checklist + explicit `JoinOn`). Papers mainly **justify the problem** (universal relation, denormalization, outer-join reordering) and inform **optional** heuristics.

| # | Paper | Supports our goals? | Used in repo? |
|---|--------|-------------------|---------------|
| 1 | Simplified URA & properties | **Conceptual** — single wide view; unique join paths; null/key propagation on orphans | Cite only; multi-path BIRD schemas exceed “simple URA” |
| 2 | Denormalization strategies for DW (Shin & Sanders 2006) | **Yes (taxonomy)** — collapsing relations (CR), redundant attributes; workload/access-path justification | Informal (Method B rules); see § Paper 2 below |
| 3 | One Button Machine | **Low** — auto joins for ML features, inner joins, not FOJ row coverage | No |
| 4 | Deep Feature Synthesis | **Low** — ER graph + multi-hop paths for features, not materialised FOJ | No |
| 5 | Simpli-Squared | **Partial** — FK + table size without cardinality | Benchmark only; see § Paper 5 below |
| 6 | EELs — outerjoin/antijoin reordering (Rao et al. 2001) | **Yes (semantics)** — legal reorderings for outer joins | Topo deps only; see § Paper 6 below |

**What the pipeline does that papers rarely cover:** chained **FULL OUTER** materialisation, **no row loss**, **2NF-not-3NF** wide shape, and **COALESCE** left keys (`convert.py`).

---

## Paper 2 — DW denormalization strategies (Shin & Sanders)

**Paper gives:** four patterns — **collapsing relations (CR)**, partitioning (PR), redundant attributes (RA), plus workload/cardinality/access-path analysis for *when* denormalization pays off in DSS/warehouse queries.

**How we map:**

| Paper idea | Our pipeline |
|------------|--------------|
| CR | 1NF `one_nf_0` and 2NF wide clusters merge many tables into one physical table |
| RA | Wide output repeats attributes from several sources (intentional redundancy) |
| Access-path / transaction analysis | **Method B1** — anchor by BIRD hub (`customers`, `trans`, …), not implemented as automatic SQL mining |
| Join cost / relational algebra | Different objective — we minimise **NULL sparsity** and preserve orphans, not single-query execution cost |

**What we tried:** overlap-first and sparse-last rules in Method A/B mirror “join high-value tables first,” but we did **not** implement the paper’s cost–benefit model or four-strategy picker.

**Promising?** **Yes for framing and documentation** (label specs as CR-style denorm for DSS). **Moderate for automation** — mining `dev.json` SQL for table co-occurrence could improve anchor choice (Method C step 2). **Not sufficient alone** for FOJ order or multi-hop `JoinOn` paths.

---

## Paper 5 — Simpli-Squared (join order without cardinality estimates)

**Paper gives:** join **query** ordering using only **referential integrity + base table sizes** (split at M:N, greedy 1:N, smaller/larger heuristics) — targets **inner-join** execution cost, not NULL rates in a materialised FOJ.

**What we tried:** In `scripts/benchmark_join_orders_student_club.py`, variant **`simpli`** — topological sort of FK children by **ascending row count** (small dimensions before `zip_code`). Same script also ran **`overlap`** (Method A) and **`workload`** (BIRD table mentions).

**Results (2026-05-20 quick runs):**

| Database | Simpli vs current (Method B) |
|----------|------------------------------|
| `student_club` | **Tie** — 42,367 rows, same coverage; `zip_code` orphans dominate final size |
| `thrombosis_prediction` | **Current wins** — Lab→Exam ~**10%** sample NULLs vs Exam→Lab ~**20%** (Simpli/overlap agree with current when overlap is used) |
| `california_schools` | **Tie** — 17,897 rows, ~6.6% sample NULLs both orders |

**Promising?** **Limited for this project.**

- Useful as a **tie-break** when overlap scores tie and deps are tree-like (1:N before huge optional dimensions).
- **Not promising** as a replacement for Method B: ignores **multi-hop** paths (`expense`→`budget`), **sibling facts**, and **FOJ orphan cardinality** (hub→dim match 100% while dim has 41k orphan rows).
- Do **not** expect Simpli-Squared’s inner-join cost optimality to transfer to **FOJ NULL minimisation**.

---

## Paper 6 — EELs (outerjoin & antijoin reordering)

**Paper gives:** **Extended Eligibility Lists** so a bottom-up optimiser only applies outer/anti join reorderings that preserve **semantic equivalence** of the original query.

**How we map:**

| Paper idea | Our pipeline |
|------------|--------------|
| FOJ reordering is constrained | We fix order in `specs.py` instead of searching legal permutations |
| Eligibility = predicates’ required tables | Each `JoinOn` may only reference aliases **already in the chain** (Method B2) |
| More reorder freedom than naive rules | Could enumerate **legal** permutations then score with overlap/sparse metrics |

**What we tried:**

- **Topo sort** on hard deps (`budget`←`expense`, `event`←`budget`, `attendance`←`event`) before greedy/Simpli orders in the benchmark script.
- A naive “all FK neighbors must be in chain” EEL check was **too strict** (e.g. flags `expense` illegal because `budget` is a graph neighbor but not yet in ON) — **not** used in production.

**Promising?** **Yes for a small follow-on, not yet implemented.**

- **High value:** `eel_legal(spec) -> bool` (or list legal swaps) before editing `join_steps` — prevents broken reorderings while exploring Method A/C candidates.
- **Low value alone:** legality does not pick the **best** order; pair with overlap (paper 2 spirit) + sparse-last (Method B5).
- Full IBM-style EEL integration is overkill; a **chain-FOJ specialization** (only edges between new table and current chain) is enough for our specs.

---

## Empirical benchmark (papers 2 / 5 / 6 vs Method B)

Script: `schema_effect/scripts/benchmark_join_orders_student_club.py` (FOJ + COALESCE). Spot checks on `thrombosis_prediction`, `california_schools`.

| Method | Paper link | Outcome |
|--------|------------|---------|
| **Method B (current specs)** | B + overlap rule (2-ish) | **Recommended** — wins on thrombosis NULLs; fixes zip/Exam ordering |
| **Method A (overlap greedy)** | Overlap tie-break | Same as B when topo-fixed; wrong anchor/path without B |
| **Simpli-Squared heuristic** | Paper 5 | No gain on `student_club`; does not beat overlap-first on thrombosis |
| **Workload (BIRD SQL counts)** | Paper 2 access paths | No gain over B in quick tests |
| **Topo / EEL-style deps** | Paper 6 | Necessary filter for auto orders; **not** a ranking criterion |

`financial` full materialisation benchmark was **aborted** (>7 min, no output) — loan/order order comparison still open.

---

## Change log

| Date | Change |
|------|--------|
| 2026-05-20 | Document Methods A/B/C; per-DB analysis; enable COALESCE for 1NF |
| 2026-05-20 | `california_schools`: frpm before satscores (hybrid B+) |
| 2026-05-20 | Related work: papers 1–6; § Paper 2/5/6, empirical benchmark notes |
