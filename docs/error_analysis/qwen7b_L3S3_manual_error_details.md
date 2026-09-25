# Qwen2.5-Coder-7B · L3·S3 — hand-classified failures (n=301)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Grouped by database, sorted by question id.

| Category | Legend |
|---|---|
| Invalid SQL | |
| Schema linking | |
| JOIN errors | |
| GROUP BY errors | |
| Nesting problem | |
| Predicate error | |
| Other | |

---

## california_schools (28 failures)

### Q5 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Virtual='F' (real code) is replaced with the invented value 'Yes' in predicted; an unneeded frpm join and a dropped rtype='S' filter are secondary compounding issues.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT `T2`.`CDSCode`)
FROM `satscores` AS T1
JOIN `schools`  AS T2 ON T1.`cds` = T2.`CDSCode`
WHERE T2.`Virtual` = 'F'
  AND T1.`AvgScrMath` > 400 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
JOIN satscores ON frpm.county_district_school_code = satscores.county_district_school_code 
JOIN schools ON frpm.county_district_school_code = schools.county_district_school_code 
WHERE satscores.average_score_math > 400 AND schools.Virtual = 'Yes';
```

### Q11 (simple, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters the raw per-row Enrollment sum (no grouping) with School IS NOT NULL; predicted adds an unwarranted GROUP BY CDSCode HAVING SUM(...)>500, aggregating potentially multiple per-year frpm rows per school into one, and drops the schools join/School-not-null check.

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT county_district_school_code 
FROM frpm 
GROUP BY county_district_school_code 
HAVING SUM(enrollment_k12) + SUM(enrollment_ages_5_17) > 500;
```

### Q12 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references T2.average_score_1500_or_above, which matches no real column or alias anywhere in the schema (the correct alias for NumGE1500 is 'number_scores_1500_or_above') -- a hallucinated identifier.

**Gold SQL:**

```sql
SELECT MAX(
         CAST(f.`Free Meal Count (Ages 5-17)` AS REAL) /
         f.`Enrollment (Ages 5-17)`
       ) AS max_eligible_free_rate
FROM frpm      AS f
JOIN satscores AS s
     ON f.`CDSCode` = s.`cds`
WHERE s.`rtype` = 'S'                  
  AND s.`NumTstTakr`  > 0               
  AND f.`Enrollment (Ages 5-17)` > 0    
  AND CAST(s.`NumGE1500` AS REAL) / s.`NumTstTakr` > 0.3;
```

**Predicted SQL:**

```sql
SELECT MAX(T1.percent_eligible_free_ages_5_17) AS max_eligible_free_rate
FROM frpm AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.average_score_1500_or_above > 0.3;
```

### Q17 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops both the CharterNum IS NOT NULL and rtype='S' filters that gold requires, changing which rows are included in the RANK() window.

**Gold SQL:**

```sql
SELECT CharterNum, AvgScrWrite, 
RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank 
FROM schools AS T1  INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds 
WHERE T2.AvgScrWrite > 499 AND CharterNum is not null AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT 
    T1.charter_number, 
    T2.average_score_writing, 
    RANK() OVER (ORDER BY T2.average_score_writing DESC) AS rank
FROM 
    schools AS T1
JOIN 
    satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.average_score_writing > 499;
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold requires a signed difference (Enrollment K-12 - Enrollment Ages 5-17) > 30; predicted wraps it in ABS(), which also passes rows where the difference is very negative, changing which schools qualify.

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    s.Street, 
    s.street_abbreviated, 
    s.City, 
    s.Zip, 
    s.State, 
    f.enrollment_k12 - f.enrollment_ages_5_17 AS enrollment_difference
FROM 
    frpm f
JOIN 
    schools s ON f.county_district_school_code = s.county_district_school_code
WHERE 
    ABS(f.enrollment_k12 - f.enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold recomputes the ratio directly from FreeMealCount(K-12)/Enrollment(K-12); predicted instead uses the different, pre-existing percent_eligible_free_k12 column (a stored percentage, not the freshly computed fraction gold's 0.1 threshold assumes) -- a wrong real column.

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT f.school_name
FROM frpm f
JOIN satscores s ON f.county_district_school_code = s.county_district_school_code
WHERE f.percent_eligible_free_k12 > 0.1 AND s.number_scores_1500_or_above > 0;
```

### Q25 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters District LIKE 'Riverside%'; predicted instead filters County='Riverside' -- a different, real column (same pattern the taxonomy calls out: County substituted for District); also drops the GROUP BY/HAVING AVG aggregation.

**Gold SQL:**

```sql
SELECT s.`sname`,
       sc.`FundingType`
FROM satscores AS s
JOIN schools  AS sc
  ON s.`cds` = sc.`CDSCode`
WHERE sc.`District` LIKE 'Riverside%'   AND s.rtype = 'S'
GROUP BY s.`sname`, sc.`FundingType`
HAVING AVG(s.`AvgScrMath`) > 400;
```

**Predicted SQL:**

```sql
SELECT s.School, s.funding_type 
FROM schools s 
JOIN satscores sa ON s.county_district_school_code = sa.county_district_school_code 
WHERE s.County = 'Riverside' AND sa.average_score_math > 400;
```

### Q26 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** School Type belongs to frpm (already joined as f); predicted references it via s (schools, which has no School Type column) instead -- an alias mix-up on an already-joined table; predicted also confuses FRPM Count (a raw count) with the pre-stored percent column for its threshold.

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    s.Street, 
    s.street_abbreviated, 
    s.City, 
    s.Zip, 
    s.State, 
    s.mailing_street, 
    s.mailing_street_abbreviated, 
    s.mailing_city, 
    s.mailing_zip_code, 
    s.mailing_state
FROM 
    schools s
JOIN 
    frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE 
    s.School_Type = 'High' 
    AND f.county_name = 'Monterey' 
    AND f.percent_eligible_free_or_reduced_price_meal_ages_5_17 > 800;
```

### Q27 (moderate, retrieval) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses LEFT JOIN schools->satscores to preserve schools without SAT score rows; predicted uses INNER JOIN, silently dropping schools with no matching satscores entry.

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    s.Street, 
    s.City, 
    s.Zip, 
    s.State, 
    s.mailing_city, 
    s.mailing_zip_code, 
    s.mailing_state, 
    s.Phone, 
    s.phone_extension, 
    s.Website, 
    ss.average_score_writing
FROM 
    schools s
JOIN 
    satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE 
    (s.open_date > '1991-12-31' OR s.closed_date < '2000-01-01');
```

### Q28 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects T2.DOCType (schools' district ownership type); predicted selects T1.district_type (frpm's 'District Type' column) instead -- a different, real column from a different table; ABS() wrapping, a truncated 'Local' literal (vs 'Locally funded'), and an added GROUP BY/HAVING are secondary issues.

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT 
    T1.school_name, 
    T1.district_type 
FROM 
    frpm AS T1 
JOIN 
    schools AS T2 
ON 
    T1.county_district_school_code = T2.county_district_school_code 
WHERE 
    T2.funding_type = 'Local' 
GROUP BY 
    T1.school_name, 
    T1.district_type 
HAVING 
    ABS(T1.enrollment_k12 - T1.enrollment_ages_5_17) > (SELECT AVG(ABS(enrollment_k12 - enrollment_ages_5_17)) FROM frpm WHERE funding_type = 'Local')
```

### Q31 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted adds a wholly fabricated WHERE condition (grade_span_offered LIKE '%10th%' OR '%11th%') not present in gold at all, and collapses gold's raw per-row ratio with OFFSET 9 LIMIT 2 into a single AVG() aggregate with LIMIT 10.

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT AVG(T1.percent_eligible_free_k12) AS avg_eligible_free_rate
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.grade_span_offered LIKE '%10th%' OR T2.grade_span_offered LIKE '%11th%'
ORDER BY T1.enrollment_k12 DESC
LIMIT 10;
```

### Q32 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold computes FRPM Count(K-12)/Enrollment(K-12) fresh; predicted substitutes the different, pre-stored percent_eligible_free_or_reduced_price_meal_k12 column instead -- same recurring 'stored percent vs freshly computed ratio' wrong-column pattern.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    T1.school_name, 
    T1.percent_eligible_free_or_reduced_price_meal_k12
FROM 
    frpm AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.school_ownership_code = 66
ORDER BY 
    T1.free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold picks a single top school via ORDER BY NumGE1500 DESC LIMIT 1 (with rtype='S' filter); predicted replaces this with a tie-preserving '= (SELECT MAX(number_scores_1500_or_above) FROM satscores)' equality subquery -- the ORDER BY/LIMIT1 <-> MAX-subquery swap pattern -- and drops the rtype='S' filter both outside and inside the subquery.

**Gold SQL:**

```sql
SELECT s.AdmFName1,
       s.AdmLName1,
       s.AdmFName2,
       s.AdmLName2,
       s.AdmFName3,
       s.AdmLName3
FROM satscores t
JOIN schools  s ON t.cds = s.CDSCode
WHERE t.rtype = 'S'    
ORDER BY t.NumGE1500 DESC
LIMIT 1;
```

**Predicted SQL:**

```sql
SELECT 
    T1.admin_first_name_1, 
    T1.admin_last_name_1, 
    T1.admin_email_1, 
    T1.admin_first_name_2, 
    T1.admin_last_name_2, 
    T1.admin_email_2, 
    T1.admin_first_name_3, 
    T1.admin_last_name_3, 
    T1.admin_email_3
FROM 
    schools AS T1
JOIN 
    satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.number_scores_1500_or_above = (SELECT MAX(number_scores_1500_or_above) FROM satscores);
```

### Q37 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold ranks schools by the proportion of test-takers scoring >=1500 (NumGE1500/NumTstTakr), taking the MINIMUM ratio; predicted instead computes the average of the three SAT subject scores and picks the lowest -- an entirely different, reinvented metric.

**Gold SQL:**

```sql
SELECT s.Street, s.City, s.State, s.Zip 
FROM schools s JOIN satscores sat ON s.CDSCode = sat.cds 
WHERE sat.NumTstTakr > 0 AND sat.NumGE1500 IS NOT NULL AND sat.NumTstTakr IS NOT NULL  AND rtype = 'S'
AND CAST(sat.NumGE1500 AS FLOAT) / CAST(sat.NumTstTakr AS FLOAT) =
 (SELECT MIN(CAST(NumGE1500 AS FLOAT) / CAST(NumTstTakr AS FLOAT)) 
 FROM satscores WHERE NumTstTakr > 0 AND NumGE1500 IS NOT NULL AND NumTstTakr IS NOT NULL AND rtype = 'S' )
```

**Predicted SQL:**

```sql
SELECT Street, City, State, Zip 
FROM schools 
WHERE county_district_school_code = (
    SELECT county_district_school_code 
    FROM satscores 
    ORDER BY (average_score_reading + average_score_math + average_score_writing) / 3 ASC 
    LIMIT 1
);
```

### Q40 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters schools.District; predicted filters satscores.dname (aliased district_name, on T1=satscores not T2=schools) instead -- a different real column in a different table for the same concept; the rtype='S' filter is also dropped.

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.Phone 
FROM satscores AS T1 
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.district_name = 'Fresno Unified' 
ORDER BY T1.average_score_reading ASC 
LIMIT 1;
```

### Q41 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a CTE with RANK() OVER (PARTITION BY county ORDER BY AvgScrRead DESC) to get the top-5 non-virtual schools per county; predicted has no window function or per-county partitioning at all -- it computes a single global top-5 by AVG reading score, and uses Virtual='Yes' instead of 'F'.

**Gold SQL:**

```sql
WITH ranked AS (
  SELECT s.`School`,
         s.`Virtual`,
         sc.`cname`,
         RANK() OVER (PARTITION BY sc.`cname` ORDER BY sc.`AvgScrRead` DESC) AS rnk
  FROM `schools` s
  JOIN `satscores` sc ON s.`CDSCode` = sc.`cds`
  WHERE sc.`AvgScrRead` IS NOT NULL AND rtype = 'S'
)
SELECT DISTINCT `School`
FROM ranked
WHERE `Virtual` = 'F'
  AND rnk <= 5;
```

**Predicted SQL:**

```sql
SELECT 
    s.School,
    s.County,
    AVG(ss.average_score_reading) AS avg_reading_score
FROM 
    schools s
JOIN 
    satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE 
    s.Virtual = 'Yes'
GROUP BY 
    s.School, s.County
ORDER BY 
    avg_reading_score DESC
LIMIT 5;
```

### Q46 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Gold needs frpm (DOC/Enrollment) joined with schools; predicted swaps frpm for satscores entirely and references T1.school_name (schools alias) which doesn't exist there -- the real school_name column lives on frpm, which isn't joined; the WHERE filter is also wrong (educational_option_name instead of DOC=31).

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.school_name, T1.state, SUM(T1.enrollment_grade_12) AS total_enrollment
FROM schools AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.educational_option_name = 'State Special'
GROUP BY T1.school_name, T1.state
ORDER BY total_enrollment DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters DOC=52 (district ownership code); predicted instead filters District='Elementary School District' (a different real column/domain) -- dropping the DOC filter entirely; the AVG(month formula) also replaces gold's simple COUNT/12.

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(CAST((strftime('%Y', open_date) - 1980) * 12 + strftime('%m', open_date) AS REAL)) AS avg_opening_month
FROM schools
WHERE County = 'Alameda' AND District = 'Elementary School District' AND open_date LIKE '1980%';
```

### Q48 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold computes two independent COUNT(*) subqueries filtered on schools.DOC ('54'/'52') and StatusType='Merged'; predicted instead uses frpm.district_type ('Unified'/'Elementary', an unrelated column on a different, extra-joined table) via conditional SUM, dropping the StatusType='Merged' filter entirely.

**Gold SQL:**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.district_type = 'Unified' THEN 1 ELSE 0 END) / 
    SUM(CASE WHEN T1.district_type = 'Elementary' THEN 1 ELSE 0 END) AS ratio
FROM 
    frpm AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T1.county_name = 'Orange';
```

### Q50 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects s.MailStreet (mailing address); predicted selects T2.street (the physical street) instead -- a different, real column.

**Gold SQL:**

```sql
SELECT s.`MailStreet`   AS postal_street_address,
       s.`School`
FROM   `satscores` AS ss
JOIN   `schools`   AS s
       ON ss.`cds` = s.`CDSCode`
WHERE  ss.`rtype` = 'S'
  AND  ss.`AvgScrMath` IS NOT NULL
ORDER BY ss.`AvgScrMath` DESC
LIMIT 6, 1;
```

**Predicted SQL:**

```sql
SELECT T2.street, T2.school 
FROM satscores AS T1 
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
ORDER BY T1.average_score_math DESC 
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters schools.Charter=0 (numeric flag); predicted instead filters frpm.is_charter_school=0, but that frpm column stores 'Y'/'N' text values, not 0/1 -- a different, wrong real column, plus dropping the schools join entirely.

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
WHERE county_name = 'Los Angeles' AND is_charter_school = 0 AND percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters schools.City='Fremont' and schools.EdOpsCode='SSS'; predicted instead filters frpm.county_name='Fremont' (City confused with County) and school_name LIKE '%State Special School%' (a fabricated pattern standing in for the EdOpsCode='SSS' code), dropping the schools join entirely.

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT SUM(enrollment_ages_5_17) AS total_students
FROM frpm
WHERE county_name = 'Fremont'
  AND school_name LIKE '%State Special School%'
  AND academic_year = '2014-2015';
```

### Q77 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters GSserved='K-9' (Grade Span Served); predicted filters grade_span_offered='K-9' (GSoffered, Grade Span Offered) instead -- a different, real column.

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    f.percent_eligible_free_or_reduced_price_meal_ages_5_17
FROM 
    schools s
JOIN 
    frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE 
    s.County = 'Los Angeles' 
    AND s.grade_span_offered = 'K-9';
```

### Q79 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by County (comparing San Diego vs Santa Barbara) and returns the one with more non-virtual schools; predicted has no GROUP BY at all, returning a single combined COUNT across both counties; Virtual=1 is also used instead of the real text code 'F'.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS num_virtual_schools
FROM schools
WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 1;
```

### Q82 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold sorts by ABS(longitude) DESC to find the school farthest from the meridian in either direction; predicted sorts by raw Longitude DESC (no ABS), which for California's uniformly-negative longitudes picks the closest-to-zero value instead of the most extreme -- a missing transformation in the ORDER BY expression, not a WHERE/HAVING predicate.

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered FROM schools ORDER BY Longitude DESC LIMIT 1;
```

### Q83 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters frpm.'NSLP Provision Status'='Multiple Provision Types'; predicted instead filters frpm.educational_option_type IN (...) -- a different real column (Educational Option Type, not NSLP Provision Status); GSoffered='K-8' exact match is also loosened into two LIKE patterns.

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT 
    T1.City, 
    COUNT(T1.school) AS school_count
FROM 
    schools AS T1
JOIN 
    frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T1.grade_span_offered LIKE '%K%' AND 
    T1.grade_span_offered LIKE '%8%' AND 
    T2.educational_option_type IN ('Multiple', 'Multiple Provision Types')
GROUP BY 
    T1.City;
```

### Q85 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold computes FRPM Count(K-12)*100/Enrollment(K-12) fresh; predicted substitutes the different, pre-stored percent_eligible_free_k12 column instead -- same recurring 'stored percent vs freshly computed ratio' wrong-column pattern as Q24/Q32.

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT T1.percent_eligible_free_k12, T1.district_code 
FROM frpm AS T1 
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.admin_first_name_1 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops DOC=54 and SOC=62 entirely, replacing them with fabricated conditions unrelated to gold (grade_span_offered LIKE patterns, educational_option_name LIKE '%Unified%'), and uses an invented City value 'City of San Bernardino City Unified' instead of 'San Bernardino'.

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT 
    admin_email_1 AS email1, 
    admin_email_2 AS email2, 
    admin_email_3 AS email3
FROM 
    schools
WHERE 
    County = 'San Bernardino' 
    AND City = 'City of San Bernardino City Unified' 
    AND open_date BETWEEN '2009-01-01' AND '2010-12-31' 
    AND grade_span_offered LIKE '%Intermediate%' 
    AND grade_span_offered LIKE '%Middle%' 
    AND educational_option_name LIKE '%Unified%'
```

---

## debit_card_specializing (26 failures)

### Q1471 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold aggregates directly over customers (no join); predicted adds an unneeded join to transactions_1k, multiplying counts per customer's transactions and changing the EUR/CZK ratio.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T2.currency = 'EUR' THEN 1 ELSE 0 END) * 1.0 / 
    SUM(CASE WHEN T2.currency = 'CZK' THEN 1 ELSE 0 END) AS ratio
FROM 
    transactions_1k AS T1
JOIN 
    customers AS T2 ON T1.customer_id = T2.customer_id;
```

### Q1472 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Predicted lacks GROUP BY CustomerID / SUM(Consumption) entirely -- it embeds a strftime filter restricting to a single month ('2012-01') inside the JOIN and just returns one unaggregated row instead of grouping and summing across all of 2012 per customer.

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.customer_id, c.segment, c.currency, y.consumption
FROM customers c
JOIN yearmonth y ON c.customer_id = y.customer_id AND strftime('%Y-%m', y.date) = '2012-01'
WHERE c.segment = 'LAM'
ORDER BY y.consumption ASC
LIMIT 1;
```

### Q1473 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a derived table (FROM (SELECT ... GROUP BY CustomerID)) to sum consumption per customer before averaging /12; predicted has no subquery at all, just a flat AVG(consumption) over raw rows.

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) AS avg_monthly_consumption
FROM yearmonth
JOIN customers ON yearmonth.customer_id = customers.customer_id
WHERE customers.segment = 'SME' AND strftime('%Y', yearmonth.date) = '2013';
```

### Q1476 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold joins customers+yearmonth directly; predicted routes through an extra transactions_1k join matched on date+customer_id, duplicating yearmonth rows per transaction on that date.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.currency = 'CZK' THEN T3.consumption ELSE 0 END) - 
    SUM(CASE WHEN T1.currency = 'EUR' THEN T3.consumption ELSE 0 END) AS consumption_difference
FROM 
    customers AS T1
JOIN 
    transactions_1k AS T2 ON T1.customer_id = T2.customer_id
JOIN 
    yearmonth AS T3 ON T2.date = T3.date AND T2.customer_id = T3.customer_id
WHERE 
    strftime('%Y', T2.date) = '2012';
```

### Q1479 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Currency lives on customers, which gold joins; predicted swaps customers for transactions_1k and references a nonexistent T2.currency there instead.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT strftime('%Y', T2.date) AS year
FROM yearmonth AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id AND T1.date = T2.date
WHERE T2.currency = 'CZK'
GROUP BY year
ORDER BY SUM(T1.consumption) DESC
LIMIT 1;
```

### Q1480 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted's GROUP BY T1.month references T1 (the inner yearmonth alias), which has no 'month' column -- 'month' only exists as a SELECT-list alias, not a real column anywhere.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.month, MAX(T1.consumption) AS peak_consumption
FROM (
    SELECT strftime('%Y-%m', T2.date) AS month, SUM(T2.amount / T2.price) AS consumption
    FROM yearmonth AS T1
    JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id AND T1.date = T2.date
    WHERE T1.customer_id IN (
        SELECT customer_id
        FROM customers
        WHERE segment = 'SME'
    )
    AND T2.date LIKE '2013%'
    GROUP BY T1.month
) AS T1;
```

### Q1481 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted's subquery is a single-table query on transactions_1k (no JOIN at all) referencing 'currency', a column that only exists on customers -- a column borrowed from a sibling table with no join present.

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM transactions_1k WHERE date LIKE '2013%' AND currency = 'CZK' GROUP BY customer_id ORDER BY SUM(amount) ASC LIMIT 1) AND date LIKE '2013%') -
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM transactions_1k WHERE date LIKE '2013%' AND currency = 'CZK' GROUP BY customer_id ORDER BY SUM(amount) DESC LIMIT 1) AND date LIKE '2013%')
```

### Q1482 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops the T1.Currency='EUR' filter entirely and fabricates prior-year values via arbitrary multipliers (0.85/0.9/0.75) instead of computing real 2012 sums the way gold does.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T1.segment = 'SME' THEN T2.consumption ELSE 0 END) - SUM(CASE WHEN T1.segment = 'SME' THEN T2.consumption * 0.85 ELSE 0 END)) / SUM(CASE WHEN T1.segment = 'SME' THEN T2.consumption * 0.85 ELSE 0 END) * 100 AS SME_change,
    (SUM(CASE WHEN T1.segment = 'LAM' THEN T2.consumption ELSE 0 END) - SUM(CASE WHEN T1.segment = 'LAM' THEN T2.consumption * 0.9 ELSE 0 END)) / SUM(CASE WHEN T1.segment = 'LAM' THEN T2.consumption * 0.9 ELSE 0 END) * 100 AS LAM_change,
    (SUM(CASE WHEN T1.segment = 'KAM' THEN T2.consumption ELSE 0 END) - SUM(CASE WHEN T1.segment = 'KAM' THEN T2.consumption * 0.75 ELSE 0 END)) / SUM(CASE WHEN T1.segment = 'KAM' THEN T2.consumption * 0.75 ELSE 0 END) * 100 AS KAM_change
FROM 
    customers AS T1
JOIN 
    yearmonth AS T2 ON T1.customer_id = T2.customer_id
WHERE 
    T2.date BETWEEN '2012-01-01' AND '2012-12-31'
    OR T2.date BETWEEN '2013-01-01' AND '2013-12-31';
```

### Q1483 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** yearmonth.Date is stored as plain 'YYYYMM' (e.g. '201308'); predicted uses hyphenated 'YYYY-MM' bounds ('2013-08'/'2013-11') which don't match the real format.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consumption) AS total_consumption
FROM yearmonth
WHERE customer_id = 6 AND date BETWEEN '2013-08' AND '2013-11';
```

### Q1484 (simple, aggregate) — **Nesting problem** (Wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** Predicted uses EXCEPT between two COUNT(*) subqueries to try to compute a numeric difference -- EXCEPT is a set operation, not arithmetic subtraction, so it doesn't reproduce gold's SUM(IIF(...)) difference; literals are also wrong ('Czech Republic'/'Slovakia' spelled out instead of 'CZE'/'SVK', and lowercase 'discount').

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS difference
FROM gasstations
WHERE country = 'Czech Republic' AND segment = 'discount'
  EXCEPT
SELECT COUNT(*) AS discount_stations_in_slovakia
FROM gasstations
WHERE country = 'Slovakia' AND segment = 'discount';
```

### Q1486 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** Currency belongs to customers (already joined as T1); predicted references T2.currency (transactions_1k) instead -- an alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T2.currency = 'CZK' THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.currency = 'EUR' THEN 1 ELSE 0 END) AS difference
FROM customers AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.segment = 'SME';
```

### Q1490 (moderate, aggregate) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses LEFT JOIN yearmonth to preserve customers with no consumption rows; predicted uses INNER JOIN, silently dropping such customers from the denominator; it also drops COUNT(DISTINCT ...).

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM customers AS T1 JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'LAM';
```

### Q1493 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** yearmonth.Date is plain text 'YYYYMM'; predicted applies strftime('%Y-%m', T2.date)='2012-02' to it, a transformation that doesn't parse a non-ISO text value -- gold just compares Date='201202' directly.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id)
FROM customers AS T1
JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id AND strftime('%Y-%m', T2.date) = '2012-02';
```

### Q1498 (simple, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by month (SUBSTR(Date,5,2)) and sums consumption per month, taking the highest monthly total; predicted has no GROUP BY at all and just takes MAX(consumption) over individual readings.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) AS highest_monthly_consumption FROM yearmonth WHERE date LIKE '2012%';
```

### Q1500 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold only joins transactions_1k+products, filtering date directly; predicted adds an unnecessary join to yearmonth (matched on customer_id), duplicating rows across a customer's multiple yearmonth entries, and drops DISTINCT.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL:**

```sql
SELECT T3.description FROM transactions_1k AS T1 JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id AND T1.date LIKE '2012-08-%' JOIN products AS T3 ON T1.product_id = T3.product_id
```

### Q1505 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Currency='EUR' is written as the lowercase/spelled-out 'euro' in predicted -- the extra join to transactions_1k is vestigial (COUNT DISTINCT customer_id absorbs any duplication) and not the actual cause.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.customer_id)
FROM customers c
JOIN transactions_1k t ON c.customer_id = t.customer_id
JOIN yearmonth ym ON c.customer_id = ym.customer_id
WHERE c.currency = 'euro' AND ym.consumption > 1000;
```

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Country='CZE' (real code) is replaced with the spelled-out 'Czech Republic' in predicted.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT T3.description FROM transactions_1k AS T1 JOIN gasstations AS T2 ON T1.gas_station_id = T2.gas_station_id JOIN products AS T3 ON T1.product_id = T3.product_id WHERE T2.country = 'Czech Republic'
```

### Q1509 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Country='CZE' (real code) is replaced with the spelled-out 'Czech Republic' in predicted.

**Gold SQL:**

```sql
SELECT COUNT(t.`TransactionID`)
FROM `transactions_1k` AS t
JOIN `gasstations` AS g
  ON t.`GasStationID` = g.`GasStationID`
WHERE g.`Country` = 'CZE'
  AND DATE(t.`Date`) > '2012-01-01';
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM transactions_1k 
JOIN gasstations ON transactions_1k.gas_station_id = gasstations.gas_station_id 
WHERE gasstations.country = 'Czech Republic' AND transactions_1k.date > '2012-01-01';
```

### Q1514 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold's join to gasstations is vestigial (doesn't restrict rows); the real cause is predicted's missing DISTINCT, which can return duplicate/multiple currency rows if more than one transaction matches that exact date+time.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT T1.currency 
FROM customers AS T1 
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id 
WHERE T2.time = '16:25:00' AND T2.date = '2012-08-24';
```

### Q1524 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters T1.Price=548.4; predicted filters T2.amount=548.4 instead -- Amount (quantity) and Price (unit price) are two different real columns on transactions_1k.

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT T1.country 
FROM gasstations AS T1 
JOIN transactions_1k AS T2 ON T1.gas_station_id = T2.gas_station_id 
WHERE T2.amount = 548.4 AND T2.date = '2012-08-24';
```

### Q1525 (simple, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold uses COUNT(DISTINCT CustomerID) for both numerator and denominator; predicted uses SUM(CASE...)/COUNT(*) over raw joined rows, which double-counts customers with multiple transactions on that date.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM customers AS T1 
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id 
WHERE T2.date = '2012-08-25';
```

### Q1526 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** yearmonth.Date is monthly ('YYYYMM'), not a full date; predicted filters y1.date='2012-08-25'/y2.date='2013-08-25' (day-level format) which never matches, and compares single specific dates instead of gold's whole-year SUM(IIF(SUBSTRING(Date,1,4)=...)) aggregation.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    (y2.consumption - y1.consumption) / y1.consumption AS consumption_decrease_rate
FROM 
    yearmonth y1
JOIN 
    yearmonth y2 ON y1.customer_id = y2.customer_id AND y2.date = '2013-08-25'
WHERE 
    y1.date = '2012-08-25' AND y1.customer_id IN (
        SELECT 
            t1.customer_id
        FROM 
            transactions_1k t1
        WHERE 
            t1.amount = 634.8 AND t1.date = '2012-08-25'
    );
```

### Q1528 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Gold is a single-table query on gasstations (Country/Segment); predicted queries customers/yearmonth entirely instead -- unrelated tables; 'country' doesn't exist on customers, only on gasstations, which predicted never references.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T2.segment = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(T1.customer_id)) AS premium_percentage
FROM 
    yearmonth AS T1
JOIN 
    customers AS T2 ON T1.customer_id = T2.customer_id
WHERE 
    T2.country = 'SVK';
```

### Q1529 (moderate, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Predicted computes SUM(amount) instead of SUM(amount*price) -- missing the price multiplication factor entirely, for both the total and the August-only subtotal.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent, 
       SUM(CASE WHEN date LIKE '2012-08-%' THEN amount ELSE 0 END) AS august_spent
FROM transactions_1k
WHERE customer_id = 38508;
```

### Q1531 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold picks the top-spending customer via a nested subquery ranked by SUM(Amount*Price); predicted flattens this into one query, ranking instead by SUM(amount) directly in the outer ORDER BY/LIMIT, and computes AVG(price) instead of the weighted SUM(price*amount)/SUM(amount).

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT 
    c.customer_id, 
    AVG(t.price) AS avg_price_per_item, 
    c.currency
FROM 
    transactions_1k t
JOIN 
    customers c ON t.customer_id = c.customer_id
GROUP BY 
    c.customer_id, 
    c.currency
ORDER BY 
    SUM(t.amount) DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Predicted's JOIN ON adds y.date = t.date, comparing yearmonth's 'YYYYMM' format against transactions_1k's 'YYYY-MM-DD' format -- these never match; gold joins solely on CustomerID and filters T2.Date='201208' separately via WHERE.

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT y.consumption
FROM yearmonth y
JOIN transactions_1k t ON y.customer_id = t.customer_id AND y.date = t.date
WHERE t.product_id = 5 AND t.price > 29.00 AND y.date LIKE '2012-08-%';
```

---

## european_football_2 (33 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2015/2016' (real 'YYYY/YYYY' format) is truncated to '2016' in predicted.

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League AS L 
JOIN Match AS M ON L.id = M.league_id 
WHERE M.season = '2016' 
GROUP BY L.name 
ORDER BY SUM(M.home_team_goals + M.away_team_goals) DESC 
LIMIT 1;
```

### Q1028 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses GROUP BY+HAVING with a nested tie-preserving MAX(win_count) subquery to find the team(s) with the most away wins; predicted has no GROUP BY/HAVING at all -- just a flat filter returning every team that won any away match; league name and season literals are also wrong.

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T2.team_long_name
FROM Match AS T1
JOIN Team AS T2 ON T1.away_team_api_id = T2.team_api_id
JOIN League AS T3 ON T1.league_id = T3.id
JOIN Country AS T4 ON T3.country_id = T4.id
WHERE T4.name = 'Scotland' AND T3.name = 'Scottish Premier League' AND T1.season = '2010/2011'
AND T1.away_team_goals > T1.home_team_goals;
```

### Q1030 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold checks home_team_goal = away_team_goal (a draw); predicted instead filters M.goal = 0, a different real column (an XML blob of goal event details on Match) that doesn't represent draws at all; season format is also wrong ('2016' vs '2015/2016').

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League AS L 
JOIN Match AS M ON L.id = M.league_id 
WHERE M.season = '2016' AND M.goal = 0 
GROUP BY L.name 
ORDER BY COUNT(M.match_api_id) DESC 
LIMIT 1;
```

### Q1031 (challenging, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold's age calculation includes a CASE adjustment for whether the birthday has occurred yet this year; predicted's simpler year-difference formula omits this adjustment -- a SELECT-expression computation difference, not a WHERE/HAVING predicate; DISTINCT is also dropped.

**Gold SQL:**

```sql
SELECT DISTINCT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T2.Birthday) - CASE
    WHEN strftime('%m-%d','now') < strftime('%m-%d', Birthday) THEN 1
    ELSE 0
  END AS age FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE STRFTIME('%Y',t1."date") >= '2013' AND STRFTIME('%Y',t1."date") <= '2015' AND t1.sprint_speed >= 97
```

**Predicted SQL:**

```sql
SELECT P.player_name, (strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS age
FROM Player P
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id
WHERE PA.sprint_speed >= 97 AND PA.date BETWEEN '2013-01-01' AND '2015-12-31';
```

### Q1032 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (...)) -- a tie-preserving pattern; predicted collapses this to ORDER BY match_count DESC LIMIT 1.

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(M.id) AS match_count
FROM League L
JOIN Match M ON L.id = M.league_id
GROUP BY L.id
ORDER BY match_count DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses strict inequalities (>50 AND <60, excluding the boundary values); predicted uses BETWEEN 50 AND 60 (inclusive), including teams at exactly 50 or 60.

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT team_fifa_api_id 
FROM Team_Attributes 
WHERE buildup_play_speed BETWEEN 50 AND 60;
```

### Q1036 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The join/subquery structure and thresholds are functionally equivalent to gold; the likely cause is predicted's missing DISTINCT, which can return duplicate team names if a team has multiple qualifying 2012 attribute rows.

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T1.team_long_name 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
WHERE T2.buildup_play_passing > (SELECT AVG(buildup_play_passing) FROM Team_Attributes WHERE date LIKE '2012%') 
AND T2.date LIKE '2012%'
```

### Q1037 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** preferred_foot lives on Player_Attributes, not Player; predicted queries Player alone with no join to Player_Attributes at all.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'Left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player 
WHERE birthday BETWEEN '1987-01-01' AND '1992-12-31';
```

### Q1040 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by (player_api_id, player_name) to keep same-named players distinct; predicted groups by player_name only, which would merge distinct players who happen to share a name.

**Gold SQL:**

```sql
SELECT p.player_name
FROM Player            AS p
JOIN  Player_Attributes AS pa
      ON p.player_api_id = pa.player_api_id
WHERE p.height > 180
GROUP BY p.player_api_id, p.player_name
ORDER BY AVG(pa.heading_accuracy) DESC
LIMIT 10;
```

**Predicted SQL:**

```sql
SELECT P.player_name, AVG(PA.heading_accuracy) AS avg_heading_accuracy
FROM Player AS P
JOIN Player_Attributes AS PA ON P.player_api_id = PA.player_api_id
WHERE P.height > 180
GROUP BY P.player_name
ORDER BY avg_heading_accuracy DESC
LIMIT 10;
```

### Q1042 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2009/2010' (real 'YYYY/YYYY' format) is shortened to '2009/10' in predicted; the HAVING formula itself (AVG vs SUM/COUNT) is mathematically equivalent to gold's, not a real bug.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2009/2010' GROUP BY t1.name HAVING (CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) - (CAST(SUM(t2.away_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) > 0
```

**Predicted SQL:**

```sql
SELECT L.name
FROM League AS L
JOIN Match AS M ON L.id = M.league_id
WHERE M.season = '2009/10'
GROUP BY L.id
HAVING AVG(M.home_team_goals) > AVG(M.away_team_goals);
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted adds a fabricated attacking_work_rate filter with no basis in gold, and loosens/miscases the defensive_work_rate condition (capitalized 'High'/'Medium' OR'd, instead of gold's exact lowercase 'high').

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.player_api_id)
FROM Player p
JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id
WHERE p.birthday < '1986-01-01'
AND (pa.defensive_work_rate = 'High' OR pa.defensive_work_rate = 'Medium')
AND (pa.attacking_work_rate = 'Low' OR pa.attacking_work_rate = 'Medium');
```

### Q1088 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The join/filter logic exactly matches gold; predicted's only difference is a missing DISTINCT, which can return duplicate player names across multiple qualifying attribute snapshots.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT P.player_name 
FROM Player AS P 
JOIN Player_Attributes AS PA ON P.player_api_id = PA.player_api_id 
WHERE PA.volleys > 70 AND PA.dribbling > 70;
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (...)) -- a tie-preserving pattern; predicted collapses this to ORDER BY COUNT(match_api_id) DESC LIMIT 1.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League AS L 
JOIN Match AS M ON L.id = M.league_id 
WHERE M.season = '2008/2009' 
GROUP BY L.name 
ORDER BY COUNT(M.match_api_id) DESC 
LIMIT 1;
```

### Q1094 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** player_name lives on Player, not Player_Attributes; predicted never joins Player at all, incorrectly self-joining Player_Attributes to itself on player_api_id (which would only match a player to their own other records); it also misses gold's per-player 'most recent rating' CTE entirely.

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT (T1.overall_rating - T2.overall_rating) * 100 / T2.overall_rating AS percentage_increase FROM Player_Attributes AS T1 JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.player_name = 'Ariel Borysiuk' AND T2.player_name = 'Paulin Puel'
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Player_Attributes.date is stored as a full datetime string; gold uses SUBSTR(date,1,10) to compare just the date portion; predicted compares date directly with '=', which won't match the full datetime value.

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.player_name 
FROM Player AS P 
JOIN Player_Attributes AS PA ON P.player_api_id = PA.player_api_id 
WHERE PA.overall_rating = 77 AND PA.date = '2016-06-23' 
ORDER BY P.birthday ASC 
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Player_Attributes.date is stored as a full datetime string; gold uses SUBSTR(date,1,10) for comparison; predicted uses a direct '=' match instead, which won't match the full datetime value.

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT T1.overall_rating 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Aaron Mooy' AND T1.date = '2016-02-04';
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses date LIKE '2015-05-01%' (prefix match against a full datetime); predicted uses a direct '=' match against a date-only literal instead.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.attacking_work_rate 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Francesco Migliore' AND T1.date = '2015-05-01';
```

### Q1107 (moderate, retrieval) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold joins Player to Player_Attributes on player_fifa_api_id; predicted joins on player_api_id instead -- both are real columns present on both tables, but this dataset has known inconsistencies between the two ID columns, so using the wrong one changes matched rows; the secondary date tiebreak is also dropped.

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.date 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Kevin Constant' 
ORDER BY T1.crossing DESC 
LIMIT 1;
```

### Q1110 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses date LIKE '2010-02-22%' (prefix match against a full datetime); predicted uses a direct '=' match against a date-only literal instead.

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT T2.buildup_play_passing_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_long_name = 'FC Lorient' AND T2.date = '2010-02-22';
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses date LIKE '2015-09-10%' (prefix match against a full datetime); predicted uses a direct '=' match against a date-only literal instead.

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT T2.defence_aggression_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_long_name = 'Hannover 96' AND T2.date = '2015-09-10';
```

### Q1114 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold joins Player to Player_Attributes on player_fifa_api_id; predicted joins on player_api_id instead -- the recurring wrong-join-key issue in this dataset.

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(T1.overall_rating) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Marko Arnautovic' AND T1.date BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold joins Player to Player_Attributes on player_fifa_api_id; predicted correlates the two via player_api_id-based subqueries instead -- the same recurring wrong-join-key issue.

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT ((SELECT overall_rating FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Landon Donovan') AND date = '2013-07-12') - 
(SELECT overall_rating FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Jordan Bowery') AND date = '2013-07-12')) * 100 / 
(SELECT overall_rating FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Jordan Bowery') AND date = '2013-07-12')
```

### Q1122 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold finds player(s) with MAX(overall_rating); predicted instead orders by T2.strength DESC -- a completely different real attribute; it also collapses the tie-preserving MAX subquery into ORDER BY/LIMIT 1.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT T1.player_name FROM Player AS T1 JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id ORDER BY T2.strength DESC LIMIT 1
```

### Q1124 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** attacking_work_rate is a categorical text column ('low'/'medium'/'high'), not numeric; predicted computes AVG(attacking_work_rate) and compares with '>', a nonsensical numeric transformation of a text column -- gold simply filters attacking_work_rate = 'high'.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.player_name FROM Player p JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id WHERE pa.attacking_work_rate > ( SELECT AVG(attacking_work_rate) FROM Player_Attributes )
```

### Q1130 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** chanceCreationPassingClass='Safe' (real value) is replaced with the invented value 'Low' in predicted.

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T1.team_short_name FROM Team AS T1 JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id WHERE T2.chance_creation_passing_class = 'Low'
```

### Q1133 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold requires STRFTIME year > '1990' (born 1991 or later); predicted uses birthday > '1990-01-01' instead, which incorrectly includes players born anytime in 1990 itself.

**Gold SQL:**

```sql
SELECT COUNT(id) FROM Player WHERE STRFTIME('%Y', birthday) > '1990' AND player_name LIKE 'Aaron%'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player WHERE player_name LIKE 'Aaron%' AND birthday > '1990-01-01';
```

### Q1134 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references T1.attribute_id, which matches no real column anywhere in this schema -- Player_Attributes' PK is just 'id' (gold filters on id=6/23 directly).

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL:**

```sql
SELECT AVG(T1.jumping) - AVG(T2.jumping) AS difference FROM Player_Attributes AS T1 JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.attribute_id = 6 AND T2.attribute_id = 23
```

### Q1135 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects Player_Attributes.id (its own PK); predicted selects player_api_id instead -- a different real column (FK to Player, not the attributes-row PK).

**Gold SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT player_api_id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

### Q1139 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** League name 'Belgium Jupiler League' is misspelled as 'Belgian Jupiler League' in predicted.

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT home_team_goals, away_team_goals 
FROM Match 
WHERE date = '2008-09-24' AND league_id IN (SELECT id FROM League WHERE name = 'Belgian Jupiler League');
```

### Q1144 (simple, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a nested '= (SELECT MAX(weight)...)' subquery (tie-preserving); predicted collapses this into ORDER BY weight DESC LIMIT 1 -- the same MAX-subquery/ORDER-BY-LIMIT1 swap pattern.

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT T1.finishing, T1.curve 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
ORDER BY T2.weight DESC 
LIMIT 1;
```

### Q1145 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2015/2016' (real 'YYYY/YYYY' format) is shortened to '2015/16' in predicted.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(M.id) AS game_count
FROM League L
JOIN Match M ON L.id = M.league_id
WHERE M.season = '2015/16'
GROUP BY L.name
ORDER BY game_count DESC
LIMIT 4;
```

### Q1147 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold finds player(s) with MAX(overall_rating); predicted instead orders by T2.strength DESC -- a completely different real attribute (identical bug to Q1122).

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT T1.player_name FROM Player AS T1 JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id ORDER BY T2.strength DESC LIMIT 1
```

### Q1148 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references T1.overall_strength, which matches no real column anywhere in the schema -- the real column is overall_rating.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.height < 180 AND T1.overall_strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.player_api_id)
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id;
```

---

## financial (25 failures)

### Q89 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters account.frequency='POPLATEK PO OBRATU'; predicted instead filters disp.type='issuance after transaction' (an unrelated column -- disp.type holds OWNER/DISPONENT codes, not payment frequency) via an unnecessary added join chain (account->disp->client->district).

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT t1.account_id)
FROM account AS t1
JOIN disp AS t2 ON t1.account_id = t2.account_id
JOIN client AS t3 ON t2.client_id = t3.client_id
JOIN district AS t4 ON t3.district_id = t4.district_id
WHERE t4.region = 'East Bohemia' AND t2.type = 'issuance after transaction';
```

### Q93 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** A3='north Bohemia' (lowercase 'north') is capitalized to 'North Bohemia' in predicted -- a case mismatch.

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(client_id) 
FROM client 
JOIN district ON client.district_id = district.district_id 
WHERE gender = 'M' AND region = 'North Bohemia' AND average_salary > 8000;
```

### Q94 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** account_id is real (on account), reached via disp; predicted selects account_id directly from client (no such column there), skipping the required disp/account join chain.

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT account_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1) AS oldest_female_client_account,
    (SELECT MAX(average_salary) - MIN(average_salary) FROM district) AS salary_gap;
```

### Q98 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters account.frequency='POPLATEK TYDNE'; predicted drops that filter and instead adds loan.status='approved', an unrelated column with an invented value not among the real status codes (A/B/C/D).

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE strftime('%Y', l.date) = '1997' AND l.status = 'approved'
ORDER BY l.amount ASC
LIMIT 1;
```

### Q100 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** District Name 'Sokolov' is misspelled as 'Sokolow' in predicted's subquery literal.

**Gold SQL:**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.client_id) 
FROM client c 
JOIN disp d ON c.client_id = d.client_id 
JOIN account a ON d.account_id = a.account_id 
WHERE c.gender = 'F' 
AND c.birth_date < '1950-01-01' 
AND c.district_id IN (SELECT district_id FROM district WHERE district_name = 'Sokolow');
```

### Q112 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** district_name (district.A2) is real, reached via district; predicted's alias 'd' refers to disp (not district, which is never joined at all), so district_name doesn't exist there.

**Gold SQL:**

```sql
SELECT DISTINCT d.A2
FROM `client`  c
JOIN `disp`    di ON di.`client_id` = c.`client_id`
JOIN `account`  a  ON a.`account_id` = di.`account_id`
JOIN `district` d  ON d.`district_id` = a.`district_id`
WHERE c.`gender` = 'F'
  AND c.`birth_date` = '1976-01-29';
```

**Predicted SQL:**

```sql
SELECT d.district_name
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN account a ON d.account_id = a.account_id
WHERE c.gender = 'F' AND c.birth_date = '1976-01-29';
```

### Q115 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by T2.A4 (district code) to compare across districts and picks the highest-coded group; predicted has no GROUP BY at all, computing one aggregate over the whole south-Bohemia population.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.client_id) AS percentage_male_clients
FROM district AS T1
JOIN client AS T3 ON T1.district_id = T3.district_id
WHERE T1.region = 'South Bohemia'
ORDER BY T1.number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold identifies the target account via loan.date='1993-07-05' (joining loan->account->trans); predicted never joins loan at all, self-joining trans directly on matching dates without identifying the specific account.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT 
    (t2.balance_after_transaction - t1.balance_after_transaction) / t1.balance_after_transaction * 100 AS balance_increase_rate
FROM 
    trans t1
JOIN 
    trans t2 ON t1.account_id = t2.account_id AND t1.date < t2.date
WHERE 
    t1.date = '1993-03-22' AND t2.date = '1998-12-27';
```

### Q117 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold has no WHERE clause (denominator = SUM(amount) over ALL loans); predicted translates status 'A' to invented label 'Fully Paid' and additionally adds a WHERE status IN ('Fully Paid','No Issue') filter gold doesn't have, narrowing the denominator.

**Gold SQL:**

```sql
SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.status = 'Fully Paid' THEN T1.amount ELSE 0 END) AS REAL) * 100 / SUM(T1.amount) FROM loan AS T1 WHERE T1.status IN ('Fully Paid', 'No Issue');
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='C' (real code) is translated to the invented label 'running' in predicted.

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.status = 'running' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM loan AS T1 
WHERE T1.amount < 100000;
```

### Q125 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted replaces l.status='D' with an invented 'running', drops the A12/A13 NOT NULL and A12>0 guards, adds a fabricated condition (l.amount > SUM of debit transactions) not in gold, and computes a raw difference instead of gold's percentage-change formula.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.unemployment_rate_1996 - d.unemployment_rate_1995 AS unemployment_rate_increment
FROM district d
JOIN account a ON d.district_id = a.district_id
JOIN loan l ON a.account_id = l.account_id
WHERE l.status = 'running' AND l.amount > (SELECT SUM(t.amount) FROM trans t WHERE t.account_id = a.account_id AND t.type = 'debit');
```

### Q129 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** 'VYDAJ' is translated to the invented label 'withdrawal'; predicted also adds a fabricated filter t.transaction_type_code != 'credit_card' not present in gold, using an invented literal.

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT d.district_name
FROM district d
JOIN account a ON d.district_id = a.district_id
JOIN trans t ON a.account_id = t.account_id
WHERE t.type = 'withdrawal' AND t.transaction_type_code != 'credit_card' AND t.date LIKE '1996-01-%'
ORDER BY t.amount DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** frequency='POPLATEK MESICNE' (real code) is translated to the invented label 'monthly' in predicted.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT l.account_id)
FROM loan l
JOIN account a ON l.account_id = a.account_id
WHERE l.date BETWEEN '1995-01-01' AND '1997-12-31'
AND l.amount >= 250000
AND a.statement_frequency = 'monthly';
```

### Q137 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold filters loan.status IN ('C','D') via account->loan join; predicted drops the loan table/join entirely and instead applies an invented value 'running' to the unrelated account.frequency column.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM account WHERE statement_frequency = 'running' AND district_id = 1;
```

### Q145 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters trans.operation='VYBER KARTOU'; predicted instead filters trans.type='credit_card', a different real column with a different value domain and a fabricated literal not matching either column's real codes.

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.account_id 
FROM trans AS T1 
JOIN account AS T2 ON T1.account_id = T2.account_id 
WHERE T1.type = 'credit_card' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE strftime('%Y', date) = '1998') AND strftime('%Y', T1.date) = '1998';
```

### Q149 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Card connects to account only via disp (card.disp_id->disp.disp_id->disp.account_id); predicted joins card directly to account on a nonexistent card.account_id column, skipping the disp bridge entirely.

**Gold SQL:**

```sql
SELECT DISTINCT T3.`type`
FROM `district` AS T1
JOIN `account`  AS T2 ON T1.`district_id` = T2.`district_id`
JOIN `disp`     AS T3 ON T2.`account_id`  = T3.`account_id`
WHERE T3.`type` <> 'OWNER'
  AND T1.`A11`  > 8000
  AND T1.`A11` <= 9000;
```

**Predicted SQL:**

```sql
SELECT DISTINCT c.type, AVG(d.average_salary) AS avg_income
FROM card c
JOIN account a ON c.account_id = a.account_id
JOIN district d ON a.district_id = d.district_id
WHERE c.disposition_id NOT IN (SELECT disposition_id FROM disp WHERE type LIKE '%loan%')
AND d.average_salary BETWEEN 8000 AND 9000
GROUP BY c.type;
```

### Q152 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold's A15>4000 threshold (number_crimes_1995); predicted instead filters d.number_inhabitants>4000, a different real column entirely; also flattens gold's 'district_id IN (SELECT DISTINCT ...)' subquery into a direct join with account, which can double-count districts.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.number_crimes_1995) 
FROM district d 
JOIN account a ON d.district_id = a.district_id 
WHERE d.number_inhabitants > 4000 AND strftime('%Y', a.date) >= '1997';
```

### Q159 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Gold identifies the client via client->disp->account->trans; predicted has no client/disp join at all, referencing a nonexistent trans.client_id column directly, and uses trans.type/a fabricated transaction_type_code filter instead of trans.operation='VYBER'.

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT t.transaction_id, t.date, t.amount 
FROM trans t 
JOIN account a ON t.account_id = a.account_id 
WHERE t.client_id = 3356 AND t.type = 'withdrawal' AND t.transaction_type_code = 'cash';
```

### Q168 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** gender belongs to client (T2, already joined); predicted references T3.gender (disp, which has no gender column) instead -- an alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.client_id)
FROM district AS T1
JOIN client AS T2 ON T1.district_id = T2.district_id
JOIN disp AS T3 ON T2.client_id = T3.client_id
WHERE T1.average_salary > 10000;
```

### Q169 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** loan.amount/loan.date (loan is joined as T4) are mistakenly referenced via T3 (account) instead -- an alias mix-up on an already-joined table; predicted also drops the disp.type='OWNER' filter gold requires.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN strftime('%Y', T3.date) = '1997' THEN T3.amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y', T3.date) = '1996' THEN T3.amount ELSE 0 END)) / SUM(CASE WHEN strftime('%Y', T3.date) = '1996' THEN T3.amount ELSE 0 END) AS growth_rate
FROM 
    client AS T1
JOIN 
    disp AS T2 ON T1.client_id = T2.client_id
JOIN 
    account AS T3 ON T2.account_id = T3.account_id
JOIN 
    loan AS T4 ON T3.account_id = T4.account_id
WHERE 
    T1.gender = 'M';
```

### Q173 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold aggregates over the `order` table (standing orders, GROUP BY account_id,k_symbol, SUM(amount)=3539); predicted queries `trans` (transaction log) directly instead -- a different, wrong table -- and doesn't reproduce the GROUP BY/SUM subquery.

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT T1.statement_frequency, SUM(T2.amount) AS total_debit_amount
FROM account AS T1
JOIN trans AS T2 ON T1.account_id = T2.account_id
WHERE T1.account_id = 3 AND T2.transaction_type_code = 'debit' AND T2.amount = 3539;
```

### Q186 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** account and client aren't directly linked; the real path is account<-disp->client; predicted joins account directly to client on a nonexistent account.client_id column, skipping the disp bridge.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.statement_frequency = 'weekly' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM account AS T1 JOIN client AS T2 ON T1.client_id = T2.client_id WHERE T2.gender = 'male';
```

### Q189 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** account has no client_id column (needs disp bridge: account<-disp->client); predicted joins account directly to client on a nonexistent column, and also references an undefined alias T3.average_salary.

**Gold SQL:**

```sql
SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id  WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.account_id 
FROM account AS T1 
JOIN client AS T2 ON T1.client_id = T2.client_id 
WHERE T2.gender = 'F' 
ORDER BY T2.birth_date ASC, T3.average_salary ASC 
LIMIT 1;
```

### Q192 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops account.frequency='POPLATEK PO OBRATU' entirely; status condition is changed to a single invented 'running' value instead of IN('C','D'); a fabricated EXISTS subquery on trans (t.date<l.date) with no basis in gold is also added.

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(l.amount) AS average_loan_amount
FROM loan l
JOIN account a ON l.account_id = a.account_id
WHERE l.status = 'running'
AND EXISTS (
    SELECT 1
    FROM trans t
    WHERE t.account_id = a.account_id
    AND t.date < l.date
);
```

### Q194 (moderate, retrieval) — **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** card only has disp_id (not account_id); the correct join is card.disp_id=disp.disp_id; predicted instead joins ca.account_id=d.account_id, a nonexistent column, and fabricates additional conditions (type='credit_card' instead of 'gold', a disposition_id subquery, an unrelated EXISTS loan check).

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, julianday('now') - julianday(c.birth_date) AS age
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN card ca ON d.account_id = ca.account_id
WHERE ca.type = 'credit_card' AND ca.disposition_id IN (SELECT disposition_id FROM disp WHERE type = 'high_level')
AND EXISTS (SELECT 1 FROM loan l WHERE l.account_id = d.account_id);
```

---

## formula_1 (51 failures)

### Q846 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold ranks by qualifying.q1 time; predicted queries results (a different, wrong table) and joins status via a fabricated 'eliminated' status filter with no correspondence to gold's ORDER BY q1 DESC LIMIT 5 logic.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT T1.driver_ref_name 
FROM drivers AS T1 
JOIN results AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.race_id = 20 AND T2.status_id IN (SELECT status_id FROM status WHERE status LIKE '%eliminated%');
```

### Q850 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The join/filter logic matches gold exactly (races.name filtered by circuits.country='Germany'); predicted's missing DISTINCT can return duplicate race names for a circuit hosting the Grand Prix multiple years.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT T1.name FROM races AS T1 JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.country = 'Germany'
```

### Q854 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The join/filter logic matches gold; predicted's missing DISTINCT can return duplicate lat/lng rows if the same Grand Prix was held at the same circuit across multiple years.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.latitude, T1.longitude FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name LIKE '%Australian Grand Prix%'
```

### Q857 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The join/filter logic matches gold exactly; predicted's missing DISTINCT can return duplicate lat/lng rows across multiple years of the same Grand Prix.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.latitude, T1.longitude FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name = 'Abu Dhabi Grand Prix'
```

### Q859 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects qualifying.q1 (the Q1 session time); predicted selects qualifying.position instead -- a different real column entirely.

**Gold SQL:**

```sql
SELECT T1.q1 FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 354 AND T2.forename = 'Bruno' AND T2.surname = 'Senna'
```

**Predicted SQL:**

```sql
SELECT T1.position 
FROM qualifying AS T1 
JOIN drivers AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.first_name = 'Bruno' AND T2.last_name = 'Senna' AND T1.race_id = 354;
```

### Q861 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold matches q3 LIKE '1:54%' (a prefix pattern); predicted uses an exact-match qualifying_3_time='00:01:54' (wrong format) and adds a fabricated position=1 condition with no basis in gold.

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT T1.number 
FROM drivers AS T1 
JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.race_id = 903 AND T2.position = 1 AND T2.qualifying_3_time = '00:01:54';
```

### Q862 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold identifies non-finishers via results.time IS NULL; predicted instead checks position=0 -- a wrong/invented transformation of 'did not finish'.

**Gold SQL:**

```sql
SELECT COUNT(T3.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T1.year = 2007 AND T1.name = 'Bahrain Grand Prix' AND T2.time IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM results WHERE race_id = (SELECT race_id FROM races WHERE year = 2007 AND name = 'Bahrain Grand Prix') AND position = 0;
```

### Q865 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops both the results.time IS NOT NULL (finishers only) and drivers.dob IS NOT NULL filters gold requires.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name 
FROM drivers AS T1 
JOIN results AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.race_id = 592 
ORDER BY T1.date_of_birth ASC 
LIMIT 1;
```

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold matches time LIKE '1:27%' (prefix pattern); predicted uses an exact match against '00:01:27' (wrong format), which won't match real recorded lap times with fractional seconds.

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.url 
FROM drivers d 
JOIN laptimes lt ON d.driver_id = lt.driver_id 
WHERE lt.race_id = 161 AND lt.time = '00:01:27';
```

### Q868 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The join/filter logic matches gold; predicted's missing DISTINCT can return duplicate lat/lng rows across multiple years of the same Grand Prix; an extra 'location' column is also added.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.location, T1.latitude, T1.longitude FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold uses constructorResults.points (per-race points for that specific race); predicted substitutes constructorStandings.points (cumulative championship standings) -- a different, real, but wrong table.

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.url 
FROM constructors AS T1 
JOIN constructorStandings AS T2 ON T1.constructor_id = T2.constructor_id 
WHERE T2.race_id = 9 
ORDER BY T2.points DESC 
LIMIT 1;
```

### Q872 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold matches q3 LIKE '1:33%' (prefix pattern); predicted uses an exact match against '00:01:33' (wrong format).

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT T1.driver_code 
FROM drivers AS T1 
JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.race_id = 45 AND T2.qualifying_3_time = '00:01:33';
```

### Q877 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops the results.time IS NOT NULL filter (finishers only) that gold requires, potentially including non-finishers in the youngest-driver ranking.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.driver_id, d.first_name, d.last_name, d.date_of_birth
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
WHERE r.race_id = 872
ORDER BY d.date_of_birth DESC
LIMIT 1;
```

### Q879 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold explicitly casts CAST(fastestLapSpeed AS REAL) before sorting; predicted sorts the raw (likely text-stored) column directly without casting, which sorts lexicographically rather than numerically.

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.nationality 
FROM drivers AS T1 
JOIN results AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.fastest_lap_speed IS NOT NULL 
ORDER BY T2.fastest_lap_speed DESC 
LIMIT 1;
```

### Q880 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold pivots on specific raceId values (853, 854); predicted instead filters T1.number=853 -- confusing results.number (the driver's car number) with raceId -- and restructures into an unrelated self-join on consecutive race IDs.

**Gold SQL:**

```sql
SELECT ((MAX(CASE WHEN r.`raceId` = 853 THEN CAST(r.`fastestLapSpeed` AS REAL) END) -
         MAX(CASE WHEN r.`raceId` = 854 THEN CAST(r.`fastestLapSpeed` AS REAL) END)) * 100.0) /
       MAX(CASE WHEN r.`raceId` = 854 THEN CAST(r.`fastestLapSpeed` AS REAL) END) AS percent_faster
FROM `drivers` d
JOIN `results`  r ON d.`driverId` = r.`driverId`
WHERE d.`forename` = 'Paul'
  AND d.`surname`  = 'di Resta';
```

**Predicted SQL:**

```sql
SELECT 
    (T1.fastest_lap_speed - T2.fastest_lap_speed) * 100 / T2.fastest_lap_speed AS percentage_faster
FROM 
    results AS T1
JOIN 
    results AS T2 ON T1.driver_id = T2.driver_id AND T1.race_id < T2.race_id
WHERE 
    T1.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Paul' AND last_name = 'di Resta') 
    AND T1.number = 853
ORDER BY 
    T1.race_id DESC
LIMIT 1;
```

### Q881 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races.date is needed to filter '1983-07-16'; predicted never joins races at all, referencing r.date on results (which has no date column) instead, and restructures the whole computation (GROUP BY driver, wrong scope).

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT 
    d.driver_id, 
    d.first_name, 
    d.last_name, 
    COUNT(r.race_id) AS total_races, 
    SUM(CASE WHEN r.date = '1983-07-16' THEN 1 ELSE 0 END) AS completed_races, 
    (SUM(CASE WHEN r.date = '1983-07-16' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.race_id)) AS completion_rate
FROM 
    drivers d
JOIN 
    results r ON d.driver_id = r.driver_id
WHERE 
    r.date BETWEEN '1983-01-01' AND '1983-12-31'
GROUP BY 
    d.driver_id, 
    d.first_name, 
    d.last_name;
```

### Q884 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses two subqueries to find the year AND month of the earliest race, then returns ALL races matching that year+month; predicted collapses this into a plain ORDER BY date ASC LIMIT 1, returning only a single race.

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.name FROM races AS T1 JOIN seasons AS T2 ON T1.year = T2.year ORDER BY T1.date ASC LIMIT 1
```

### Q894 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects lapTimes.milliseconds (the numeric value); predicted selects lapTimes.time (the text time string) instead -- a different real column.

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT l.time AS lap_time, d.first_name || ' ' || d.last_name AS driver, r.name AS race
FROM lapTimes l
JOIN drivers d ON l.driver_id = d.driver_id
JOIN races r ON l.race_id = r.race_id
ORDER BY l.milliseconds ASC
LIMIT 1;
```

### Q896 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Gold uses driverStandings.position (cumulative championship position); predicted substitutes results.position (single-race finishing position) instead -- a different, real but wrong table; it also never joins races, so year doesn't exist on results.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN r.position != 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(r.race_id)
FROM results r
JOIN drivers d ON r.driver_id = d.driver_id
WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton' AND r.year >= 2010;
```

### Q897 (moderate, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold ranks drivers by COUNT(T2.wins) DESC (most seasons/races with at least one win); predicted instead ranks by MAX(points) DESC -- a different, wrong sort criterion that could select an entirely different driver.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.nationality, MAX(ds.points) AS max_points
FROM drivers d
JOIN driverStandings ds ON d.driver_id = ds.driver_id
WHERE ds.wins > 0
GROUP BY d.driver_id
ORDER BY max_points DESC
LIMIT 1;
```

### Q898 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold's SELECT list includes a computed age expression alongside forename/surname; predicted drops the age column entirely -- a SELECT-list shape mismatch.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name FROM drivers WHERE nationality = 'Japanese' ORDER BY date_of_birth DESC LIMIT 1
```

### Q901 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters by calendar month (STRFTIME('%m', date)='09', i.e. September); predicted substitutes round BETWEEN 9 AND 11 (the race's sequence number within the season) -- a completely different, unrelated column/concept.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name, T1.name, T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Predicted SQL:**

```sql
SELECT r.name AS race_name, c.name AS circuit_name, c.location 
FROM races r 
JOIN circuits c ON r.circuit_id = c.circuit_id 
WHERE r.year = 2005 AND r.round BETWEEN 9 AND 11;
```

### Q902 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold uses driverStandings.position (championship standing); predicted substitutes results.position (single-race finishing position) instead -- a different, real but wrong table.

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT r.name 
FROM races r 
JOIN results res ON r.race_id = res.race_id 
JOIN drivers d ON res.driver_id = d.driver_id 
WHERE d.first_name = 'Alex' AND d.last_name = 'Yoong' AND res.position < 20;
```

### Q904 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references r.season_id to join seasons, but races has no season_id column -- it stores year directly; predicted also substitutes results (fastestLapTime, race-level) for lapTimes (per-lap milliseconds), the wrong table for finding the single fastest individual lap.

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name AS race, s.year AS year
FROM results res
JOIN races r ON res.race_id = r.race_id
JOIN seasons s ON r.season_id = s.year
JOIN drivers d ON res.driver_id = d.driver_id
WHERE d.first_name = 'Michael' AND d.last_name = 'Schumacher'
ORDER BY res.fastest_lap_time ASC
LIMIT 1;
```

### Q909 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold scopes to races named 'European Grand Prix' (races.name); predicted instead filters circuits.country='Europe' -- a different, wrong column entirely, changing the scope from a specific race to all races in generically-European countries.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.country = 'Germany' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T1.country = 'Europe'
```

### Q910 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Silverstone Circuit' is truncated to just 'Silverstone' in predicted.

**Gold SQL:**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Silverstone Circuit'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Silverstone'
```

### Q915 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects drivers.nationality directly (single table, no join needed); predicted selects circuits.country instead (via unnecessary joins through races/results) -- a completely different, wrong column from an unrelated table.

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.country FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id JOIN results AS T3 ON T2.race_id = T3.race_id JOIN drivers AS T4 ON T3.driver_id = T4.driver_id ORDER BY T4.date_of_birth ASC LIMIT 1
```

### Q930 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters results.rank=0 to scope races; predicted drops this condition entirely, replacing it with an unbounded 'ORDER BY position ASC' with no LIMIT -- returning every race the driver ever raced in.

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT r.name AS race_name
FROM races r
JOIN results res ON r.race_id = res.race_id
JOIN drivers d ON res.driver_id = d.driver_id
WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton'
ORDER BY res.position ASC;
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Predicted's race name literal is garbled/corrupted ('AustChineseralian Grand Prix', an apparent text-generation artifact), which won't match the real value 'Chinese Grand Prix'.

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT T1.time 
FROM results AS T1 
JOIN races AS T2 ON T1.race_id = T2.race_id 
WHERE T1.position = 2 AND T2.year = 2008 AND T2.name = 'AustChineseralian Grand Prix';
```

### Q940 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold identifies finishers via results.time IS NOT NULL; predicted substitutes position>0 instead -- a different, wrong transformation not equivalent to checking time IS NOT NULL.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT d.driver_id) 
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
JOIN races ra ON r.race_id = ra.race_id
WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position > 0;
```

### Q944 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses 3 CTEs to compute the champion's time (positionOrder=1) vs the last-place driver's time (MAX positionOrder) and the percentage difference; predicted flattens this into a single MAX/MIN(milliseconds) aggregate, dropping the explicit positionOrder-based selection and the 'time IS NOT NULL' filter.

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    ((MAX(T1.milliseconds) - MIN(T1.milliseconds)) / MAX(T1.milliseconds)) * 100 AS percentage_faster
FROM 
    results AS T1
JOIN 
    races AS T2 ON T1.race_id = T2.race_id
WHERE 
    T2.year = 1988 AND T2.name = 'Australian Grand Prix';
```

### Q951 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold uses constructorResults (per-race results) with points=0, GROUP BY constructorId HAVING COUNT=2; predicted substitutes constructorStandings (cumulative standings) instead -- a different, wrong table -- and drops the GROUP BY/HAVING COUNT=2 condition entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM constructors 
JOIN constructorStandings ON constructors.constructor_id = constructorStandings.constructor_id 
WHERE constructors.nationality = 'Japanese' AND constructorStandings.points = 0;
```

### Q954 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** nationality belongs to drivers (already joined as T3); predicted's WHERE clause references T4.nationality instead (T4=seasons, an unneeded extra join with no nationality column) -- an alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T4.nationality = 'Japanese' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS race_completion_percentage
FROM 
    races AS T1
JOIN 
    results AS T2 ON T1.race_id = T2.race_id
JOIN 
    drivers AS T3 ON T2.driver_id = T3.driver_id
JOIN 
    seasons AS T4 ON T1.year = T4.year
WHERE 
    T4.year BETWEEN 2007 AND 2009;
```

### Q955 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Gold joins results directly to races for year/position=1 filtering; predicted substitutes an unrelated join chain through seasons/driverStandings/laptimes instead, referencing T2.year on driverStandings (which has no year column).

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT T1.year, AVG(T4.milliseconds / 1000) AS avg_champion_time FROM seasons AS T1 INNER JOIN driverstandings AS T2 ON T1.year = T2.year AND T2.position = 1 INNER JOIN results AS T3 ON T2.driverid = T3.driverid INNER JOIN laptimes AS T4 ON T3.raceid = T4.raceid AND T3.driverid = T4.driverid WHERE T1.year < 1975 GROUP BY T1.year
```

### Q959 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races.year is needed to filter year=2009; predicted never joins races at all, referencing T1.year directly on results (which has no year column) -- it substitutes an unrelated driverstandings join and position=1 filter instead of gold's time-format LIKE pattern check.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T1.fastest_lap_number FROM results AS T1 JOIN driverstandings AS T2 ON T1.driverid = T2.driverid WHERE T2.position = 1 AND T1.year = 2009
```

### Q962 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold requires laps > 50; predicted uses laps = 50 (exact equality) instead -- the comparison operator itself changed, not just the threshold value.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.date_of_birth < '1985-01-01' AND T1.laps = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM results AS T1 JOIN drivers AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id IN (SELECT race_id FROM races WHERE YEAR BETWEEN 2000 AND 2005)
```

### Q963 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold parses the MM:SS.mmm time string into total seconds via SUBSTR/CAST arithmetic and compares numerically (<120 seconds); predicted instead does a raw string comparison time < '02:00.00', which compares lexicographically rather than temporally.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT r.driver_id)
FROM results r
JOIN laptimes lt ON r.race_id = lt.race_id AND r.driver_id = lt.driver_id
JOIN drivers d ON r.driver_id = d.driver_id
WHERE d.nationality = 'French' AND lt.time < '02:00.00';
```

### Q967 (simple, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a derived table to find the 3 youngest drivers OVERALL via ORDER BY JULIANDAY(dob) DESC LIMIT 3, then counts how many are Dutch; predicted instead filters nationality FIRST (using the wrong value 'Netherlands' instead of 'Dutch') then takes the top 3 by dob -- a fundamentally different computation order.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM drivers WHERE nationality = 'Netherlands' AND date_of_birth IS NOT NULL ORDER BY date_of_birth DESC LIMIT 3
```

### Q972 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold returns ALL 1971-born drivers with any recorded fastestLapTime (a plain existence filter, no ordering/limit); predicted adds an unwarranted ORDER BY fastest_lap_time ASC LIMIT 1, turning a set-returning query into a single-row query -- a fundamental shape change not present in gold.

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.driver_id, d.driver_code
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
WHERE d.date_of_birth LIKE '1971%'
ORDER BY r.fastest_lap_time ASC
LIMIT 1;
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses strict inequalities (raceId<100 AND raceId>50, excluding 50/100); predicted uses BETWEEN 50 AND 100 (inclusive) instead; it also assumes statusId=2 corresponds to a 'Disqualified' status via a subquery lookup rather than using the raw code, and swaps the SUM(IIF(time IS NOT NULL,...)) for a plain COUNT(*).

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM results WHERE race_id BETWEEN 50 AND 100 AND status_id = (SELECT status_id FROM status WHERE status = 'Disqualified');
```

### Q978 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The filter/columns match gold exactly (country='Austria', location/lat/lng); predicted's only difference is a missing DISTINCT.

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** year belongs to races (already joined as r); predicted's SELECT references q.year (qualifying, which has no year column) instead -- an alias mix-up on an already-joined table; it also replaces gold's oldest-driver-subquery/date-ordering approach with an unrelated position=1 filter and grid_position ordering.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MIN(q.year) AS first_qualifying_year,
    r.name AS race_name,
    r.date AS race_date,
    r.time AS race_time
FROM 
    qualifying q
JOIN 
    results res ON q.driver_id = res.driver_id AND q.race_id = res.race_id
JOIN 
    races r ON q.race_id = r.race_id
WHERE 
    q.position = 1
ORDER BY 
    res.grid_position ASC
LIMIT 1;
```

### Q988 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold joins pitStops directly to drivers (pitStops already has driverId); predicted adds an unnecessary extra join through results, which could drop pit stops for driver/race combinations without a corresponding results row.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, AVG(ps.duration) AS avg_pit_stop_duration
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
JOIN pitStops ps ON r.race_id = ps.race_id AND d.driver_id = ps.driver_id
WHERE d.nationality = 'German' AND d.date_of_birth BETWEEN '1980-01-01' AND '1985-12-31'
GROUP BY d.driver_id
ORDER BY avg_pit_stop_duration ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold filters directly on results.time LIKE '_:%:__.___' (a valid-format check); predicted instead joins driverStandings and filters position=1 (championship leader) -- an entirely different, wrong table/condition.

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T1.time 
FROM results AS T1 
JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id 
JOIN races AS T3 ON T1.race_id = T3.race_id 
WHERE T3.name = 'Canadian Grand Prix' AND T3.year = 2008 AND T2.position = 1;
```

### Q990 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold filters directly on results.time LIKE pattern (valid finish format); predicted substitutes constructorStandings and filters position=1 instead -- a different, wrong table/condition.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T4.constructor_ref_name, T4.url 
FROM races AS T1 
JOIN constructorStandings AS T2 ON T1.race_id = T2.race_id 
JOIN constructors AS T4 ON T2.constructor_id = T4.constructor_id 
WHERE T1.year = 2009 AND T1.name = 'Singapore Grand Prix' AND T2.position = 1;
```

### Q994 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Predicted's SELECT references cr.points, but no alias 'cr' was ever introduced in the FROM/JOIN clause (only c, cs, r exist) -- likely a copy-paste artifact; it also mistakenly treats 'Monaco Grand Prix' (a race name) as if it were a circuit name.

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.constructor_id, c.name, c.nationality, SUM(cr.points) AS total_points
FROM constructors c
JOIN constructorStandings cs ON c.constructor_id = cs.constructor_id
JOIN races r ON cs.race_id = r.race_id
WHERE r.circuit_id IN (SELECT circuit_id FROM circuits WHERE name = 'Monaco Grand Prix')
AND r.year BETWEEN 1980 AND 2010
GROUP BY c.constructor_id, c.name, c.nationality
ORDER BY total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold finds the driver with the fastest Q3 time via a parsed time-to-seconds ORDER BY; predicted drops this entirely, replacing it with fabricated conditions (qualifying.position=1, races.round=3) with no basis in gold, and truncates the circuit name.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM races AS T1 JOIN qualifying AS T2 ON T1.race_id = T2.race_id JOIN circuits AS T3 ON T1.circuit_id = T3.circuit_id JOIN drivers AS T4 ON T2.driver_id = T4.driver_id WHERE T1.year = 2008 AND T3.name = 'Marina Bay Street' AND T2.position = 1 AND T1.round = 3
```

### Q1002 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold has no WHERE filter at all (ranks across all entries by dob DESC LIMIT 1); predicted adds a fabricated WHERE r.year=(SELECT MIN(year) FROM races) condition with no basis in gold, restricting to only races from the earliest season.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.nationality, r.name AS race_name
FROM drivers d
JOIN results res ON d.driver_id = res.driver_id
JOIN races r ON res.race_id = r.race_id
WHERE r.year = (SELECT MIN(year) FROM races)
ORDER BY d.date_of_birth DESC
LIMIT 1;
```

### Q1003 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by driverId and picks the driver with the most statusId=3 occurrences (ORDER BY COUNT DESC LIMIT 1); predicted drops the GROUP BY entirely, just returning a flat COUNT(*) -- a completely different query shape; it also mistranslates statusId=3 into a LIKE '%accident%' text match.

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS accident_count
FROM results r
JOIN status s ON r.status_id = s.status_id
WHERE r.race_id IN (
    SELECT race_id
    FROM races
    WHERE name = 'Canadian Grand Prix'
) AND s.status LIKE '%accident%';
```

### Q1011 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a derived table to find each driver's personal-best lap (MIN(milliseconds) GROUP BY driverId), then takes the top 20 drivers by that; predicted skips the aggregation entirely, taking the top 20 individual lap records directly.

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM drivers AS T1 JOIN laptimes AS T2 ON T1.driver_id = T2.driver_id ORDER BY T2.milliseconds ASC LIMIT 20
```

### Q1014 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** circuit_id isn't a column on lapTimes at all -- it must be reached via races; predicted joins lapTimes directly to circuits on a nonexistent l.circuit_id, skipping races entirely, and uses MAX(milliseconds) instead of gold's MIN/fastest-time logic.

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(l.milliseconds) AS max_milliseconds, c.name AS circuit_name
FROM lapTimes l
JOIN circuits c ON l.circuit_id = c.circuit_id
WHERE c.country = 'Italy'
GROUP BY l.driver_id
ORDER BY max_milliseconds DESC
LIMIT 1;
```

---

## student_club (24 failures)

### Q1322 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Predicted's outer COUNT(event_id) is ambiguous after joining event and attendance (attendance.link_to_event is correctly S3-renamed to event_id, colliding with event.event_id) -- an unqualified-column ambiguity error, plus the subquery logic itself (count events per member) doesn't match gold's intent (events per meeting).

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(event_id) 
FROM event 
JOIN attendance ON event.event_id = attendance.event_id 
WHERE event.type = 'meeting' AND attendance.member_id IN (SELECT member_id FROM attendance GROUP BY member_id HAVING COUNT(event_id) > 10);
```

### Q1334 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted adds an extra unwarranted filter T1.position='Student_Club' not present in gold at all, incorrectly narrowing the result -- a condition wholesale added.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 JOIN zip_code AS T2 ON T1.zip_code = T2.zip_code WHERE T2.state = 'Illinois' AND T1.position = 'Student_Club'
```

### Q1338 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Expense has no direct link to event; the real path is expense.link_to_budget -> budget.budget_id -> budget.link_to_event -> event.event_id. Predicted skips budget and joins expense directly to event on a nonexistent event_id column.

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT e.is_approved 
FROM expense e 
JOIN event ev ON e.event_id = ev.event_id 
WHERE ev.event_name = 'October Meeting' AND ev.event_date = '2019-10-08';
```

### Q1339 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters by month only (SUBSTR(expense_date,6,2) IN ('09','10')), regardless of year; predicted hardcodes a specific year (BETWEEN '2023-09-01' AND '2023-10-31'), a wrong restructuring of the month-only filter.

**Gold SQL:**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL:**

```sql
SELECT AVG(e.cost) AS average_cost
FROM expense e
JOIN member m ON e.member_id = m.member_id
WHERE m.first_name = 'Elijah' AND m.last_name = 'Allen'
  AND e.expense_date BETWEEN '2023-09-01' AND '2023-10-31';
```

### Q1340 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Gold sources the year from event.event_date reached via budget->event; predicted queries budget directly for a nonexistent expense_date column and an invented event_status='Student_Club' value, missing the event/expense joins entirely.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT SUM(amount_spent) FROM budget WHERE event_status = 'Student_Club' AND strftime('%Y', expense_date) = '2019') - 
    (SELECT SUM(amount_spent) FROM budget WHERE event_status = 'Student_Club' AND strftime('%Y', expense_date) = '2020')
```

### Q1344 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's 'notes' come from the income table (Fundraising income received 2019-09-14); predicted substitutes the event table (type='fundraising', event_date) entirely -- a different, wrong table.

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT T1.notes FROM event AS T1 WHERE T1.event_date = '2019-09-14' AND T1.type = 'fundraising';
```

### Q1359 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold computes a ratio of conditional SUM(amount) for two specific events; predicted computes an unrelated COUNT(*) with a subquery comparison of individual amount_spent values -- a different aggregation approach that doesn't correspond to gold's ratio computation.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM budget 
JOIN event ON budget.event_id = event.event_id 
WHERE event_name = 'Yearly Kickoff' AND category = 'Advertisement' AND amount_spent > (SELECT amount_spent FROM budget JOIN event ON budget.event_id = event.event_id WHERE event_name = 'October Meeting' AND category = 'Advertisement');
```

### Q1362 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** County='Orange County' is truncated to just 'Orange' in predicted -- an incomplete/wrong literal.

**Gold SQL:**

```sql
SELECT COUNT(distinct city) FROM zip_code WHERE county = 'Orange County' AND state = 'Virginia'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT city) FROM zip_code WHERE county = 'Orange' AND state = 'Virginia';
```

### Q1376 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a HAVING clause with a nested MAX(ratio) subquery (tie-preserving) to select events tied for the top spend/budget ratio, aggregated via SUM per event; predicted collapses this into a flat, non-aggregated ORDER BY ratio DESC LIMIT 1 with no GROUP BY, HAVING, or subquery.

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT e.event_name, (b.amount_spent / b.amount) AS spend_to_budget_ratio
FROM event e
JOIN budget b ON e.event_id = b.event_id
WHERE e.status = 'closed'
ORDER BY spend_to_budget_ratio DESC
LIMIT 1;
```

### Q1380 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold sums budget.spent WHERE category='Food'; predicted substitutes the expense table (SUM(cost) WHERE expense_description LIKE '%food%') entirely -- a different, wrong table and matching approach.

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) AS total_amount_spent_for_food
FROM expense
WHERE expense_description LIKE '%food%';
```

### Q1387 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Predicted skips both the expense bridge (member->expense->budget) and the event join (budget->event) entirely, directly joining member to budget on a nonexistent member_id column and filtering on a nonexistent event_name column.

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 JOIN budget AS T2 ON T1.member_id = T2.member_id WHERE T2.event_name = 'Yearly Kickoff' AND T1.position = 'Student';
```

### Q1389 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Expense has no direct link to event; predicted joins event directly to expense on a nonexistent event_id column, skipping the required budget bridge table.

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name FROM event e JOIN expense ex ON e.event_id = ex.event_id ORDER BY ex.cost ASC, e.event_name ASC LIMIT 1
```

### Q1390 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Expense has no direct link to event; predicted joins expense directly to event on a nonexistent event_id column, skipping the required budget bridge table.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN e.event_name = 'Yearly Kickoff' THEN e.cost ELSE 0 END) / SUM(e.cost)) * 100 AS percentage
FROM 
    expense e
JOIN 
    event ev ON e.event_id = ev.event_id;
```

### Q1392 (simple, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold wants the alphabetically-last income source in a date range via a plain ORDER BY source DESC LIMIT 1 (no aggregation); predicted adds an unwanted GROUP BY income_source with SUM(amount), fundamentally changing what's being sorted.

**Gold SQL:**

```sql
SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT income_source, SUM(amount) AS total_amount
FROM income
WHERE date_received BETWEEN '2019-09-01' AND '2019-09-30'
GROUP BY income_source
ORDER BY total_amount DESC
LIMIT 1;
```

### Q1401 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Expense has no direct link to event; predicted joins expense directly to event on a nonexistent event_id column, skipping the required budget bridge table.

**Gold SQL:**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL:**

```sql
SELECT T2.cost FROM event AS T1 JOIN expense AS T2 ON T1.event_id = T2.event_id WHERE T1.event_name = 'September Speaker' AND T2.expense_description LIKE '%posters%'
```

### Q1403 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold uses only event+budget, sorting directly by budget.remaining (which already encodes spent-vs-budgeted); predicted adds an unnecessary join to expense and recomputes an ad hoc SUM(cost)-SUM(spent) metric instead, changing both the join grain and the sort direction, and drops the remaining<0 filter.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name
FROM event e
JOIN budget b ON e.event_id = b.event_id
JOIN expense ex ON b.budget_id = ex.budget_id
WHERE e.status = 'closed'
GROUP BY e.event_id
ORDER BY SUM(ex.cost) - SUM(b.amount_spent) DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** expense.approved (renamed is_approved) is stored as text 'true'/'false'; predicted compares is_approved = 1 (numeric) instead of = 'true', which won't match the text value.

**Gold SQL:**

```sql
SELECT
    T2.`category`,
    SUM(T3.`cost`) AS total_approved_value
FROM `event`  AS T1
JOIN `budget` AS T2 ON T1.`event_id`  = T2.`link_to_event`
JOIN `expense` AS T3 ON T2.`budget_id` = T3.`link_to_budget`
WHERE T1.`event_name` = 'October Meeting'
  AND T3.`approved` = 'true'  
GROUP BY T2.`category`;
```

**Predicted SQL:**

```sql
SELECT b.category, SUM(e.cost) AS total_value
FROM expense e
JOIN budget b ON e.budget_id = b.budget_id
JOIN event ev ON b.event_id = ev.event_id
WHERE ev.event_name = 'October Meeting' AND e.is_approved = 1;
```

### Q1410 (simple, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Predicted concatenates first_name and last_name into a single 'full_name' string column instead of returning them as two separate columns like gold -- a SELECT-list shape mismatch.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'
```

**Predicted SQL:**

```sql
SELECT m.first_name || ' ' || m.last_name AS full_name, SUM(e.cost) AS total_cost
FROM member m
JOIN expense e ON m.member_id = e.member_id
WHERE m.member_id = 'rec4BLdZHS2Blfp4v'
GROUP BY m.first_name, m.last_name;
```

### Q1422 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold wants event.type (a real column describing e.g. Meeting/Game); predicted returns budget.category (a different, unrelated real column, spending category) via an added unneeded join.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT T1.category FROM budget AS T1 JOIN event AS T2 ON T1.event_id = T2.event_id WHERE T2.location = 'MU 215'
```

### Q1427 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='Guest Speaker' is lowercased to 'guest speaker' in predicted, a case mismatch on an otherwise-correct predicate; DISTINCT is also dropped.

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT T3.category 
FROM event AS T1 
JOIN budget AS T3 ON T1.event_id = T3.event_id 
WHERE T1.location = 'MU 215' AND T1.type = 'guest speaker' AND T3.amount_spent = 0;
```

### Q1432 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops the T1.position='Member' filter entirely, replacing it with an unrelated/invented major_name='Student_Club' filter via a subquery on the major table -- 'Student_Club' isn't a valid major and has nothing to do with the intended position filter.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM member AS T1 
JOIN income AS T2 ON T1.member_id = T2.member_id 
WHERE T1.t_shirt_size = 'Medium' AND T1.major_id IN (SELECT major_id FROM major WHERE major_name = 'Student_Club');
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='Game' and status='Closed' are lowercased to 'game'/'closed' in predicted, a case mismatch on otherwise-correct predicates.

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT event_name 
FROM event 
WHERE type = 'game' AND status = 'closed' AND event_date BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1457 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold's budget join is vestigial (doesn't change the AVG(cost) computation); the real cause is predicted's missing DISTINCT, which can return duplicate member rows if a member has multiple qualifying expenses.

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, m.phone
FROM member m
JOIN expense e ON m.member_id = e.member_id
WHERE e.cost > (SELECT AVG(cost) FROM expense);
```

### Q1460 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters on the single exact description string 'Water, Veggie tray, supplies'; predicted splits it into an IN-list of three separate lowercase substrings ('water','veggie tray','supplies') -- a wrong restructuring of the literal -- and aggregates with SUM/GROUP BY instead of returning the raw per-row cost.

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, SUM(e.cost) AS total_cost
FROM member m
JOIN expense e ON m.member_id = e.member_id
WHERE e.expense_description IN ('water', 'veggie tray', 'supplies')
GROUP BY m.member_id;
```

---

## superhero (28 failures)

### Q723 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='Blue' is lowercased to 'blue' in predicted.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN hero_power ON superhero.id = hero_power.hero_id 
JOIN superpower ON hero_power.power_id = superpower.id 
WHERE superhero.eye_colour_id IN (SELECT id FROM colour WHERE colour = 'blue') 
AND superpower.power_name = 'Agility';
```

### Q724 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='Blue'/'Blond' are lowercased to 'blue'/'blond' in predicted.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name FROM superhero s JOIN colour e ON s.eye_colour_id = e.id JOIN colour h ON s.hair_colour_id = h.id WHERE e.colour = 'blue' AND h.colour = 'blond'
```

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops the height_cm IS NOT NULL AND != 0 filters gold requires, letting invalid heights into the ordered result.

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT s.superhero_name, s.height_cm 
FROM superhero s 
JOIN publisher p ON s.publisher_id = p.id 
WHERE p.publisher_name = 'Marvel Comics' 
ORDER BY s.height_cm DESC;
```

### Q728 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold includes a RANK() OVER (ORDER BY COUNT DESC) window-function column (PopularityRank); predicted has no window function at all, just colour/count with a plain ORDER BY.

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.colour, COUNT(*) AS count
FROM superhero s
JOIN colour c ON s.eye_colour_id = c.id
JOIN publisher p ON s.publisher_id = p.id
WHERE p.publisher_name = 'Marvel Comics'
GROUP BY c.colour
ORDER BY count DESC;
```

### Q732 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references s.speed as if it were a direct column; superhero has no 'speed' column anywhere -- speed is only represented via the generic hero_attribute/attribute EAV pattern (attribute_name='Speed'), which is genuinely absent as a physical column.

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id INNER JOIN attribute AS T4 ON T3.attribute_id = T4.id WHERE T4.attribute_name = 'Speed' ORDER BY T3.attribute_value LIMIT 1
```

**Predicted SQL:**

```sql
SELECT p.publisher_name
FROM publisher p
JOIN superhero s ON p.id = s.publisher_id
WHERE s.speed IS NOT NULL
ORDER BY s.speed ASC
LIMIT 1;
```

### Q733 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs colour (eye_colour_id) filtered ='Gold'; predicted instead joins alignment and filters alignment.alignment='Gold' -- wrong table entirely (alignment holds Good/Bad/Neutral values, not colour names).

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN alignment ON superhero.alignment_id = alignment.id 
JOIN publisher ON superhero.publisher_id = publisher.id 
WHERE alignment.alignment = 'Gold' AND publisher.publisher_name = 'Marvel Comics';
```

### Q736 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a tie-preserving '= (SELECT MIN(attribute_value)...)' subquery pattern (returns ALL heroes tied for lowest intelligence); predicted collapses this into ORDER BY ASC LIMIT 1, the exact MIN-subquery/ORDER-BY-LIMIT1 swap pattern the taxonomy calls out.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 JOIN hero_attribute AS T2 ON T1.id = T2.hero_id JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Intelligence' ORDER BY T2.attribute_value ASC LIMIT 1
```

### Q743 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** publisher_name belongs to publisher (already joined as T3); predicted references it via T2 (superhero) instead -- an alias mix-up on an already-joined table; alignment='Self-Interest' is also an invented value.

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T1.alignment = 'Self-Interest' THEN 1 ELSE 0 END) * 100 / COUNT(*)) AS percentage_self_interest,
    SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' AND T1.alignment = 'Self-Interest' THEN 1 ELSE 0 END) AS marvel_self_interest_count
FROM 
    alignment AS T1
JOIN 
    superhero AS T2 ON T1.id = T2.alignment_id
JOIN 
    publisher AS T3 ON T2.publisher_id = T3.id;
```

### Q744 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a derived table plus an outer CASE to determine which publisher has more heroes and the signed difference; predicted flattens this into two independent scalar subqueries with hardcoded, unverified publisher_id=1/2 instead of joining on publisher_name, omitting the CASE-based 'which publisher' output entirely.

**Gold SQL:**

```sql
SELECT CASE WHEN marvel_cnt > dc_cnt THEN 'Marvel Comics' ELSE 'DC Comics' END AS publisher_with_more_superheroes,
       marvel_cnt - dc_cnt AS difference
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
    (SELECT COUNT(*) FROM superhero WHERE publisher_id = 1) - 
    (SELECT COUNT(*) FROM superhero WHERE publisher_id = 2) AS difference;
```

### Q745 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** 'publisher_id' is a real column, but it lives on superhero (the FK side), not publisher itself (whose own PK is just 'id'); predicted references it directly on a single-table publisher query with no join at all.

**Gold SQL:**

```sql
SELECT id FROM publisher WHERE publisher_name = 'Star Trek'
```

**Predicted SQL:**

```sql
SELECT publisher_id FROM publisher WHERE publisher_name = 'Star Trek'
```

### Q750 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted's subquery references gender_name, which matches no real column anywhere -- the real column on gender is just 'gender'.

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender_name = 'Female')
```

### Q753 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold requires joining colour and filtering colour='No Colour' (a real dictionary value); predicted instead checks eye_colour_id IS NULL directly on superhero, assuming NULL represents 'no colour' rather than joining to check for that specific dictionary value.

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE height_cm BETWEEN 170 AND 190 
AND eye_colour_id IS NULL;
```

### Q758 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Predicted references a table named 'hair_colour', which doesn't exist anywhere in the schema -- colour is used generically via separate FK columns (eye/hair/skin_colour_id), not separate per-attribute tables.

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT T3.colour FROM superhero AS T1 JOIN hair_colour AS T2 ON T1.hair_colour_id = T2.id JOIN colour AS T3 ON T2.colour_id = T3.id WHERE T1.height_cm = 185 AND T1.race_id = (SELECT id FROM race WHERE race = 'Human')
```

### Q766 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Predicted's tie-preserving '= (SELECT MAX(attribute_value)...)' subquery is structurally equivalent to gold's CTE approach; the only visible difference is predicted's missing DISTINCT on full_name.

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT s.full_name 
FROM superhero s
JOIN hero_attribute ha ON s.id = ha.hero_id
JOIN attribute a ON ha.attribute_id = a.id
WHERE a.attribute_name = 'Strength' AND ha.attribute_value = (SELECT MAX(attribute_value) FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'Strength'))
```

### Q769 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references s.durability as if it were a direct column; superhero has no 'durability' column anywhere -- it's only represented via the hero_attribute/attribute EAV pattern.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.superhero_name
FROM superhero s
JOIN alignment a ON s.alignment_id = a.id
JOIN publisher p ON s.publisher_id = p.id
WHERE a.alignment = 'Good' AND p.publisher_name = 'Dark Horse Comics'
ORDER BY s.durability DESC
LIMIT 1;
```

### Q772 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects the raw eye_colour_id/hair_colour_id/skin_colour_id FK values directly from superhero; predicted joins colour three times and returns the resolved colour names instead -- different (though related) real columns than what was asked for.

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c1.colour AS eye_colour,
    c2.colour AS hair_colour,
    c3.colour AS skin_colour
FROM 
    superhero s
JOIN 
    gender g ON s.gender_id = g.id
JOIN 
    colour c1 ON s.eye_colour_id = c1.id
JOIN 
    colour c2 ON s.hair_colour_id = c2.id
JOIN 
    colour c3 ON s.skin_colour_id = c3.id
JOIN 
    publisher p ON s.publisher_id = p.id
WHERE 
    g.gender = 'Female' AND p.publisher_name = 'Dark Horse Comics';
```

### Q775 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters on skin_colour_id joined to colour='Blue'; predicted joins colour via eye_colour_id instead -- a different, real FK column; the colour/gender literals are also lowercased.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.colour = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM colour AS T1 
JOIN superhero AS T2 ON T1.id = T2.eye_colour_id 
JOIN gender AS T3 ON T2.gender_id = T3.id 
WHERE T3.gender = 'female';
```

### Q782 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='Black' is lowercased to 'black' in predicted; the eye/hair join restructuring (two separate colour joins vs gold's quirky single-alias double-condition join) is logically equivalent since 'Black' maps to one unique colour id either way.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name FROM superhero s JOIN colour e ON s.eye_colour_id = e.id JOIN colour h ON s.hair_colour_id = h.id WHERE e.colour = 'black' AND h.colour = 'black'
```

### Q788 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** publisher_name belongs to publisher (already joined as T3); predicted references it via T2 (superhero) instead -- an alias mix-up on an already-joined table; predicted also uses INNER JOIN instead of gold's LEFT JOIN for publisher.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM gender AS T1 JOIN superhero AS T2 ON T1.id = T2.gender_id JOIN publisher AS T3 ON T2.publisher_id = T3.id WHERE T1.gender = 'Female';
```

### Q790 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters on full_name (civilian name, e.g. 'Emil Blonsky'); predicted filters on superhero_name (codename) instead -- a different real column.

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT (SELECT weight_kg FROM superhero WHERE superhero_name = 'Emil Blonsky') - (SELECT weight_kg FROM superhero WHERE superhero_name = 'Charles Chandler') AS weight_difference
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops the height_cm > 0 filter entirely, including invalid/placeholder zero heights in the average.

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references T1.speed as if it were a direct column (and also queries hero_power/superpower as if Speed were a super-power rather than a measurable attribute); 'speed' matches no real column anywhere in the schema.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 JOIN hero_power AS T2 ON T1.id = T2.hero_id JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Speed' ORDER BY T1.speed DESC LIMIT 1
```

### Q797 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='Blue'/'Brown' are lowercased to 'blue'/'brown' in predicted.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name
FROM superhero s
JOIN colour e ON s.eye_colour_id = e.id
JOIN colour h ON s.hair_colour_id = h.id
WHERE e.colour = 'blue' AND h.colour = 'brown';
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='Blue' is lowercased to 'blue' in predicted's subquery.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM superhero AS T1 JOIN colour AS T2 ON T1.eye_colour_id = T2.id;
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Predicted drops the 'weight_kg = 0' half of gold's 'weight_kg = 0 OR weight_kg IS NULL' filter (checks IS NULL only), and substitutes eye_colour_id IS NULL for colour id=1 (a real, non-null dictionary value) -- both wrong transformations of gold's literal comparisons.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') AND weight_kg IS NULL) -
    (SELECT COUNT(*) FROM superhero WHERE eye_colour_id IS NULL AND weight_kg IS NULL) AS difference;
```

### Q822 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment='Bad' is translated to the invented value 'villain'; colour='Green' is lowercased to 'green'.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.skin_colour_id = colour.id 
JOIN alignment ON superhero.alignment_id = alignment.id 
WHERE colour.colour = 'green' AND alignment.alignment = 'villain';
```

### Q825 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Predicted references a table named 'power', which doesn't exist -- the real table is 'superpower'.

**Gold SQL:**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL:**

```sql
SELECT T3.gender 
FROM superhero AS T1 
JOIN hero_power AS T2 ON T1.id = T2.hero_id 
JOIN power AS T4 ON T2.power_id = T4.id 
JOIN gender AS T3 ON T1.gender_id = T3.id 
WHERE T4.power_name = 'Phoenix Force';
```

### Q829 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a derived table plus CASE to determine which publisher has more heroes; predicted flattens this into two scalar subqueries and omits the 'which publisher' CASE output entirely; it also uses the wrong/truncated literal 'DC' instead of 'DC Comics' for one subquery.

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
SELECT (SELECT COUNT(*) FROM superhero WHERE publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'DC')) - (SELECT COUNT(*) FROM superhero WHERE publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Marvel Comics')) AS difference
```

---

## thrombosis_prediction (48 failures)

### Q1149 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Predicted calls GREATEST(), a function SQLite doesn't support ('no such function: GREATEST').

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN SUM(CASE WHEN admission_type = 'Inpatient' AND sex = 'Male' THEN 1 ELSE 0 END) > SUM(CASE WHEN admission_type = 'Outpatient' AND sex = 'Male' THEN 1 ELSE 0 END) THEN 'Inpatient'
        ELSE 'Outpatient'
    END AS more_inpatient_or_outpatient,
    ABS(
        (SUM(CASE WHEN admission_type = 'Inpatient' AND sex = 'Male' THEN 1 ELSE 0 END) - SUM(CASE WHEN admission_type = 'Outpatient' AND sex = 'Male' THEN 1 ELSE 0 END)) * 100.0 / 
        GREATEST(SUM(CASE WHEN admission_type = 'Inpatient' AND sex = 'Male' THEN 1 ELSE 0 END), SUM(CASE WHEN admission_type = 'Outpatient' AND sex = 'Male' THEN 1 ELSE 0 END))
    ) AS deviation_percentage
FROM 
    Patient;
```

### Q1150 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters WHERE SEX='F' then computes % born after 1930 among females (denominator = all females); predicted moves the sex condition into the CASE numerator (denominator becomes ALL patients) and reverses the birthday comparison (before 1930 instead of after); it also uses Chinese '女' instead of 'F'.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = '女' AND birthday < '1930-01-01' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient;
```

### Q1152 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Admission = '+'/'-' (real symbol codes) are mistranslated to invented English values 'Inpatient'/'Outpatient'.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) AS inpatient_count,
    SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS outpatient_count,
    (SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) / SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END)) AS ratio
FROM 
    Patient
WHERE 
    diagnosis = 'SLE';
```

### Q1153 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold joins Patient directly to Laboratory (2 tables); predicted adds an unnecessary extra join to Examination, which -- since both tables have multiple rows per patient ID -- multiplies the Laboratory rows returned.

**Gold SQL:**

```sql
SELECT T1.Diagnosis, T2.Date FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 30609
```

**Predicted SQL:**

```sql
SELECT P.diagnosis, L.Date 
FROM Patient AS P 
JOIN Examination AS E ON P.ID = E.ID 
JOIN Laboratory AS L ON P.ID = L.ID 
WHERE P.ID = 30609;
```

### Q1155 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a fixed threshold LDH > 500; predicted substitutes a dynamic '> (SELECT AVG(...))' comparison instead -- a fundamentally different, restructured condition.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.lactate_dehydrogenase > (SELECT AVG(lactate_dehydrogenase) FROM Laboratory);
```

### Q1156 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters Examination.RVVT='+' (a specific coagulation test result); predicted instead filters Examination.thrombosis_degree>0 -- a completely different real column (overall thrombosis severity, not the RVVT test).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT P.ID, (strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS age
FROM Patient P
JOIN Examination E ON P.ID = E.ID
WHERE E.thrombosis_degree > 0;
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Thrombosis is a numeric severity code (gold uses =2); predicted invents a text value 'severe' instead of the real numeric code.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.diagnosis 
FROM Patient AS P 
JOIN Examination AS E ON P.ID = E.ID 
WHERE E.thrombosis_degree = 'severe';
```

### Q1162 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters year(Description) [aliased first_record_date]; predicted instead filters first_hospital_visit_date (Patient.'First Date') -- a different, real column; sex and admission_type values are also wrong.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE sex = 'female' 
AND strftime('%Y', first_hospital_visit_date) = '1997' 
AND admission_type = 'immediate_outpatient';
```

### Q1164 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Thrombosis=1 (numeric code) is mistranslated to the invented text 'most serious'; sex is also 'female' instead of 'F'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID)
FROM `Patient` AS T1
JOIN `Examination` AS T2 ON T1.ID = T2.ID
WHERE T1.`SEX` = 'F'
  AND STRFTIME('%Y', T2.`Examination Date`) = '1997'
  AND T2.`Thrombosis` = 1;
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE e.thrombosis_degree = 'most serious' AND strftime('%Y', e.examination_date) = '1997' AND p.sex = 'female';
```

### Q1168 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold joins only Laboratory+Patient; predicted adds an unnecessary Examination join, which (given multiple Examination rows per patient) duplicates Laboratory rows and can change which row LIMIT 1 picks; it also drops gold's secondary ORDER BY Date DESC tiebreak.

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    L.Date AS last_laboratory_date,
    (strftime('%Y', P.first_hospital_visit_date) - strftime('%Y', P.birthday)) - 
    (strftime('%m-%d', P.first_hospital_visit_date) < strftime('%m-%d', P.birthday)) AS age_at_first_visit
FROM 
    Patient P
JOIN 
    Examination E ON P.ID = E.ID
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    P.diagnosis = 'SJS'
ORDER BY 
    P.birthday ASC
LIMIT 1;
```

### Q1169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold computes a ratio using per-gender UA thresholds via CASE (male UA<=8.0 vs female UA<=6.5); predicted abandons this entirely for SUM(sex)/SUM(sex) with an unrelated WHERE filter (uric_acid != AVG(...)) with no correspondence to gold's logic; Chinese values are also used.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.sex = '男' THEN 1 ELSE 0 END) * 1.0 / 
    SUM(CASE WHEN T1.sex = '女' THEN 1 ELSE 0 END) AS male_female_ratio
FROM 
    Patient AS T1
JOIN 
    Laboratory AS T2 ON T1.ID = T2.ID
WHERE 
    T2.uric_acid != (SELECT AVG(uric_acid) FROM Laboratory);
```

### Q1171 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold computes age AT THE TIME OF EXAMINATION (year(Examination Date) - year(Birthday) < 18), relative to each row's own exam year; predicted substitutes a single fixed cutoff (birthday > 1987-12-31), losing the per-row relative-to-exam-date computation.

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient AS P 
JOIN Examination AS E ON P.ID = E.ID 
WHERE P.birthday > '1987-12-31' AND E.examination_date BETWEEN '1990-01-01' AND '1993-12-31';
```

### Q1175 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Predicted's ORDER BY references L.hemoglobin, but no alias 'L' (Laboratory) was ever introduced in the FROM/JOIN clause -- only Examination and Patient are joined.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    (strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS age,
    E.diagnosis
FROM 
    Examination E
JOIN 
    Patient P ON E.ID = P.ID
ORDER BY 
    L.hemoglobin DESC
LIMIT 1;
```

### Q1179 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters Patient.Description [aliased first_record_date] = '1994-02-19'; predicted instead filters Patient.birthday = '1994-02-19' -- a different real column; predicted also selects 5 columns instead of gold's single 'aCL IgM'.

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT e.anticardiolipin_igg, e.anticardiolipin_igm, e.antinuclear_antibody, e.antinuclear_antibody_pattern, e.anticardiolipin_iga
FROM Examination e
JOIN Patient p ON e.ID = p.ID
WHERE p.diagnosis = 'SLE' AND p.birthday = '1994-02-19' AND e.examination_date = '1993-11-12';
```

### Q1185 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references L1.patient_id, but Laboratory's actual ID column is just 'ID' -- 'patient_id' doesn't exist as a column name anywhere in this schema.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (L2.total_cholesterol - L1.total_cholesterol) / L1.total_cholesterol * 100 AS decrease_rate
FROM 
    Laboratory L1
JOIN 
    Laboratory L2 ON L1.ID = L2.ID
WHERE 
    L1.Date BETWEEN '1981-11-01' AND '1981-11-30'
    AND L2.Date BETWEEN '1981-12-01' AND '1981-12-31'
    AND L1.patient_id IN (
        SELECT ID FROM Patient WHERE birthday = '1959-02-18'
    );
```

### Q1187 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GPT (alanine_aminotransferase) is confused with GOT (aspartate_aminotransferase) -- two different real Laboratory columns; predicted also filters on Examination.examination_date via unneeded extra joins instead of Laboratory.Date directly.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT P.ID 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
JOIN Laboratory L ON P.ID = L.ID 
WHERE E.examination_date BETWEEN '1987-07-06' AND '1996-01-31' 
AND L.aspartate_aminotransferase > 30 
AND L.albumin < 4;
```

### Q1189 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold's subquery average is scoped by BOTH Thrombosis=2 AND ANA Pattern='S' (same filters as the outer query); predicted's subquery only filters ANA Pattern='S', dropping the Thrombosis=2 condition inside the subquery.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID)
FROM Patient p
JOIN Examination e ON p.ID = e.ID
WHERE e.thrombosis_degree = 2 
  AND e.anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) FROM Examination WHERE antinuclear_antibody_pattern = 'S') * 1.2;
```

### Q1192 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold joins only Patient+Laboratory; predicted adds an unnecessary Examination join (row-duplication risk); it also substitutes wrong values/thresholds (admission_type='outpatient' vs '-', and total_bilirubin BETWEEN 0.5-1.2 instead of gold's simple < 2.0 upper bound).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday, P.first_record_date, P.first_hospital_visit_date, P.admission_type, P.diagnosis
FROM Patient P
JOIN Examination E ON P.ID = E.ID
JOIN Laboratory L ON P.ID = L.ID
WHERE P.admission_type = 'outpatient'
  AND strftime('%Y-%m', L.Date) = '1991-10'
  AND L.total_bilirubin BETWEEN 0.5 AND 1.2;
```

### Q1195 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** SEX='F' is replaced with 'female' in predicted; otherwise the join/filter logic matches gold exactly.

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(L.albumin) 
FROM Laboratory L 
JOIN Patient P ON L.ID = P.ID 
WHERE P.sex = 'female' AND L.platelet_count > 400 AND P.diagnosis = 'SLE';
```

### Q1198 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters Patient.Diagnosis directly (no join needed); predicted instead joins Examination and filters Examination.Diagnosis -- a different real column requiring an unnecessary join, which would also exclude patients with zero Examination records; sex 'female' vs 'F' is also wrong.

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient AS P JOIN Examination AS E ON P.ID = E.ID WHERE P.sex = 'female' AND E.diagnosis = 'APS';
```

### Q1201 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold queries Patient alone (no join needed); predicted adds an unnecessary Examination join, which -- since a patient can have multiple Examination rows -- inflates the COUNT(*) denominator by duplicating patients; Chinese '女' is also used instead of 'F'.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.sex = '女' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient AS T1 JOIN Examination AS T2 ON T1.ID = T2.ID WHERE strftime('%Y', T1.birthday) = '1980' AND T1.diagnosis = 'RA'
```

### Q1205 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold checks gender-specific UA thresholds (F>6.5 or M>8.0) via CASE; predicted substitutes a generic population 'normal range' BETWEEN 140 AND 420 check with no gender distinction at all.

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN uric_acid BETWEEN 140 AND 420 THEN 'true' ELSE 'false' END AS is_within_normal_range FROM Laboratory WHERE ID = 57266;
```

### Q1208 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GPT (alanine_aminotransferase) is confused with GOT (aspartate_aminotransferase) again -- a different real column; predicted also uses a dynamic AVG-based threshold instead of gold's fixed >=60, and 'male' instead of 'M'.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT P.ID
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE P.sex = 'male' AND L.aspartate_aminotransferase > (SELECT AVG(aspartate_aminotransferase) FROM Laboratory);
```

### Q1209 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GPT (alanine_aminotransferase) is confused with GOT (aspartate_aminotransferase) -- a different real column; predicted also uses a dynamic AVG-based threshold instead of gold's fixed >60.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.diagnosis 
FROM Patient AS P 
JOIN Laboratory AS L ON P.ID = L.ID 
WHERE L.aspartate_aminotransferase > (SELECT AVG(aspartate_aminotransferase) FROM Laboratory) 
ORDER BY P.birthday ASC;
```

### Q1220 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold filters the exact value UN=29; predicted substitutes a 'normal range' BETWEEN 6.5 AND 7.5 check instead -- a completely different, restructured condition unrelated to the specific value 29 gold asks about.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.urea_nitrogen BETWEEN 6.5 AND 7.5;
```

### Q1225 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold lists patient IDs (GROUP_CONCAT) with T-BIL>=2.0 grouped by sex; predicted instead computes AVG(bilirubin) for patients outside a normal range (0.6-1.9) -- both the WHERE condition and the aggregate function are fundamentally different from what gold asks.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.sex, AVG(L.total_bilirubin) AS avg_total_bilirubin
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.total_bilirubin < 0.6 OR L.total_bilirubin > 1.9
GROUP BY P.sex;
```

### Q1227 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** T-CHO/total_cholesterol lives on Laboratory, not Examination; predicted joins Examination instead of Laboratory entirely, so the column doesn't exist there; sex '男' is also wrong.

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(JULIANDAY(Patient.first_hospital_visit_date) - JULIANDAY(Patient.birthday)) / 365 AS average_age FROM Patient JOIN Examination ON Patient.ID = Examination.ID WHERE Patient.sex = '男' AND Examination.total_cholesterol > (SELECT AVG(total_cholesterol) FROM Examination);
```

### Q1229 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a fixed TG>=200 threshold; predicted substitutes a dynamic '> AVG(...)' comparison instead.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID)
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.triglyceride > (SELECT AVG(triglyceride) FROM Laboratory)
AND strftime('%Y', 'now') - strftime('%Y', P.birthday) > 50;
```

### Q1231 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a fixed CPK>=250 threshold; predicted substitutes a dynamic '> AVG(...)' comparison instead; DISTINCT is also dropped and sex is '男' instead of 'M'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient p
JOIN Laboratory l ON p.ID = l.ID
WHERE p.sex = '男' AND p.birthday BETWEEN '1936-01-01' AND '1956-12-31' AND l.creatinine_phosphokinase > (SELECT AVG(creatinine_phosphokinase) FROM Laboratory);
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses simple fixed thresholds (GLU>=180, T-CHO<250); predicted substitutes 'normal range' exclusion/inclusion checks (glucose NOT BETWEEN 3.9-6.1, cholesterol BETWEEN 5.2-200) that don't correspond to gold's thresholds at all.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, strftime('%Y', 'now') - strftime('%Y', P.birthday) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.blood_glucose NOT BETWEEN 3.9 AND 6.1 AND L.total_cholesterol BETWEEN 5.2 AND 200;
```

### Q1235 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references P.age as if it were a stored column; Patient has no 'age' column at all -- gold computes it via STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', Birthday).

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT P.ID, P.age 
FROM Patient P 
JOIN (SELECT ID FROM Laboratory WHERE red_blood_cell_count < (SELECT AVG(red_blood_cell_count) FROM Laboratory)) L ON P.ID = L.ID;
```

### Q1238 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** hemoglobin (HGB) lives on Laboratory, not Examination; predicted joins Examination instead of Laboratory entirely.

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE P.diagnosis = 'SLE' AND E.hemoglobin IS NOT NULL AND E.hemoglobin >= 13.5 
ORDER BY P.birthday ASC 
LIMIT 1;
```

### Q1239 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Gold requires HCT>=52 (at least twice); predicted uses 48 instead -- a different threshold value, same structure/operator otherwise.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.ID, (strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.hematocrit > 48
GROUP BY P.ID
HAVING COUNT(L.ID) >= 2;
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses fixed thresholds PLT<100 and PLT>400; predicted uses 150 and 450 instead -- different threshold values, same structure otherwise.

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM Patient WHERE ID IN (SELECT ID FROM Laboratory WHERE platelet_count < 150)) AS lower_than_normal,
    (SELECT COUNT(*) FROM Patient WHERE ID IN (SELECT ID FROM Laboratory WHERE platelet_count > 450)) AS higher_than_normal;
```

### Q1242 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references P.age as if it were a stored column; Patient has no 'age' column at all (same hallucination as Q1235).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, P.birthday, P.first_record_date, P.first_hospital_visit_date, P.admission_type, P.diagnosis
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE strftime('%Y', L.Date) = '1984' AND P.age < 50 AND L.platelet_count BETWEEN 150 AND 450;
```

### Q1243 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** PT (prothrombin_time) lives on Laboratory, not Examination; predicted joins Examination instead of Laboratory entirely.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.sex = '女' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE strftime('%Y', 'now') - strftime('%Y', T1.birthday) > 55 AND T2.prothrombin_time IS NOT NULL AND ABS(T2.prothrombin_time - 10) >= 2;
```

### Q1247 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses specific fixed thresholds (FG<=150 OR >=450, WBC>3.5 AND <9.0); predicted substitutes different-scale 'normal range' thresholds (fibrinogen NOT BETWEEN 1.5-3.5, WBC BETWEEN 4.0-10.0) that don't correspond to gold's values at all -- a units/scale-confused restructuring.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID)
FROM Patient p
JOIN Laboratory l ON p.ID = l.ID
WHERE p.sex = '男' AND l.white_blood_cell_count BETWEEN 4.0 AND 10.0 AND l.fibrinogen NOT BETWEEN 1.5 AND 3.5;
```

### Q1251 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses a fixed IGG>=2000 threshold; predicted substitutes a dynamic '> AVG(...)' comparison instead, and drops the Patient join/DISTINCT entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Laboratory WHERE immunoglobulin_g > (SELECT AVG(immunoglobulin_g) FROM Laboratory);
```

### Q1252 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Symptoms lives on Examination, not Patient; predicted never joins Examination at all, referencing P.symptoms directly; it also uses immunoglobulin_g BETWEEN 1.5-8.0 instead of gold's 900-2000 (a unit-scale confusion).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.immunoglobulin_g IS NOT NULL AND L.immunoglobulin_g BETWEEN 1.5 AND 8.0 AND P.symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses IGA BETWEEN 80 AND 500 (fixed values); predicted substitutes 0.8 AND 1.6 instead -- a completely different scale, likely a units confusion / 'normal range' substitution.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Laboratory l ON p.ID = l.ID 
WHERE p.first_hospital_visit_date > '1990-01-01' AND l.immunoglobulin_a BETWEEN 0.8 AND 1.6;
```

### Q1256 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters Patient.Description IS NULL (aliased first_record_date); predicted instead filters Patient.diagnosis LIKE '%abnormal%' -- a completely different, fabricated condition on the wrong column; the CRP='+' filter is also restructured into an anti-join pattern instead of the specific value check.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
LEFT JOIN Laboratory l ON p.ID = l.ID AND l.c_reactive_protein IS NOT NULL 
WHERE p.diagnosis LIKE '%abnormal%' AND l.ID IS NULL;
```

### Q1257 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold uses CRE>=1.5 and age<70 (via CURRENT_TIMESTAMP-Birthday); predicted substitutes a wrong-scale creatinine range (NOT BETWEEN 65-110) and replaces the age computation with first_hospital_visit_date<'2023-07-01' -- an unrelated column/condition.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Laboratory l ON p.ID = l.ID 
WHERE l.creatinine IS NOT NULL AND (l.creatinine < 65 OR l.creatinine > 110) AND p.first_hospital_visit_date < '2023-07-01';
```

### Q1265 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** RNP (anti_ribonuclear_protein) lives on Laboratory, not Examination; predicted joins Examination instead -- it also uses IS NULL logic instead of IN ('negative','0'), and 'Hospital' instead of '+' for admission_type.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE e.anti_ribonuclear_protein IS NULL AND p.admission_type = 'Hospital';
```

### Q1267 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold requires Laboratory.SM IN ('negative','0'); predicted instead filters Patient.diagnosis LIKE '%anti-SM%' -- a fabricated condition on the wrong table/column; it also drops gold's CTE-based 'never had any thrombosis across all exam records' aggregation entirely.

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
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE p.diagnosis LIKE '%anti-SM%' AND e.thrombosis_degree IS NULL;
```

### Q1270 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references e.antiscl70 -- not only is this on the wrong table (SC170's real alias 'anti_scl70' lives on Laboratory, not Examination), the name is also misspelled (missing the underscore), matching no real column anywhere.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT p.ID)
FROM `Patient`   p
JOIN `Laboratory` l ON p.ID = l.ID
WHERE p.SEX = 'F'
  AND l.SC170 IN ('negative','0')
  AND NOT EXISTS (  
        SELECT 1
        FROM `Examination` e
        WHERE e.ID = p.ID
          AND e.Symptoms IS NOT NULL
  );
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE p.sex = '女' AND e.antiscl70 IS NULL AND p.symptoms = '';
```

### Q1275 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold checks CENTROMEA/SSB IN ('negative','0') (specific text values); predicted checks IS NULL instead -- a different, wrong transformation; sex '男' is also used instead of 'M'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
JOIN Laboratory ON Patient.ID = Laboratory.ID 
WHERE Patient.sex = '男' AND Laboratory.anti_centromere IS NULL AND Laboratory.anti_ssb IS NULL;
```

### Q1281 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Gold orders by Birthday DESC LIMIT 1 (picks the youngest patient among those with GOT>=60); predicted computes MIN(birthday) instead -- the wrong direction (picks the oldest patient); the threshold (>40 vs >=60) is also wrong.

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(P.birthday) AS youngest_birthdate
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.aspartate_aminotransferase > 40;
```

### Q1302 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** CPK (creatinine_phosphokinase) lives on Laboratory, not Examination; predicted never joins Laboratory at all -- it also drops the (KCT='+' OR RVVT='+' OR LAC='+') condition entirely, replacing it with an unrelated thrombosis_degree>0 filter.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.ID) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE e.creatinine_phosphokinase BETWEEN 18 AND 250 AND e.thrombosis_degree > 0;
```

---

## toxicology (38 failures)

### Q197 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold computes oxygen count PER MOLECULE (GROUP BY molecule_id) then averages across molecules; predicted's subquery has no GROUP BY at all, computing one combined COUNT(*) across all qualifying atoms, so AVG() over that single row just returns the total; element case ('O' vs 'o') and bond_type ('single' vs '-') are also wrong.

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(oxygen_count) FROM ( SELECT COUNT(*) AS oxygen_count FROM atom WHERE element = 'O' AND molecule_id IN ( SELECT molecule_id FROM bond WHERE bond_type = 'single' ) )
```

### Q198 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Predicted writes AVG(COUNT(*)) -- a nested aggregate function, which SQLite disallows ('misuse of aggregate function COUNT()').

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) FROM ( SELECT T1.molecule_id FROM molecule AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = 'single' GROUP BY T1.molecule_id )
```

### Q200 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects DISTINCT molecule_id; predicted selects T1.label instead -- a different real column; bond_type='#' is also mistranslated to 'triple' and label='+' to a LIKE '%carcinogenic%' pattern.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT T1.label FROM molecule AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = 'triple' AND T1.label LIKE '%carcinogenic%'
```

### Q201 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='c' is capitalized to 'C' and bond_type='=' is translated to 'double' in predicted; the atom-to-bond-via-molecule_id join matches gold's own (fan-out-prone) structure, so the missing COUNT(DISTINCT...) dedup is secondary to the literal mismatches.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = 'double'
```

### Q206 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** 'TR004_8_9' is a bond_id value; gold filters connected.bond_id='TR004_8_9' directly. Predicted misinterprets this string as a molecule.label value and constructs a wrong subquery chain that doesn't correspond to any real molecule.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT bond_id FROM bond WHERE molecule_id = ( SELECT molecule_id FROM molecule WHERE label = 'TR004_8_9' ) )
```

### Q207 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold identifies the specific atoms that are endpoints of double bonds via the connected bridge table; predicted skips connected entirely, joining atom directly to bond via molecule_id, returning every atom in any molecule containing a double bond somewhere.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = 'double'
```

### Q208 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='h' is capitalized to 'H' in predicted; the GROUP BY/COUNT/ORDER BY/LIMIT structure otherwise matches gold.

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT T1.label FROM molecule AS T1 JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.element = 'H' GROUP BY T1.label ORDER BY COUNT(*) DESC LIMIT 1
```

### Q212 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold uses HAVING with a tie-preserving nested MIN(cnt) subquery to find the element(s) with fewest atoms; predicted collapses this to GROUP BY+ORDER BY ASC LIMIT 1 (loses ties); it also mistranslates label='-' into a NOT LIKE '%carcinogenic%' pattern.

**Gold SQL:**

```sql
SELECT `a`.`element`
FROM `atom` AS `a`
JOIN `molecule` AS `m`  ON `a`.`molecule_id` = `m`.`molecule_id`
WHERE `m`.`label` = '-'
GROUP BY `a`.`element`
HAVING COUNT(*) = (
    SELECT MIN(cnt)
    FROM (
        SELECT COUNT(*) AS cnt
        FROM `atom` AS `a2`
        JOIN `molecule` AS `m2` ON `a2`.`molecule_id` = `m2`.`molecule_id`
        WHERE `m2`.`label` = '-'
        GROUP BY `a2`.`element`
    )
);
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label NOT LIKE '%carcinogenic%' GROUP BY T1.element ORDER BY COUNT(*) ASC LIMIT 1
```

### Q213 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The OR-condition logic is functionally identical to gold's (just reordered); predicted's missing DISTINCT can surface duplicate bond_type rows if 'connected' stores both directions of the same bond.

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT T1.bond_type FROM bond AS T1 JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE (T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20') OR (T2.atom_id = 'TR004_20' AND T2.atom_id2 = 'TR004_8')
```

### Q215 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold avoids joining atom to bond directly (scopes via molecule_id IN (subquery)); predicted instead joins atom->molecule->bond directly on molecule_id, multiplying each atom row by the molecule's bond count with no DISTINCT dedup; bond_type and element case are also wrong.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.element = 'I' THEN 1 ELSE 0 END) AS iodine_count,
    SUM(CASE WHEN T1.element = 'S' THEN 1 ELSE 0 END) AS sulfur_count
FROM 
    atom AS T1
JOIN 
    molecule AS T2 ON T1.molecule_id = T2.molecule_id
JOIN 
    bond AS T3 ON T2.molecule_id = T3.molecule_id
WHERE 
    T3.bond_type = 'single';
```

### Q218 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold compares label='+' directly (exact match); predicted uses label LIKE '%carcinogenic%' instead -- both the operator and the value/structure changed; element case ('F' vs 'f') is also wrong.

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.label LIKE '%carcinogenic%'
```

### Q219 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold computes the % of triple-bond-containing molecules that are labeled '+'; predicted inverts this into the % of bonds (among label-matching molecules) that are triple bonds -- numerator/denominator roles swapped; literals ('triple' vs '#', LIKE '%carcinogenic%' vs '+') are also wrong.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label LIKE '%carcinogenic%'
```

### Q220 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters atom.molecule_id='TR000' directly (single table, no join needed); predicted instead joins molecule and filters molecule.label='TR000' -- label holds '+'/'-' values, not molecule IDs.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR000' ORDER BY T1.element ASC LIMIT 3
```

### Q226 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters bond.molecule_id='TR008' directly (single table, no join needed); predicted instead joins molecule and filters molecule.label='TR008' -- the same recurring ID/label confusion; bond_type is also mistranslated to 'double'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR008'
```

### Q227 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold compares label='+' directly (exact match, over the whole molecule table); predicted uses label LIKE '%carcinogenic%' instead -- both the operator and value/structure changed.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN molecule.label LIKE '%carcinogenic%' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(molecule.molecule_id) FROM molecule
```

### Q228 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters atom.molecule_id='TR206' directly (single table, no join needed); predicted instead joins molecule and filters molecule.label='TR206' -- the same recurring ID/label confusion.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR206'
```

### Q230 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters atom.molecule_id='TR060' directly; predicted instead filters molecule.label='TR060' via unneeded extra joins to connected/bond, and adds a fabricated bond_type='toxicology' condition.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT T1.element, T4.label FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN bond AS T3 ON T2.bond_id = T3.bond_id JOIN molecule AS T4 ON T1.molecule_id = T4.molecule_id WHERE T4.label = 'TR060' AND T3.bond_type = 'toxicology'
```

### Q231 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters bond.molecule_id='TR010' directly (no molecule join needed); predicted instead joins molecule and filters molecule.label='TR010' -- the same recurring ID/label confusion.

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT T2.bond_type FROM molecule AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = 'TR010' GROUP BY T2.bond_type ORDER BY COUNT(*) DESC LIMIT 1
```

### Q232 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects DISTINCT molecule_id; predicted selects m.label instead -- a different, wrong real column (and orders by it too); it also drops the label='-' filter entirely and adds an unnecessary GROUP BY/HAVING.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT m.label 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
WHERE b.bond_type = 'single' 
GROUP BY m.molecule_id 
HAVING COUNT(b.bond_id) >= 1 
ORDER BY m.label ASC 
LIMIT 3;
```

### Q234 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold's atom_id already encodes the molecule prefix (e.g. 'TR009_12'), used directly, no molecule join needed; predicted uses a bare numeric 12 for atom_id and adds a molecule.label='TR009' condition -- the same recurring ID/label confusion.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM bond 
JOIN connected ON bond.bond_id = connected.bond_id 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
WHERE (connected.atom_id = 12 OR connected.atom_id2 = 12) AND molecule.label = 'TR009';
```

### Q236 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** 'TR001_6_9' is a bond_id value; gold filters connected.bond_id='TR001_6_9' directly. Predicted instead references T1.label (bond table, which has no label column at all) -- the same recurring ID/label confusion, and molecule is never joined.

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT T1.bond_type, T3.element AS atom1_element, T4.element AS atom2_element FROM bond AS T1 JOIN connected AS T2 ON T1.bond_id = T2.bond_id JOIN atom AS T3 ON T2.atom_id = T3.atom_id JOIN atom AS T4 ON T2.atom_id2 = T4.atom_id WHERE T1.label = 'TR001_6_9'
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** atom_id is a compound text string like 'TR009_19'; gold uses SUBSTR(atom_id,-2)='19' to match the numeric suffix; predicted compares atom_id=19 directly as if it were a bare integer.

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected WHERE atom_id = 19 OR atom_id2 = 19;
```

### Q240 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters atom.molecule_id='TR004' directly (single table); predicted instead joins molecule and filters molecule.label='TR004' -- the same recurring ID/label confusion.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR004'
```

### Q242 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold selects DISTINCT molecule_id; predicted selects DISTINCT label instead -- a different real column; it also drops the label='+' filter entirely and uses atom_id BETWEEN 21 AND 25 directly instead of gold's SUBSTR(atom_id,-2) BETWEEN '21' AND '25' text-suffix check.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label
FROM molecule m
JOIN atom a ON m.molecule_id = a.molecule_id
WHERE a.atom_id BETWEEN 21 AND 25;
```

### Q243 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element codes 'p'/'n' (phosphorus/nitrogen) are mistranslated to full spelled-out 'Phosphorus'/'Nitrogen', which don't match the real stored single-letter codes.

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT T1.bond_id FROM bond AS T1 JOIN connected AS T2 ON T1.bond_id = T2.bond_id JOIN atom AS T3 ON T2.atom_id = T3.atom_id JOIN atom AS T4 ON T2.atom_id2 = T4.atom_id WHERE (T3.element = 'Phosphorus' AND T4.element = 'Nitrogen') OR (T3.element = 'Nitrogen' AND T4.element = 'Phosphorus')
```

### Q244 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by molecule_id (via CTE) to count double bonds per molecule and find the max; predicted groups by T1.label instead -- collapsing hundreds of different molecules sharing the same label into one group; it also collapses the tie-preserving MAX subquery into ORDER BY/LIMIT 1.

**Gold SQL:**

```sql
with sub as ( SELECT T.molecule_id, COUNT(T.bond_type) as cnt
 FROM bond AS T WHERE T.bond_type = '=' GROUP BY T.molecule_id 
) 
SELECT T1.label FROM molecule AS T1 INNER JOIN sub
 AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.cnt = (select max(cnt) from sub)
```

**Predicted SQL:**

```sql
SELECT T1.label FROM molecule AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = 'double' GROUP BY T1.label ORDER BY COUNT(T2.bond_id) DESC LIMIT 1
```

### Q245 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold counts each iodine atom's actual bond-participations via the connected bridge table; predicted instead joins atom to bond via molecule_id (counting ALL bonds in the atom's molecule) and wraps it in AVG() with no GROUP BY at all.

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) FROM ( SELECT COUNT(*) AS bond_count FROM atom JOIN bond ON atom.molecule_id = bond.molecule_id WHERE atom.element = 'I' )
```

### Q247 (challenging, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** The NOT IN subquery logic matches gold exactly; predicted's missing DISTINCT can surface duplicate element values if multiple unconnected atoms share the same element.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id NOT IN (SELECT atom_id FROM connected)
```

### Q248 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold filters bond.molecule_id='TR041' directly; predicted instead filters molecule.label='TR041' via an unneeded extra molecule join -- the same recurring ID/label confusion; bond_type is also mistranslated to 'triple'.

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT T3.atom_id FROM molecule AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id JOIN connected AS T3 ON T2.bond_id = T3.bond_id WHERE T1.label = 'TR041' AND T2.bond_type = 'triple'
```

### Q249 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** 'TR144_8_19' is a bond_id value; gold filters connected.bond_id='TR144_8_19' directly. Predicted instead filters molecule.label='TR144_8_19' -- the same recurring ID/label confusion, dropping the connected bridge table entirely.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR144_8_19'
```

### Q253 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold identifies the specific endpoint atoms of triple bonds via the connected bridge table; predicted skips connected and joins atom directly to bond via molecule_id, returning every atom in any molecule with a triple bond somewhere.

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = 'triple'
```

### Q255 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold joins bond to molecule (label='+') directly; predicted instead joins bond to connected/atom and filters atom.element='carcinogenic' -- 'carcinogenic' is a molecule.label concept, not any real chemical element value, and connected/atom is the wrong table entirely.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond AS T1 JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id IN ( SELECT atom_id FROM atom WHERE element = 'carcinogenic' )
```

### Q260 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold counts ALL atoms in molecules that merely contain a triple bond AND contain a phosphorus/bromine atom somewhere (molecule-level existence filters via two IN-subqueries); predicted requires each individually counted atom to itself have element IN ('phosphorus','bromine') -- turning molecule-level existence filters into row-level equality filters.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.atom_id) 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
JOIN bond AS T3 ON T1.molecule_id = T3.molecule_id 
WHERE T3.bond_type = 'triple' AND (T1.element = 'phosphorus' OR T1.element = 'bromine');
```

### Q263 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold scopes to single-bond molecules via molecule_id IN (subquery), avoiding any join to bond on the atom rows; predicted joins atom->molecule->bond directly via molecule_id, multiplying each atom row by the molecule's bond count with no DISTINCT dedup; element case and bond_type value are also wrong.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN T1.element = 'Cl' THEN 1 ELSE NULL END) * 100.0 / COUNT(T1.element)) AS percentage
FROM 
    atom AS T1
JOIN 
    molecule AS T2 ON T1.molecule_id = T2.molecule_id
JOIN 
    bond AS T3 ON T2.molecule_id = T3.molecule_id
WHERE 
    T3.bond_type = 'single';
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label='+' is mistranslated to invented values 'Carcinogen'/'Carcinogenic Compound' via IN(); element case 'Cl' vs 'cl' is also wrong; the atom-molecule join structure matches gold exactly.

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label IN ('Carcinogen', 'Carcinogenic Compound')
```

### Q281 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold's SUBSTR(atom_id,-2)='_4' matches atoms whose ID literally ends in '_4'; predicted instead picks the atom at ordinal position 4 via a correlated ORDER BY atom_id LIMIT 3,1 subquery -- a wrong transformation -- and drops the GROUP BY element aggregation entirely.

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT m.label, a.element
FROM molecule m
JOIN atom a ON m.molecule_id = a.molecule_id
WHERE a.atom_id = (SELECT atom_id FROM atom WHERE molecule_id = m.molecule_id ORDER BY atom_id LIMIT 3, 1)
AND m.label IN ('Carcinogenic');
```

### Q282 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** 'TR006' is a molecule_id value; gold's CTE filters molecule_id='TR006'. Predicted instead filters T3.label='TR006' -- the same recurring ID/label confusion, causing the WHERE clause to match nothing.

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) AS ratio, T3.label FROM atom AS T1 JOIN molecule AS T3 ON T1.molecule_id = T3.molecule_id WHERE T3.label = 'TR006'
```

### Q327 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold groups by molecule_id to find molecule(s) with more than 5 atoms; predicted groups by T1.label instead -- collapsing ALL molecules sharing a label into one giant group; it also mistranslates label='-' into a NOT LIKE '%carcinogenic%' pattern and selects label instead of molecule_id.

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT T1.label FROM molecule AS T1 JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label NOT LIKE '%carcinogenic%' GROUP BY T1.label HAVING COUNT(T2.atom_id) > 5
```

---

