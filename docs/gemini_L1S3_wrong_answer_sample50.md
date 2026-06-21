# Gemini 2.5 Flash · L1·S3 wrong-answer sample (n=50)

**Source:** `results/gemini-2.5-flash__L1S3.csv` · **Population:** 263 failures / 397 questions · **Sample:** seed=42, n=50

**Setup:** Gold SQL on 3NF SQLite; predicted SQL on `{db_id}__1nf.sqlite` (`one_nf_0`). Multiset execution comparison (`evaluator.py`).

## Category definitions

| Code | Label | Meaning |
|------|--------|--------|
| **(a)** | Genuine model error | Wrong metric, filter, column, `HAVING`, missing `/12`, `MAX` vs `SUM`, etc. |
| **(b)** | Partial (missing DISTINCT) | 1NF translation largely faithful; automated DISTINCT repair **or** clear `COUNT`/scan fan-out without DISTINCT would align with gold |
| **(c)** | Unrecoverable evaluation artefact | SQL executes but multiset ≠ gold; execution errors; or fan-out needs dedup **subquery** (SUM/AVG), not keyword DISTINCT alone |

## Summary (sample)

| Category | Count | % of sample |
|----------|------:|------------:|
| **(a)** Genuine model error | 31 | 62.0% |
| **(b)** Partial (DISTINCT missing) | 2 | 4.0% |
| **(c)** Unrecoverable eval artefact | 17 | 34.0% |
| **Total** | 50 | 100.0% |

### Full failure population (n=263, same classifier)

| Category | Count | % |
|----------|------:|--:|
| **(a)** Genuine model error | 165 | 62.7% |
| **(b)** Partial (DISTINCT missing) | 12 | 4.6% |
| **(c)** Unrecoverable eval artefact | 86 | 32.7% |
| **Total** | 263 | 100.0% |

*Sample seed=42. Classification: execute DISTINCT repairs where applicable, then SQL-shape rules (`analysis/classify_l1s3_gemini_sample.py`). (b) = faithful wide-table SQL missing deduplication; (c) = SUM/AVG fan-out, execution errors, or DISTINCT present but still mismatched.*

---

## Sampled failures

### 1. Q1162 (thrombosis_prediction, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID) FROM one_nf_0 WHERE Patient__sex = 'F' AND STRFTIME('%Y', Patient__first_hospital_visit_date) = '1997' AND Patient__admission_type = 'Outpatient'
```

### 2. Q1507 (debit_card_specializing, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.Time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T2.ChainID = 11
```

**Predicted SQL:**

```sql
SELECT DISTINCT transactions_1k__time FROM one_nf_0 WHERE gasstations__chain_id = 11
```

### 3. Q897 (formula_1, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'MAX']; predicted uses ['MAX']

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
WITH DriverWins AS (
  SELECT
    drivers__driver_id,
    drivers__first_name,
    drivers__last_name,
    drivers__nationality,
    MAX(driverStandings__wins) AS total_career_wins
  FROM one_nf_0
  GROUP BY
    drivers__driver_id,
    drivers__first_name,
    drivers__last_name,
    drivers__nationality
  ORDER BY
    total_career_wins DESC
  LIMIT 1
)
SELECT
  dw.drivers__first_name || ' ' || dw.drivers__last_name AS driver_name,
  dw.drivers__nationality,
  MAX(T2.results__points) AS max_single_race_points
FROM DriverWins AS dw
JOIN one_nf_0 AS T2
  ON dw.drivers__driver_id = T2.drivers__driver_id
GROUP BY
  dw.drivers__first_name,
  dw.drivers__last_name,
  dw.drivers__nationality;
```

### 4. Q1146 (european_football_2, moderate, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT team_away__team_long_name
FROM (
  SELECT DISTINCT
    Match__match_api_id,
    team_away__team_long_name,
    Match__away_team_goals
  FROM one_nf_0
)
GROUP BY team_away__team_long_name
ORDER BY SUM(Match__away_team_goals) DESC
LIMIT 1
```

### 5. Q1110 (european_football_2, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_passing_class
FROM one_nf_0
WHERE Team_Attributes__date = '2010-02-22'
  AND Team_Attributes__team_api_id IN (
    SELECT DISTINCT team_home__team_api_id
    FROM one_nf_0
    WHERE team_home__team_long_name = 'FC Lorient'
    UNION
    SELECT DISTINCT team_away__team_api_id
    FROM one_nf_0
    WHERE team_away__team_long_name = 'FC Lorient'
  );
```

### 6. Q1220 (thrombosis_prediction, simple, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__birthday FROM one_nf_0 WHERE Laboratory__urea_nitrogen = (SELECT MAX(Laboratory__urea_nitrogen) FROM one_nf_0 WHERE Laboratory__urea_nitrogen IS NOT NULL)
```

### 7. Q1150 (thrombosis_prediction, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN strftime('%Y', Patient__birthday) > '1930' THEN Patient__ID ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) FROM one_nf_0 WHERE Patient__sex = 'Female'
```

### 8. Q1411 (student_club, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT expense__expense_description FROM one_nf_0 WHERE member__first_name = 'Sacha' AND member__last_name = 'Harrison'
```

### 9. Q964 (formula_1, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__driver_code FROM one_nf_0 WHERE drivers__nationality = 'American'
```

### 10. Q1094 (european_football_2, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT
  (
    (SELECT MAX(Player_Attributes__overall_rating) FROM one_nf_0 WHERE Player__player_name = 'Ariel Borysiuk') -
    (SELECT MAX(Player_Attributes__overall_rating) FROM one_nf_0 WHERE Player__player_name = 'Paulin Puel')
  ) * 100.0 / (SELECT MAX(Player_Attributes__overall_rating) FROM one_nf_0 WHERE Player__player_name = 'Paulin Puel')
```

### 11. Q1484 (debit_card_specializing, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT
  (
    SELECT
      COUNT(DISTINCT gasstations__gas_station_id)
    FROM one_nf_0
    WHERE
      gasstations__segment = 'discount' AND gasstations__country = 'Czech Republic'
  ) - (
    SELECT
      COUNT(DISTINCT gasstations__gas_station_id)
    FROM one_nf_0
    WHERE
      gasstations__segment = 'discount' AND gasstations__country = 'Slovakia'
  );
```

### 12. Q1483 (debit_card_specializing, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(yearmonth__consumption) FROM (SELECT DISTINCT customers__customer_id, yearmonth__date, yearmonth__consumption FROM one_nf_0 WHERE customers__customer_id = 6 AND yearmonth__date BETWEEN '2013-08-01' AND '2013-11-30')
```

### 13. Q1317 (student_club, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT member__member_id) FROM one_nf_0 WHERE event__event_name = 'Women''s Soccer' AND member__t_shirt_size = 'M'
```

### 14. Q1156 (thrombosis_prediction, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT
  Patient__ID,
  (STRFTIME('%Y', Examination__examination_date) - STRFTIME('%Y', Patient__birthday)) AS age
FROM one_nf_0
WHERE
  Examination__thrombosis_degree > 0;
```

### 15. Q1168 (thrombosis_prediction, challenging, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT
  (
    SELECT MAX(Laboratory__Date)
    FROM one_nf_0
    WHERE Patient__ID = (
      SELECT Patient__ID
      FROM one_nf_0
      WHERE Patient__diagnosis LIKE '%SJS%' OR Examination__diagnosis LIKE '%SJS%'
      ORDER BY Patient__birthday ASC
      LIMIT 1
    )
  ),
  (
    SELECT ROUND((JULIANDAY(Patient__first_hospital_visit_date) - JULIANDAY(Patient__birthday)) / 365.25)
    FROM one_nf_0
    WHERE Patient__ID = (
      SELECT Patient__ID
      FROM one_nf_0
      WHERE Patient__diagnosis LIKE '%SJS%' OR Examination__diagnosis LIKE '%SJS%'
      ORDER BY Patient__birthday ASC
      LIMIT 1
    )
    LIMIT 1
  );
```

### 16. Q847 (formula_1, simple, retrieval) — **(b)**

**Outcome:** `wrong_answer` · **Category (b):** Retrieval SELECT without DISTINCT on denormalised `one_nf_0` (duplicate rows)

**Gold SQL:**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL:**

```sql
SELECT drivers__last_name
FROM one_nf_0
WHERE races__round = 19
ORDER BY qualifying__qualifying_2_time ASC
LIMIT 1
```

### 17. Q981 (formula_1, moderate, retrieval) — **(b)**

**Outcome:** `wrong_answer` · **Category (b):** Retrieval SELECT without DISTINCT on denormalised `one_nf_0` (duplicate rows)

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT
  T1.races__year,
  T1.races__name,
  T1.races__date,
  T1.races__time
FROM one_nf_0 AS T1
WHERE
  T1.drivers__driver_id = (
    SELECT
      drivers__driver_id
    FROM one_nf_0
    ORDER BY
      drivers__date_of_birth ASC
    LIMIT 1
  )
  AND T1.qualifying__race_id IS NOT NULL
ORDER BY
  T1.races__date ASC,
  T1.races__time ASC
LIMIT 1
```

### 18. Q1482 (debit_card_specializing, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Prediction does not use one_nf_0 wide table as expected for L1

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
WITH DeduplicatedConsumption AS (
    SELECT DISTINCT
        T.yearmonth__customer_id,
        T.yearmonth__date,
        T.yearmonth__consumption,
        T.customers__segment
    FROM one_nf_0 AS T
    WHERE T.customers__currency = 'EUR'
      AND T.customers__segment IN ('SME', 'LAM', 'KAM')
      AND STRFTIME('%Y', T.yearmonth__date) IN ('2012', '2013')
),
YearlySegmentConsumption AS (
    SELECT
        DC.customers__segment,
        STRFTIME('%Y', DC.yearmonth__date) AS consumption_year,
        SUM(DC.yearmonth__consumption) AS total_consumption
    FROM DeduplicatedConsumption AS DC
    GROUP BY
        DC.customers__segment,
        consumption_year
)
SELECT
    YSC_2012.customers__segment,
    ((YSC_2013.total_consumption - YSC_2012.total_consumption) * 100.0 / YSC_2012.total_consumption) AS percentage_change
FROM YearlySegmentConsumption AS YSC_2012
JOIN YearlySegmentConsumption AS YSC_2013
    ON YSC_2012.customers__segment = YSC_2013.customers__segment
WHERE YSC_2012.consumption_year = '2012'
  AND YSC_2013.consumption_year = '2013'
ORDER BY YSC_2012.customers__segment;
```

### 19. Q937 (formula_1, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT DISTINCT results__time FROM one_nf_0 WHERE races__year = 2008 AND races__name = 'Australian Grand Prix' AND results__position = 2
```

### 20. Q1464 (student_club, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT M.`first_name`, M.`last_name`, I.`amount`
FROM `Income` I
JOIN `Member` M ON M.`member_id` = I.`link_to_member`
WHERE I.`date_received` = '2019-09-09';
```

**Predicted SQL:**

```sql
SELECT
  T1.member_first_name || ' ' || T1.member_last_name,
  T1.income_amount
FROM (
  SELECT DISTINCT
    income__income_id,
    member__first_name AS member_first_name,
    member__last_name AS member_last_name,
    income__amount AS income_amount
  FROM one_nf_0
  WHERE income__date_received = '9/9/2019'
) AS T1;
```

### 21. Q206 (toxicology, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element FROM one_nf_0 WHERE molecule__label = 'TR004_8_9'
UNION
SELECT DISTINCT atom_2__element FROM one_nf_0 WHERE molecule__label = 'TR004_8_9'
```

### 22. Q751 (superhero, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superpower__power_name FROM one_nf_0 WHERE gender__gender = 'Male'
```

### 23. Q197 (toxicology, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['AVG', 'SUM']; predicted uses ['AVG', 'COUNT']

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(T1.oxygen_atom_count)
FROM (
    SELECT
        molecule__molecule_id,
        COUNT(DISTINCT CASE WHEN element = 'O' THEN atom_id END) AS oxygen_atom_count
    FROM (
        SELECT molecule__molecule_id, atom_1__atom_id AS atom_id, atom_1__element AS element
        FROM one_nf_0
        UNION
        SELECT molecule__molecule_id, atom_2__atom_id AS atom_id, atom_2__element AS element
        FROM one_nf_0
    ) AS all_atoms_in_molecules
    GROUP BY molecule__molecule_id
) AS T1
WHERE T1.molecule__molecule_id IN (
    SELECT DISTINCT molecule__molecule_id
    FROM one_nf_0
    WHERE bond__bond_type = 'single'
);
```

### 24. Q896 (formula_1, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT
  CAST(
    (SELECT COUNT(DISTINCT T1.races__race_id)
     FROM one_nf_0 AS T1
     WHERE T1.drivers__driver_ref_name = 'hamilton'
       AND T1.races__year >= 2010
       AND T1.circuits__circuit_id != 1)
  AS REAL) * 100.0 /
  (SELECT COUNT(DISTINCT T2.races__race_id)
   FROM one_nf_0 AS T2
   WHERE T2.drivers__driver_ref_name = 'hamilton'
     AND T2.races__year >= 2010)
```

### 25. Q1088 (european_football_2, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player__player_name FROM one_nf_0 WHERE Player_Attributes__volleys > 70 AND Player_Attributes__dribbling > 70
```

### 26. Q1157 (thrombosis_prediction, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__diagnosis FROM one_nf_0 WHERE Examination__thrombosis_degree = 'severe'
```

### 27. Q173 (financial, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT DISTINCT account__statement_frequency FROM one_nf_0 WHERE account__account_id = 3
UNION ALL
SELECT DISTINCT trans__transaction_operation FROM one_nf_0 WHERE trans__amount = 3539 AND trans__type = 'debit'
```

### 28. Q963 (formula_1, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT drivers__driver_id) FROM one_nf_0 WHERE drivers__nationality = 'French' AND lapTimes__time < '02:00.00'
```

### 29. Q169 (financial, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** SUM on fan-out 1NF rows: requires deduplicating subquery on fact keys; simple DISTINCT in SUM is insufficient

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
WITH TotalLoans1996 AS (
    SELECT SUM(T.loan_amount) AS total_amount
    FROM (
        SELECT DISTINCT loan__loan_id, loan__amount AS loan_amount
        FROM one_nf_0
        WHERE client__gender = 'M'
          AND strftime('%Y', loan__date) = '1996'
    ) AS T
),
TotalLoans1997 AS (
    SELECT SUM(T.loan_amount) AS total_amount
    FROM (
        SELECT DISTINCT loan__loan_id, loan__amount AS loan_amount
        FROM one_nf_0
        WHERE client__gender = 'M'
          AND strftime('%Y', loan__date) = '1997'
    ) AS T
)
SELECT
    (TL1997.total_amount - TL1996.total_amount) * 100.0 / TL1996.total_amount
FROM
    TotalLoans1996 AS TL1996,
    TotalLoans1997 AS TL1997;
```

### 30. Q253 (toxicology, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element, atom_2__element FROM one_nf_0 WHERE bond__bond_type = 'triple'
```

### 31. Q26 (california_schools, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT
  schools__School,
  schools__mailing_street,
  schools__mailing_city,
  schools__mailing_zip_code,
  schools__mailing_state
FROM one_nf_0
WHERE
  schools__City = 'Monterey' AND
  schools__instruction_level_name = 'High School' AND
  frpm__free_or_reduced_price_meal_count_ages_5_17 > 800;
```

### 32. Q1473 (debit_card_specializing, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['AVG', 'SUM']; predicted uses ['AVG']

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(yearmonth__consumption)
FROM (
  SELECT DISTINCT
    yearmonth__customer_id,
    yearmonth__date,
    yearmonth__consumption
  FROM one_nf_0
  WHERE customers__segment = 'SME'
    AND STRFTIME('%Y', yearmonth__date) = '2013'
)
```

### 33. Q230 (toxicology, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT DISTINCT molecule__label, atom_1__element FROM one_nf_0 WHERE molecule__molecule_id = 'TR060'
UNION
SELECT DISTINCT molecule__label, atom_2__element FROM one_nf_0 WHERE molecule__molecule_id = 'TR060'
```

### 34. Q249 (toxicology, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element FROM one_nf_0 WHERE molecule__label = 'TR144_8_19'
UNION
SELECT DISTINCT atom_2__element FROM one_nf_0 WHERE molecule__label = 'TR144_8_19'
```

### 35. Q1398 (student_club, moderate, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT event__event_name
FROM (
    SELECT DISTINCT
        event__event_id,
        event__event_name,
        budget__budget_id,
        budget__amount_spent
    FROM one_nf_0
    WHERE budget__category = 'advertisement'
) AS deduped_advertisement_budgets
GROUP BY
    event__event_id,
    event__event_name
ORDER BY
    SUM(budget__amount_spent) DESC
LIMIT 1;
```

### 36. Q829 (superhero, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT CASE WHEN marvel_cnt > dc_cnt THEN 'Marvel Comics' ELSE 'DC Comics' END AS publisher_with_more_superheroes,
        dc_cnt - marvel_cnt AS difference
FROM (
    SELECT SUM(CASE WHEN p.`publisher_name`='Marvel Comics' THEN 1 END) AS marvel_cnt,
           SUM(CASE WHEN p.`publisher_name`='DC Comics' THEN 1 END)    AS dc_cnt
    FROM `superhero` s
    JOIN `publisher` p ON s.`publisher_id` = p.`id`
) t;
```

**Predicted SQL:**

```sql
SELECT
  CASE
    WHEN (SELECT COUNT(DISTINCT superhero__id) FROM one_nf_0 WHERE publisher__publisher_name = 'DC Comics') >
         (SELECT COUNT(DISTINCT superhero__id) FROM one_nf_0 WHERE publisher__publisher_name = 'Marvel Comics')
    THEN 'DC Comics'
    WHEN (SELECT COUNT(DISTINCT superhero__id) FROM one_nf_0 WHERE publisher__publisher_name = 'Marvel Comics') >
         (SELECT COUNT(DISTINCT superhero__id) FROM one_nf_0 WHERE publisher__publisher_name = 'DC Comics')
    THEN 'Marvel Comics'
    ELSE 'Tie'
  END,
  ABS(
    (SELECT COUNT(DISTINCT superhero__id) FROM one_nf_0 WHERE publisher__publisher_name = 'DC Comics') -
    (SELECT COUNT(DISTINCT superhero__id) FROM one_nf_0 WHERE publisher__publisher_name = 'Marvel Comics')
  )
```

### 37. Q145 (financial, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** AVG over duplicated 1NF rows (and/or missing /12): dedup subquery needed; adding DISTINCT on the averaged column alone does not match 3NF gold

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.disp__account_id FROM one_nf_0 AS T1 WHERE T1.card__type = 'credit' AND strftime('%Y', T1.trans__date) = '1998' AND T1.trans__amount < ( SELECT AVG(T2.trans__amount) FROM ( SELECT DISTINCT trans__transaction_id, trans__amount FROM one_nf_0 ) AS T2 );
```

### 38. Q1265 (thrombosis_prediction, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID) FROM one_nf_0 WHERE Laboratory__anti_ribonuclear_protein = 'Normal' AND Patient__admission_type IS NOT NULL
```

### 39. Q62 (california_schools, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT schools__county_district_school_code) FROM one_nf_0 WHERE schools__Charter = 'No' AND schools__County = 'Los Angeles' AND frpm__percent_eligible_free_k12 < 0.18
```

### 40. Q1390 (student_club, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** SUM on fan-out 1NF rows: requires deduplicating subquery on fact keys; simple DISTINCT in SUM is insufficient

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT
  (SELECT SUM(T1.expense__cost) FROM (SELECT DISTINCT expense__expense_id, expense__cost FROM one_nf_0 WHERE event__event_name = 'Yearly Kickoff') AS T1) * 100.0 /
  (SELECT SUM(T2.expense__cost) FROM (SELECT DISTINCT expense__expense_id, expense__cost FROM one_nf_0) AS T2)
```

### 41. Q125 (financial, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT DISTINCT
  (district__unemployment_rate_1996 - district__unemployment_rate_1995)
FROM one_nf_0
WHERE
  loan__status = 'D';
```

### 42. Q231 (toxicology, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT bond__bond_type
FROM one_nf_0
WHERE molecule__label = 'TR010'
GROUP BY bond__bond_type
ORDER BY COUNT(DISTINCT bond__bond_id) DESC
LIMIT 1
```

### 43. Q1257 (thrombosis_prediction, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE
    Laboratory__creatinine IS NOT NULL
    AND
    (
        (CAST(strftime('%Y', Laboratory__Date) AS INTEGER) - CAST(strftime('%Y', Patient__birthday) AS INTEGER)) -
        (CASE WHEN strftime('%m%d', Laboratory__Date) < strftime('%m%d', Patient__birthday) THEN 1 ELSE 0 END)
    ) < 70;
```

### 44. Q1334 (student_club, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT DISTINCT member__first_name || ' ' || member__last_name FROM one_nf_0 WHERE zip_code__state = 'IL'
```

### 45. Q136 (financial, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT loan__loan_id)
FROM one_nf_0
WHERE
  loan__date BETWEEN '1995-01-01' AND '1997-12-31' AND
  loan__amount >= 250000 AND
  account__statement_frequency = 'monthly' AND
  loan__status = 'A';
```

### 46. Q1032 (european_football_2, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'MAX']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT League__name, COUNT(DISTINCT Match__id) FROM one_nf_0 GROUP BY League__name ORDER BY COUNT(DISTINCT Match__id) DESC LIMIT 1
```

### 47. Q1322 (student_club, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT event__event_id)
FROM one_nf_0
WHERE event__event_id IN (
    SELECT event__event_id
    FROM one_nf_0
    GROUP BY event__event_id
    HAVING COUNT(DISTINCT attendance__member_id) > 10
)
AND event__type = 'Meeting';
```

### 48. Q1281 (thrombosis_prediction, moderate, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(Patient__birthday) FROM one_nf_0 WHERE Laboratory__aspartate_aminotransferase IS NOT NULL
```

### 49. Q1267 (thrombosis_prediction, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'MAX']; predicted uses ['COUNT']

**Gold SQL:**

```sql
WITH normal_sm AS (
  SELECT DISTINCT `ID`
  FROM `Laboratory`
  WHERE `SM` IN ('negative','0')
), no_thrombosis AS (
  SELECT n.`ID`
  FROM normal_sm n
  JOIN `Examination` e ON e.`ID` = n.`ID`
  GROUP BY n.`ID`
  HAVING MAX(COALESCE(e.`Thrombosis`,0)) = 0
)
SELECT COUNT(*)
FROM no_thrombosis;
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID) FROM one_nf_0 WHERE Laboratory__anti_sm = 'normal' AND Examination__thrombosis_degree = 'normal'
```

### 50. Q115 (financial, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT
  CAST(
    (SELECT COUNT(DISTINCT T1.client__client_id)
     FROM one_nf_0 AS T1
     WHERE T1.client__district_id = (
       SELECT T2.district__district_id
       FROM one_nf_0 AS T2
       WHERE T2.district__region = 'south Bohemia'
       ORDER BY T2.district__number_inhabitants DESC
       LIMIT 1
     ) AND T1.client__gender = 'M')
  AS REAL) * 100.0 /
  (SELECT COUNT(DISTINCT T3.client__client_id)
   FROM one_nf_0 AS T3
   WHERE T3.client__district_id = (
     SELECT T4.district__district_id
     FROM one_nf_0 AS T4
     WHERE T4.district__region = 'south Bohemia'
     ORDER BY T4.district__number_inhabitants DESC
     LIMIT 1
   )
  )
```

