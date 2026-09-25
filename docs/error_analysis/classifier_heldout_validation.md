# Held-out validation of the LLM-assisted error classifier

Scored 284/284 hand-labelled Qwen2.5-Coder-14B L3·S3 failures. 4-fold cross-validation: each fold was classified by a Claude subagent (Claude Code, model claude-fable-5-1, rules = docs/error_analysis/error_taxonomy.md + .claude/skills/error-classify/SKILL.md) that saw the hand labels of the OTHER folds as guidance and never saw the labels of the fold it classified.

## Overall agreement

| metric | value | 95% bootstrap CI |
|--|--:|--:|
| accuracy (exact category match) | 91.2% | [87.7%, 94.4%] |
| Cohen's κ | 0.874 | [0.825, 0.918] |

| fold | n | accuracy |
|--|--:|--:|
| 0 | 74 | 93.2% |
| 1 | 71 | 88.7% |
| 2 | 70 | 91.4% |
| 3 | 69 | 91.3% |

## Per-category precision / recall / F1 (human label = truth)

| category | human n | classifier n | precision | recall | F1 |
|--|--:|--:|--:|--:|--:|
| Invalid SQL | 5 | 5 | 1.00 | 1.00 | 1.00 |
| Schema linking | 67 | 68 | 0.91 | 0.93 | 0.92 |
| JOIN errors | 31 | 31 | 0.87 | 0.87 | 0.87 |
| GROUP BY errors | 8 | 8 | 0.75 | 0.75 | 0.75 |
| Nesting problem | 17 | 16 | 0.88 | 0.82 | 0.85 |
| Predicate error | 135 | 131 | 0.96 | 0.93 | 0.95 |
| Other | 21 | 25 | 0.76 | 0.90 | 0.83 |

## Confusion matrix (rows = human label, columns = classifier label)

| human \ clf | Invalid | SchemaLink | JOIN | FanOut | GROUPBY | Nesting | Predicate | Other | total |
|--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Invalid | **5** | · | · | · | · | · | · | · | 5 |
| SchemaLink | · | **62** | 2 | · | · | · | 1 | 2 | 67 |
| JOIN | · | 1 | **27** | · | · | · | 1 | 2 | 31 |
| GROUPBY | · | · | 1 | · | **6** | · | 1 | · | 8 |
| Nesting | · | 1 | · | · | · | **14** | 1 | 1 | 17 |
| Predicate | · | 3 | 1 | · | 2 | 2 | **126** | 1 | 135 |
| Other | · | 1 | · | · | · | · | 1 | **19** | 21 |
| total | 5 | 68 | 31 | 0 | 8 | 16 | 131 | 25 | 284 |

## Category-rate sensitivity (what Tables 4–5 would look like under classifier vs human labels)

| category | human % | classifier % | Δ (pp) |
|--|--:|--:|--:|
| Invalid SQL | 1.8 | 1.8 | +0.0 |
| Schema linking | 23.6 | 23.9 | +0.4 |
| JOIN errors | 10.9 | 10.9 | +0.0 |
| GROUP BY errors | 2.8 | 2.8 | +0.0 |
| Nesting problem | 6.0 | 5.6 | -0.4 |
| Predicate error | 47.5 | 46.1 | -1.4 |
| Other | 7.4 | 8.8 | +1.4 |

## Disagreements

| qid | db | human | classifier | human reason | classifier reason |
|--|--|--|--|--|--|
| 24 | california_schools | Predicate error (Predicate semantic error) | Schema linking (wrong column) | missing rtype='S' filter | precomputed percent_eligible_free_k12 substituted for gold's Free Meal Count (K-12)/Enrollment (K-12) ratio; also drops  |
| 25 | california_schools | Nesting problem (HAVING clause mismatch) | Schema linking (Wrong column) | gold's per-group HAVING AVG(AvgScrMath)>400 (with GROUP BY sname,FundingType) collapsed to a flat per-row WHERE filter w | Filters County='Riverside' instead of gold's District LIKE 'Riverside%' and selects schools.School instead of satscores. |
| 62 | california_schools | Other (wrong aggregate function or scaling) | Schema linking (Wrong column) | uses precomputed percent_eligible_free_k12 without gold's *100 scaling on the Free Meal Count/Enrollment ratio | Uses precomputed percent_eligible_free_k12 < 0.18 instead of gold's Free Meal Count*100/Enrollment < 0.18 ratio (differe |
| 85 | california_schools | Schema linking (wrong column) | Other (wrong aggregate function or scaling) | precomputed percent_eligible_free_k12 substituted for gold's manually-scaled Free Meal Count K12*100/Enrollment K12 rati | Uses precomputed percent_eligible_free_k12 (a fraction) where gold computes Free Meal Count (K-12) * 100 / Enrollment (K |
| 89 | financial | JOIN errors (extra table) | Schema linking (wrong column) | joins in `trans` (not needed) and filters on trans.type='issuance' instead of gold's account.frequency='POPLATEK PO OBRA | replaces account.frequency='POPLATEK PO OBRATU' with trans.type='issuance' via an extra trans join; also 'East Bohemia'  |
| 95 | financial | Nesting problem (wrong sub-query) | Other (missing/redundant DESC) | omits gold's subquery pinning to the single (youngest) client via ORDER BY birth_date DESC LIMIT 1; instead sorts the fu | ORDER BY birth_date ASC picks the oldest client instead of gold's youngest (birth_date DESC); also collapses gold's scal |
| 125 | financial | Predicate error (Predicate semantic error) | JOIN errors (extra table) | computes a plain difference (rate_1996 - rate_1995) instead of gold's percentage-change formula; also wrong status value | routes to district via disp+client (client.district_id) instead of gold's account.district_id, changing/multiplying rows |
| 129 | financial | GROUP BY errors (wrong column) | JOIN errors (Wrong table) | introduces GROUP BY district_name + SUM(amount) ranking (highest total amount) instead of gold's simple ORDER BY per-tra | Adds unneeded client/disp joins (multiplying account rows per disponent) instead of gold's district-account-trans chain; |
| 149 | financial | Schema linking (wrong table) | JOIN errors (missing table) | replaces disp.type entirely with an unrelated 'account NOT IN loan' condition and selects statement_frequency/average_sa | Omits the disp join entirely (gold selects DISTINCT disp.type <> 'OWNER'); instead selects account.statement_frequency a |
| 243 | toxicology | Schema linking (wrong column) | JOIN errors (Wrong column) | joins connected via c.molecule_id (connected has no molecule_id column) when molecule_id lives on the already-joined bon | Joins bond to connected ON molecule_id, a column connected doesn't have (the real key is bond_id); also element='phospho |
| 247 | toxicology | Predicate error (Predicate semantic error) | Other (missing/redundant DISTINCT) | adds an extra 'atom_id NOT IN (SELECT atom_id2 FROM connected)' condition gold doesn't have | missing DISTINCT (49 rows vs gold's 5 distinct elements); the added NOT IN atom_id2 clause is vestigial since connected  |
| 736 | superhero | Predicate error (Filter value error) | Nesting problem (wrong sub-query) | attribute_name='intelligence' (lowercase) doesn't match the stored value 'Intelligence', causing the subquery to return  | Gold's tie-preserving attribute_value = (SELECT MIN(...)) equality subquery collapsed to a scalar id = (... ORDER BY att |
| 753 | superhero | JOIN errors (missing table) | Predicate error (Predicate semantic error) | substitutes eye_colour_id IS NULL for gold's JOIN colour + colour='No Colour' - 'No Colour' is a specific categorical va | Substitutes eye_colour_id IS NULL for gold's join to colour with colour = 'No Colour' (a real colour row, not NULL); the |
| 865 | formula_1 | Schema linking (wrong column) | Predicate error (Predicate semantic error) | filters results.position IS NOT NULL instead of gold's results.time IS NOT NULL - a different real column with different | filters position IS NOT NULL instead of gold's time IS NOT NULL (different finish condition); also drops dob IS NOT NULL |
| 884 | formula_1 | Predicate error (Predicate semantic error) | Nesting problem (wrong sub-query) | drops the month-matching condition entirely, collapsing to just the earliest race in the minimum year instead of gold's  | replaces gold's two scalar subqueries (year and month of the earliest race, returning all races that month) with year=MI |
| 981 | formula_1 | Other (wrong aggregate function or scaling) | Predicate error (Predicate semantic error) | subquery selects MIN(date_of_birth) (oldest driver) instead of gold's youngest-driver selection; also lacks the outer OR | subquery selects date_of_birth = MIN(...) (oldest driver) instead of gold's ORDER BY dob DESC LIMIT 1 (youngest); also M |
| 989 | formula_1 | Predicate error (Predicate semantic error) | Schema linking (wrong column) | filters on results.position=1 instead of gold's time LIKE '_:%:__.___' pattern match - different column, different condi | Selects r.time where r is the races alias (race start time) instead of results.time; also uses position = 1 instead of g |
| 994 | formula_1 | JOIN errors (extra table) | Other (SELECT-list shape) | adds an unnecessary constructorStandings join, which could silently drop constructor-race rows lacking a matching standi | column order differs (name, nationality, SUM vs gold's SUM, name, nationality); the extra constructorStandings join is v |
| 1149 | thrombosis_prediction | Predicate error (Filter value error) | GROUP BY errors (wrong column) | uses 'Inpatient'/'Outpatient'/'Male' instead of the actual stored codes '+'/'-'/'M', causing zero matches; also introduc | introduces GROUP BY admission_type (per-group rows) where gold computes one CASE/percentage row; also sex='Male' and 'In |
| 1162 | thrombosis_prediction | Predicate error (Filter value error) | Schema linking (wrong column) | uses sex='female' and admission_type='门诊' (Chinese text) instead of the stored codes 'F' and '-' | filters year of first_hospital_visit_date ('First Date') instead of gold's Description (first_record_date); also sex='fe |
| 1267 | thrombosis_prediction | Nesting problem (wrong sub-query) | Predicate error (Predicate semantic error) | drops gold's WITH CTE structure (HAVING MAX(COALESCE(Thrombosis,0))=0 across ALL of a patient's exam records) in favor o | Replaces gold's per-patient HAVING MAX(COALESCE(Thrombosis,0))=0 CTE logic with a flat row-level thrombosis_degree IS NU |
| 1479 | debit_card_specializing | GROUP BY errors (wrong column) | Predicate error (Predicate semantic error) | groups by strftime('%Y', date) (NULL for all rows since Date is 'YYYYMM' text) instead of gold's SUBSTR(Date,1,4), colla | strftime('%Y', date) misapplied to 'YYYYMM' text returns NULL for every row, unlike gold's SUBSTR(Date,1,4) |
| 1480 | debit_card_specializing | Predicate error (Predicate semantic error) | GROUP BY errors (wrong column) | strftime('%Y', date) misapplied to 'YYYYMM' text returns NULL, so the WHERE filter matches zero rows; the also-wrong mon | Groups by the full yearmonth date instead of gold's month SUBSTR(Date, 5, 2); also strftime('%Y') on 'YYYYMM' text yield |
| 1490 | debit_card_specializing | JOIN errors (Join type error) | Other (missing/redundant DISTINCT) | uses INNER JOIN where gold's LEFT JOIN preserves customers with no yearmonth rows; also drops the COUNT(DISTINCT...) per | computes a row-level percentage over yearmonth rows instead of gold's COUNT(DISTINCT CustomerID) customer-level percenta |
| 1531 | debit_card_specializing | Schema linking (wrong column) | Other (wrong aggregate function or scaling) | ranks/selects the top customer by SUM(amount) alone instead of gold's SUM(amount*price); computes avg_price_per_item as  | AVG(price) instead of gold's weighted SUM(price*amount)/SUM(amount); also ranks customers by SUM(amount) instead of SUM( |