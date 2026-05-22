# 2NF spec refinement log

Applied the [nf-specs](../.cursor/skills/nf-specs/SKILL.md) workflow to `preprocess_data/to_2nf/specs.py`.

**Design requirements (current):**

1. Wide tables are **2NF, not 3NF** (transitive deps kept).  
2. **No row loss** — FULL OUTER preserves orphan rows.  
3. **Minimize NULLs** — Step 3 join order (shared keys → match ratio).

**Dates:** 2026-05-20 (join-order pass); requirements-driven cluster reduction (same day).

---

## Requirements-driven cluster reduction

| Database | Removed clusters | Merged / changed |
|----------|------------------|------------------|
| formula_1 | `two_nf_driver_standings` | `driverStandings` only on `two_nf_results`; **keep** `two_nf_qualifying` |
| debit_card | `two_nf_customers`, `two_nf_products`, `two_nf_gasstations` | Orphans via FOJ on `two_nf_transactions`; **keep** `two_nf_yearmonth` (not in trans chain) |
| california_schools | `two_nf_frpm`, `two_nf_satscores` | Single `two_nf_schools`: FOJ `satscores` + `frpm` |
| financial | `two_nf_card` | `card` joined into `two_nf_disp` |
| superhero | `two_nf_colour` (no table in source) | Separate `hero_attribute` / `hero_power` clusters |
| european_football_2 | `two_nf_league` | `League` on `two_nf_match`; **remove** `Team_Attributes`, `Player_Attributes` from match; **keep** `two_nf_team`, `two_nf_player` |

---

## Earlier pass (join order only)

**Method:** FK graph from `dev_20240627/dev_tables.json`; match-ratio tie-breaks from source SQLite where shared-key counts tied.

---

## Summary

| Database | Initial clusters | Final clusters | Cluster changes | Join-order changes |
|----------|-----------------:|---------------:|-----------------|-------------------|
| formula_1 | 7 | 7 | none | 5 clusters reordered |
| debit_card_specializing | 5 | 5 | none | none (already optimal) |
| california_schools | 3 | 3 | none | none |
| financial | 6 | 6 | none | none (account→district deps) |
| superhero | 4 | 4 | none | 2 clusters reordered |
| european_football_2 | 4 | 4 | none | 1 cluster reordered (major) |

**No clusters were merged or removed.** Every N:1 merge candidate was rejected (see per-database notes).

---

## formula_1

### Initial clusters (7)

| Output table | Anchor | Join order |
|--------------|--------|------------|
| `two_nf_results` | results | driverStandings → races → drivers → constructors → status |
| `two_nf_races` | races | circuits → seasons |
| `two_nf_qualifying` | qualifying | races → drivers → constructors |
| `two_nf_driver_standings` | driverStandings | races → drivers |
| `two_nf_lap_times` | lapTimes | races → drivers |
| `two_nf_pit_stops` | pitStops | races → drivers |
| `two_nf_constructors` | constructors | constructorResults → constructorStandings |

### Cluster merge audit (Steps 1–2) — no changes

Candidates found (B anchor N:1 A anchor via FK):

- `qualifying`, `driverStandings`, `lapTimes`, `pitStops`, `results` → **races** (via `raceId`)
- `qualifying`, `results` → **constructors** (via `constructorId`)

**Rejected** for all:

1. **Finer row grain** — each B anchor has its own PK (`qualifyId`, `(raceId,driverId)`, etc.). Absorbing into `races` or `constructors` would change the wide-table grain away from the hub anchor PK.
2. **Intentional orphan coverage** — separate clusters preserve standing-only / qualifying-only / lap-only rows without forcing them through the `results` hub.
3. **`two_nf_results` already joins `driverStandings`** — the bridge role is in-cluster; a separate `two_nf_driver_standings` cluster still serves queries at standing grain.

### Join-order changes (Step 3)

| Cluster | Before | After | Why |
|---------|--------|-------|-----|
| `two_nf_results` | *(unchanged)* | driverStandings → races → drivers → constructors → status | Already correct: `driverStandings` has 2 shared keys with `results`; `races` hub before single-key dimensions for standing-only COALESCE path. |
| `two_nf_races` | circuits → seasons | **seasons → circuits** | Tie-break (1 key each): `seasons` has higher anchor match ratio. |
| `two_nf_qualifying` | races → drivers → constructors | **constructors → drivers → races** | All 1-key; reorder by match ratio (constructors highest). |
| `two_nf_driver_standings` | races → drivers | **drivers → races** | Tie-break: `drivers` higher match ratio. |
| `two_nf_lap_times` | races → drivers | **drivers → races** | Same tie-break as driver standings. |
| `two_nf_pit_stops` | races → drivers | **drivers → races** | Same tie-break. |
| `two_nf_constructors` | *(unchanged)* | constructorResults → constructorStandings | `constructorStandings` ON clause uses `a1.raceId` — must follow `constructorResults`. |

---

## debit_card_specializing

### Initial clusters (5)

| Output table | Anchor | Join order |
|--------------|--------|------------|
| `two_nf_yearmonth` | yearmonth | customers |
| `two_nf_transactions` | transactions_1k | customers → products → gasstations |
| `two_nf_gasstations` | gasstations | *(none)* |
| `two_nf_products` | products | *(none)* |
| `two_nf_customers` | customers | *(none)* |

### Cluster merge audit — no changes

- **`yearmonth` → `customers`**: N:1 via `CustomerID`, but `yearmonth` grain is `(CustomerID, Date)` — finer than `customers`. Merging would expand the customers cluster to month grain.
- **`products` / `gasstations` → `transactions`**: parent dimensions (transactions FK → them), wrong merge direction.
- Standalone dimension clusters kept for orphan gas station / product / customer rows.

### Join-order changes — none

All joins in `two_nf_transactions` are single-key from anchor `a0`. **customers → products → gasstations** kept: customers is the business hub (matches `to_1nf` design) even though lookup tables have higher naive match counts.

---

## california_schools

### Initial clusters (3)

| Output table | Anchor | Join order |
|--------------|--------|------------|
| `two_nf_frpm` | frpm | schools |
| `two_nf_schools` | schools | satscores |
| `two_nf_satscores` | satscores | *(none)* |

### Cluster merge audit — no changes

- **`frpm` → `schools`**: N:1 via `CDSCode`, but `frpm` is finer grain (school × year). Rejected.
- **`satscores` → `schools`**: N:1 via `cds`/`CDSCode`, but separate cluster preserves SAT rows without matching `schools` rows (different column names; orphan SAT coverage).

### Join-order changes — none

Each cluster has at most one join step.

---

## financial

### Initial clusters (6)

| Output table | Anchor | Join order |
|--------------|--------|------------|
| `two_nf_trans` | trans | account → district |
| `two_nf_loan` | loan | account → district |
| `two_nf_order` | order | account → district |
| `two_nf_disp` | disp | client → district |
| `two_nf_card` | card | disp → client |
| `two_nf_account` | account | district |

### Cluster merge audit — no changes

N:1 candidates: `trans`/`loan`/`order`/`disp`/`card` → `account` (via `account_id` or `disp_id` chain).

**Rejected:**

- Fact anchors (`trans`, `loan`, `order`, `disp`, `card`) have finer PKs than `account`.
- Merging would mix fact grains or multiply account rows.
- Separate clusters preserve fact-only orphan rows (e.g. disp without account).

### Join-order changes — none

`district` join uses `a1.district_id` (via `account` or `disp`) — hard dependency forces **account → district** and **disp → client → district** ordering.

---

## superhero

### Initial clusters (4)

| Output table | Anchor | Join order |
|--------------|--------|------------|
| `two_nf_superhero` | superhero | gender → alignment → publisher → race |
| `two_nf_hero_attribute` | hero_attribute | superhero → attribute |
| `two_nf_hero_power` | hero_power | superhero → superpower |
| `two_nf_colour` | colour | *(none)* |

### Cluster merge audit — no changes

- **`hero_attribute` / `hero_power` → `superhero`**: N:1 via `hero_id`, but junction anchors have composite PK `(hero_id, attribute_id)` / `(hero_id, power_id)` — finer grain.
- **`superhero` → `colour`**: wrong direction (`superhero` FK → `colour`).

### Join-order changes (Step 3)

| Cluster | Before | After | Why |
|---------|--------|-------|-----|
| `two_nf_superhero` | *(unchanged)* | gender → alignment → publisher → race | Already ordered by descending match ratio. |
| `two_nf_hero_attribute` | superhero → attribute | **attribute → superhero** | Tie-break (1 key each): join lookup `attribute` first (higher match ratio); both keys come from anchor `a0` so no cross-table NULL propagation, but consistent with Step 3. |
| `two_nf_hero_power` | superhero → superpower | **superpower → superhero** | Same rationale as hero_attribute. |

---

## european_football_2

### Initial clusters (4)

| Output table | Anchor | Join order |
|--------------|--------|------------|
| `two_nf_match` | Match | Country → League → Team → Team_Attributes → Player → Player_Attributes |
| `two_nf_league` | League | Country |
| `two_nf_team` | Team | Team_Attributes |
| `two_nf_player` | Player | Player_Attributes |

### Cluster merge audit — no changes

- **`Match` → `Team` / `Player`**: Match FK → Team/Player, not the reverse. Absorbing Match into Team would be wrong direction and change grain to match-level.

### Join-order changes (Step 3) — major

| Cluster | Before | After | Why |
|---------|--------|-------|-----|
| `two_nf_match` | Country → League → Team → Team_Attributes → Player → Player_Attributes | **Team_Attributes → Country → League → Team → Player → Player_Attributes** | **Rule 1:** `Team_Attributes` shares **2 keys** with `Match` (`home_team_api_id`, `date`) vs 1 for `Team`/`Country`/`League`. Joining `Team` before `Team_Attributes` caused NULL propagation: Match rows with team/date attrs but no `Team` row matched via anchor-only key missed `Team_Attributes` columns. Early 2-key join lets COALESCE pick up `team_api_id`/`date` from `a1` when joining `Team` later. `Player` still before `Player_Attributes` (`a5` dependency). |
| Others | *(unchanged)* | — | Single join step each. |

---

## Verification

From `schema_effect/`:

```bash
python3 -m preprocess_data.to_2nf.build_sqlite --list-dbs
for db in $(python3 -c "from preprocess_data.to_2nf.specs import SPECS; print(' '.join(sorted(SPECS)))"); do
  python3 -m preprocess_data.to_2nf.build_sqlite --db "$db" --dry-run
done
```

All plans should generate without error.

---

## Five additional databases

| db_id | Clusters |
|-------|----------|
| student_club | `two_nf_member`, `two_nf_event`, `two_nf_attendance`, `two_nf_expense` |
| thrombosis_prediction | `two_nf_patient`, `two_nf_examination`, `two_nf_laboratory` |
| toxicology | `two_nf_molecule`, `two_nf_atom`, `two_nf_bond`, `two_nf_connected` |

`MATERIALISED_DB_IDS` in `src/schema_builder.py` lists the nine databases with 1NF/2NF specs (excludes `card_games`, `codebase_community`).
