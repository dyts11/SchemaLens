# Concrete example: schema transformation across L1–L6 × S1–S3

Generated with `src/schema_builder.py` (`SchemaBuilder("toxicology", ...).build(structural_level, semantic_level)`) — this is the exact string injected into the LLM prompt for each condition, not a hand-made illustration.

**Database:** `toxicology` (4 tables: `atom`, `bond`, `connected`, `molecule`)
**Question:** *"In the non-carcinogenic molecules, how many contain chlorine atoms?"*
**Gold SQL (condition-invariant):**
```sql
SELECT COUNT(DISTINCT T1.molecule_id)
FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id
WHERE T2.element = 'cl' AND T1.label = '-'
```

---

## Table 1 — Structural axis (L1→L6), semantic level fixed at S3 (descriptive)

| Level | What changes | Schema representation given to the model |
|---|---|---|
| **L1** — 1NF wide | All 4 tables pre-joined into one flat table; zero joins needed but heavy redundancy | `TABLE one_nf_0 (connected__atom_id, connected__atom_id2, connected__bond_id, bond__bond_id, bond__molecule_id, bond__bond_type, atom_1__atom_id, atom_1__molecule_id, atom_1__element, atom_2__atom_id, atom_2__molecule_id, atom_2__element, molecule__molecule_id, molecule__label)` |
| **L2** — 2NF clusters | Denormalised "hub" tables anchored on one entity, joined-in neighbors flattened as prefixed columns | `-- Cluster anchor: connected (row key: (atom_id, atom_id2))` then `TABLE two_nf_connected (connected__atom_id, connected__atom_id2, connected__bond_id, bond__bond_id, bond__molecule_id, bond__bond_type, atom_1__…, atom_2__…, molecule__…)` |
| **L3** — 3NF baseline | Fully normalized; table + column names only, no types/keys/FKs | `TABLE atom (atom_id, molecule_id, element)` and `TABLE molecule (molecule_id, label)` *(+ bond, connected)* |
| **L4** — 3NF + metadata | L3 + SQLite type, `PRIMARY KEY`, `NOT NULL`, plus a preamble explaining the notation | `TABLE atom (atom_id TEXT PRIMARY KEY, molecule_id TEXT, element TEXT)` |
| **L5** — 3NF + relations | L4 + inline `FK →` comment per column + a `FOREIGN KEY RELATIONSHIPS` block after all tables | `atom (atom_id TEXT PRIMARY KEY, molecule_id TEXT -- FK → molecule.molecule_id (many-to-one), element TEXT)` … plus `atom.molecule_id → molecule.molecule_id (many-to-one)` |
| **L6** — 3NF + join paths | L5 + a `JOIN PATHS` block with ready-made `INNER JOIN … ON …` lines | adds: `atom JOIN molecule ON atom.molecule_id = molecule.molecule_id` |

**Trend on this benchmark:** EA rises roughly monotonically from L1→L6 (e.g. Qwen2.5-Coder-14B at S3: 20.2%→29.5%, see [main_experiment_qwen2.5-coder-14b-local_heatmap](figures/main_experiment_qwen2.5-coder-14b-local_heatmap.png)) — annotating structure (keys, FKs, join paths) helps the model recover the joins it needs, even though L1/L2 require no joins at all.

---

## Table 2 — Semantic axis (S1→S3), structural level fixed at L3 (3NF baseline)

| Level | Naming scheme | `atom` table | `molecule` table |
|---|---|---|---|
| **S1** — Anonymous | Position-based placeholders per table (`col_a`, `col_b`, …) — no semantic signal at all | `TABLE atom (col_a, col_b, col_c)` | `TABLE molecule (col_a, col_b)` |
| **S2** — Abbreviated | Short developer-style abbreviations | `TABLE atom (atm_id, mol_id, elem)` | `TABLE molecule (mol_id, lbl)` |
| **S3** — Descriptive | Full English column names (curated) | `TABLE atom (atom_id, molecule_id, element)` | `TABLE molecule (molecule_id, label)` |

**Trend on this benchmark:** EA jumps sharply from S1→S2 and then plateaus S2→S3 (e.g. Qwen2.5-Coder-14B at L3: 2.5%→28.5%→28.5%, see [main_experiment_qwen2.5-coder-14b-local_heatmap](figures/main_experiment_qwen2.5-coder-14b-local_heatmap.png)) — the model cannot recover which column is "element" or "label" from `col_a`/`col_b` alone (e.g. it cannot map "chlorine" → `element = 'cl'` or "non-carcinogenic" → `label = '-'`), but a short abbreviation is already enough to disambiguate.

---

### Reproducing / extending this example
```bash
.venv/bin/python -c "
from src.schema_builder import SchemaBuilder
b = SchemaBuilder('toxicology', 'dev_20240627')
print(b.build(structural_level=5, semantic_level=1))
"
```
Swap `db_id`, `structural_level` (1–6), `semantic_level` (1–4) to generate any other condition/database combination shown in the paper.
