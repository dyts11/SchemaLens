# Qwen2.5-Coder-14B · L2·S3 — hand-classified failures (n=319)

Every failure was read by hand and classified against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used. L2 replaces the 3NF schema with per-database 2NF synthetic cluster tables (`two_nf_*`, see `preprocess_data/to_2nf/specs.py`); the harness's `gold_sql` column is always the original 3NF BIRD query (executed against the 3NF database by the harness), so for this file each entry's classification reasoning is based on a constructed reference query against the actual `two_nf_*` cluster table the model targeted -- the gold_sql shown below is still the original 3NF form for readability, but the bug diagnosis in 'Reason' accounts for the cluster-table translation (including checking `src/column_aliases.py` before calling any renamed column wrong, and checking for fan-out row-duplication from the cluster's FULL OUTER JOIN chain). Several 'Reason' entries note an empirical verification (direct execution of gold vs. a reconstructed reference query against the `.sqlite` files) where the diff between predicted and gold was subtle enough to need it. Grouped by database, sorted by question id.

| Category | Legend |
|---|---|
| Invalid SQL | |
| Schema linking | |
| JOIN errors | |
| Fan-out | |
| GROUP BY errors | |
| Nesting problem | |
| Predicate error | |
| Other | |

---

## california_schools (29 failures)

### Q5 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Virtual='Yes' is an invented value (real domain is 'F'/'P'/'N'; gold needs 'F'), and also drops satscores__record_type='S' needed to exclude non-school aggregate rows.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT `T2`.`CDSCode`)
FROM `satscores` AS T1
JOIN `schools`  AS T2 ON T1.`cds` = T2.`CDSCode`
WHERE T2.`Virtual` = 'F'
  AND T1.`AvgScrMath` > 400 AND rtype = 'S'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT schools__county_district_school_code)
FROM two_nf_schools
WHERE satscores__average_score_math > 400
AND schools__Virtual = 'Yes';
```

### Q11 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters on satscores__enrollment_grade_12 (grade-12 test population) instead of the sum of frpm__enrollment_k12 + frpm__enrollment_ages_5_17 that the question actually asks about.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__county_district_school_code
FROM two_nf_schools
WHERE satscores__enrollment_grade_12 > 500;
```

### Q12 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** WHERE predicate uses satscores__average_score_reading > 0.3 instead of the NumGE1500/NumTstTakr ratio > 0.3 gold requires -- an unrelated column filling the threshold-predicate role.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MAX(frpm__percent_eligible_free_ages_5_17)
FROM two_nf_schools
WHERE satscores__average_score_reading > 0.3
```

### Q17 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops both the schools__charter_number IS NOT NULL and satscores__record_type='S' filters gold applies.

**Gold SQL (original 3NF form):**

```sql
SELECT CharterNum, AvgScrWrite, 
RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank 
FROM schools AS T1  INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds 
WHERE T2.AvgScrWrite > 499 AND CharterNum is not null AND rtype = 'S'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    schools__charter_number, 
    satscores__average_score_writing, 
    RANK() OVER (ORDER BY satscores__average_score_writing DESC) as rank
FROM 
    two_nf_schools
WHERE 
    satscores__average_score_writing > 499;
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Wraps the enrollment difference in ABS(), which admits cases where 5-17 enrollment exceeds K-12 enrollment by >30 that gold's unsigned difference excludes.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    schools__Street, 
    schools__City, 
    schools__Zip, 
    schools__State
FROM 
    two_nf_schools
WHERE 
    ABS(frpm__enrollment_k12 - frpm__enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the satscores__record_type='S' filter, letting district-level aggregate rows (rtype='D') leak into the result.

**Gold SQL (original 3NF form):**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__School
FROM two_nf_schools
WHERE frpm__percent_eligible_free_k12 > 0.1
AND satscores__number_scores_1500_or_above > 0;
```

### Q25 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters schools__County = 'Riverside' instead of the requested District LIKE 'Riverside%'; also collapses gold's GROUP BY sname, FundingType HAVING AVG(math)>400 into a plain row filter.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    schools__funding_type
FROM 
    two_nf_schools
WHERE 
    schools__County = 'Riverside' 
    AND satscores__average_score_math > 400;
```

### Q26 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the frpm__school_type = 'High Schools (Public)' filter entirely.

**Gold SQL (original 3NF form):**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    schools__Street, 
    schools__City, 
    schools__Zip, 
    schools__State
FROM 
    two_nf_schools
WHERE 
    schools__County = 'Monterey' 
    AND frpm__free_or_reduced_price_meal_count_ages_5_17 > 800;
```

### Q27 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds a spurious satscores__average_score_writing IS NOT NULL filter not present in gold, which (since gold's LEFT JOIN preserves score-less schools) wrongly excludes qualifying schools with no SAT record.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    satscores__average_score_writing, 
    schools__Phone
FROM 
    two_nf_schools
WHERE 
    (schools__open_date > '1991-12-31' OR schools__closed_date < '2000-01-01')
    AND satscores__average_score_writing IS NOT NULL;
```

### Q28 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Subquery references bare `enrollment_k12`/`enrollment_ages_5_17` without the required frpm__ prefix, causing 'no such column: enrollment_k12'.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    frpm__district_type
FROM 
    two_nf_schools
WHERE 
    ABS(frpm__enrollment_k12 - frpm__enrollment_ages_5_17) > (
        SELECT 
            AVG(ABS(enrollment_k12 - enrollment_ages_5_17))
        FROM 
            two_nf_schools
        WHERE 
            frpm__national_school_lunch_program_provision_status = 'Locally Funded'
    )
    AND frpm__national_school_lunch_program_provision_status = 'Locally Funded';
```

### Q31 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a redundant DISTINCT ahead of ORDER BY ... LIMIT 9,2, collapsing duplicate ratio values before pagination and changing which two rows the OFFSET/LIMIT returns versus gold's row-level pagination.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT frpm__percent_eligible_free_k12
FROM two_nf_schools
ORDER BY frpm__enrollment_k12 DESC
LIMIT 9, 2;
```

### Q32 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `percent_eligible_free_or_reduced_price_meal_k12` without the frpm__ prefix, causing a 'no such column' error.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    percent_eligible_free_or_reduced_price_meal_k12
FROM 
    two_nf_schools
WHERE 
    schools__school_ownership_code = 66
ORDER BY 
    free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the satscores__record_type='S' filter inside the max-NumGE1500 subquery, so the ranking can resolve to a district-level aggregate row instead of a school row.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__admin_first_name_1, 
    schools__admin_last_name_1, 
    schools__admin_first_name_2, 
    schools__admin_last_name_2, 
    schools__admin_first_name_3, 
    schools__admin_last_name_3
FROM 
    two_nf_schools
WHERE 
    satscores__county_district_school_code = (
        SELECT 
            satscores__county_district_school_code
        FROM 
            two_nf_schools
        ORDER BY 
            satscores__number_scores_1500_or_above DESC
        LIMIT 1
    )
```

### Q37 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Orders by frpm__percent_eligible_free_or_reduced_price_meal_k12 (FRPM eligibility rate), an unrelated metric, instead of the satscores NumGE1500/NumTstTakr ratio gold ranks by; also drops the tie-preserving `= (SELECT MIN(...))` subquery for a plain ORDER BY/LIMIT 1.

**Gold SQL (original 3NF form):**

```sql
SELECT s.Street, s.City, s.State, s.Zip 
FROM schools s JOIN satscores sat ON s.CDSCode = sat.cds 
WHERE sat.NumTstTakr > 0 AND sat.NumGE1500 IS NOT NULL AND sat.NumTstTakr IS NOT NULL  AND rtype = 'S'
AND CAST(sat.NumGE1500 AS FLOAT) / CAST(sat.NumTstTakr AS FLOAT) =
 (SELECT MIN(CAST(NumGE1500 AS FLOAT) / CAST(NumTstTakr AS FLOAT)) 
 FROM satscores WHERE NumTstTakr > 0 AND NumGE1500 IS NOT NULL AND NumTstTakr IS NOT NULL AND rtype = 'S' )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__Street, 
    schools__City, 
    schools__State, 
    schools__Zip
FROM 
    two_nf_schools
ORDER BY 
    frpm__percent_eligible_free_or_reduced_price_meal_k12 ASC
LIMIT 1;
```

### Q39 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References `two_nf_schools.schools__cdscode`, a hallucinated lowercase name; the real column is schools__county_district_school_code.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(satscores__number_test_takers)
FROM (
    SELECT DISTINCT two_nf_schools.schools__cdscode, satscores__number_test_takers
    FROM two_nf_schools
    WHERE two_nf_schools.schools__County = 'Fresno'
      AND two_nf_schools.schools__open_date BETWEEN '1980-01-01' AND '1980-12-31'
)
```

### Q40 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters satscores__county_name = 'Fresno' instead of the requested District = 'Fresno Unified' -- county is a broader, wrong-grain attribute for this question.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__Phone
FROM two_nf_schools
WHERE satscores__county_name = 'Fresno'
ORDER BY satscores__average_score_reading ASC
LIMIT 1;
```

### Q41 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's RANK() OVER (PARTITION BY county ORDER BY AvgScrRead DESC) top-5-per-county window with an unrelated 'top 5 counties by max score' subquery, producing a different row set; also uses invented Virtual='Yes' instead of 'F'.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__School
FROM two_nf_schools
WHERE schools__Virtual = 'Yes'
AND (schools__County, satscores__average_score_reading) IN (
    SELECT schools__County, MAX(satscores__average_score_reading)
    FROM two_nf_schools
    WHERE schools__Virtual = 'Yes'
    GROUP BY schools__County
    ORDER BY MAX(satscores__average_score_reading) DESC
    LIMIT 5
)
ORDER BY satscores__average_score_reading DESC;
```

### Q46 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects schools__State/satscores__enrollment_grade_12 instead of the requested School name and frpm__enrollment_k12 sort key, and filters educational_option_name='Special School' (not a real domain value) instead of schools__district_ownership_code=31 ('State Special Schools').

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__State, satscores__enrollment_grade_12
FROM two_nf_schools
WHERE schools__educational_option_name = 'Special School'
ORDER BY satscores__enrollment_grade_12 DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `open_date` instead of `schools__open_date`, causing 'no such column: open_date'.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(DISTINCT open_date) AS avg_open_date
FROM two_nf_schools
WHERE schools__County = 'Alameda' AND schools__District = 'Elementary School District' AND strftime('%Y', open_date) = '1980'
GROUP BY strftime('%m', open_date);
```

### Q48 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** 'Merged Unified School District'/'Merged Elementary School District' are not real schools__status_type values (only 'Merged' exists); also restructures gold's two independently-scoped COUNT subqueries (numerator County='Orange', denominator all DOC=52 statewide) into one query sharing County='Orange' across both counts.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN schools__status_type = 'Merged Unified School District' THEN schools__county_district_school_code END) AS REAL) /
       COUNT(DISTINCT CASE WHEN schools__status_type = 'Merged Elementary School District' THEN schools__county_district_school_code END) AS ratio
FROM two_nf_schools
WHERE schools__County = 'Orange';
```

### Q50 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects schools__Street instead of the requested schools__mailing_street (MailStreet); also drops the satscores__record_type='S' filter.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__School, schools__Street
FROM two_nf_schools
ORDER BY satscores__average_score_math DESC
LIMIT 6, 1
```

### Q62 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** frpm__is_charter_school='N' is an invented value (real column is integer 0/1; gold needs 0); also omits the *100 conversion, comparing the 0-1 percent_eligible_free_k12 fraction directly to 0.18 instead of the 0-100 scale gold's expression implies.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT frpm__county_district_school_code)
FROM two_nf_schools
WHERE frpm__county_name = 'Los Angeles'
  AND frpm__is_charter_school = 'N'
  AND frpm__percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters frpm__district_name='Fremont' instead of City='Fremont', and compares the School NAME field to the literal 'State Special School' instead of filtering the EdOpsCode/EdOpsName columns for 'SSS'/'State Special School'; also aggregates COUNT instead of gold's SUM(enrollment_ages_5_17).

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT frpm__school_code) 
FROM two_nf_schools 
WHERE frpm__academic_year = '2014-2015' 
AND frpm__district_name = 'Fremont' 
AND schools__School = 'State Special School';
```

### Q77 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters schools__grade_span_offered (GSoffered) with an invented long-form value 'Kindergarten to 9th grade' instead of the requested schools__grade_span_served (GSserved)='K-9'.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__School, 
    frpm__percent_eligible_free_ages_5_17
FROM 
    two_nf_schools
WHERE 
    schools__County = 'Los Angeles' 
    AND schools__grade_span_offered = 'Kindergarten to 9th grade';
```

### Q79 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters on schools__Charter='Yes' (wrong column and invented value; Charter is integer 0/1) instead of the requested Virtual='F'.

**Gold SQL (original 3NF form):**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT schools__County, COUNT(DISTINCT schools__national_center_for_education_statistics_school_id) AS school_count
FROM two_nf_schools
WHERE schools__County IN ('San Diego', 'Santa Barbara') AND schools__Charter = 'Yes'
GROUP BY schools__County
ORDER BY school_count DESC
LIMIT 1;
```

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Orders by raw Longitude DESC instead of ABS(Longitude) DESC, picking the easternmost (least negative) school instead of the one farthest from the prime meridian.

**Gold SQL (original 3NF form):**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__grade_span_offered 
FROM two_nf_schools 
ORDER BY schools__Longitude DESC 
LIMIT 1;
```

### Q83 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References `schools__CDSCode` (raw PascalCase); the real aliased column is schools__county_district_school_code.

**Gold SQL (original 3NF form):**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT schools__City, COUNT(DISTINCT schools__CDSCode) AS school_count
FROM two_nf_schools
WHERE schools__grade_span_offered = 'Kindergarten to 8th' AND frpm__educational_option_type = 'Multiple Provision Types'
GROUP BY schools__City;
```

### Q85 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Selects the raw 0-1 fraction frpm__percent_eligible_free_k12 without gold's x100 conversion, so values are 100x smaller than gold's percentage scale.

**Gold SQL (original 3NF form):**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT frpm__percent_eligible_free_k12, frpm__district_code
FROM two_nf_schools
WHERE schools__admin_first_name_1 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Replaces schools__school_ownership_code=62 (SOC) with schools__instruction_level_name IN (...) (EILName), an unrelated attribute; drops the DOC=54 filter; and uses City='San Bernardino City Unified' instead of 'San Bernardino'.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    schools__admin_email_1 AS email1, 
    schools__admin_email_2 AS email2, 
    schools__admin_email_3 AS email3
FROM 
    two_nf_schools
WHERE 
    schools__County = 'San Bernardino' 
    AND schools__City = 'San Bernardino City Unified' 
    AND schools__open_date BETWEEN '2009-01-01' AND '2010-12-31' 
    AND schools__instruction_level_name IN ('Intermediate/Middle School', 'Unified School');
```

---

## debit_card_specializing (25 failures)

### Q1471 (simple, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_transactions fans out one customer per transaction row; SUM(CASE...) counts transactions, not distinct customers, so it needs COUNT(DISTINCT CASE WHEN currency=... THEN customer_id END) to reproduce gold's per-customer count.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) / 
       SUM(CASE WHEN customers__currency = 'CZK' THEN 1 ELSE 0 END) AS ratio
FROM two_nf_transactions;
```

### Q1472 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Missing GROUP BY customer_id + SUM(consumption): orders by a single row's raw consumption and picks LIMIT 1, instead of finding the customer whose SUMMED 2012 consumption is lowest.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT customers__customer_id
FROM two_nf_yearmonth
WHERE yearmonth__date LIKE '2012%' AND customers__segment = 'LAM'
ORDER BY yearmonth__consumption ASC
LIMIT 1;
```

### Q1473 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Missing GROUP BY customer_id + SUM(consumption) before averaging: averages raw per-(customer,month) consumption values directly instead of gold's per-customer annual totals; also drops the final /12.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(yearmonth__consumption)
FROM (
    SELECT DISTINCT yearmonth__customer_id, yearmonth__consumption
    FROM two_nf_yearmonth
    WHERE customers__segment = 'SME' AND strftime('%Y', yearmonth__date) = '2013'
)
```

### Q1476 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Misapplies strftime('%Y', ...) to the compact 'YYYYMM' text date column (not a valid ISO date string), instead of gold's SUBSTR(Date,1,4)='2012', so the year filter fails to match.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    SUM(CASE WHEN customers__currency = 'CZK' THEN yearmonth__consumption ELSE 0 END) -
    SUM(CASE WHEN customers__currency = 'EUR' THEN yearmonth__consumption ELSE 0 END) AS consumption_difference
FROM 
    two_nf_yearmonth
WHERE 
    strftime('%Y', yearmonth__date) = '2012';
```

### Q1479 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Groups by the full yearmonth__date (YYYYMM) instead of just the year prefix SUBSTR(date,1,4), so it picks the single highest-consumption month rather than the highest-consumption year.

**Gold SQL (original 3NF form):**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT yearmonth__date 
FROM two_nf_yearmonth 
WHERE customers__currency = 'CZK' 
GROUP BY yearmonth__date 
ORDER BY SUM(yearmonth__consumption) DESC 
LIMIT 1;
```

### Q1480 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Missing GROUP BY SUBSTR(date,5,2) with SUM(consumption): orders raw rows by consumption DESC and returns the full date of the single highest row instead of the month with the highest total.

**Gold SQL (original 3NF form):**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT yearmonth__date
FROM two_nf_yearmonth
WHERE customers__segment = 'SME' AND yearmonth__date LIKE '2013%'
ORDER BY yearmonth__consumption DESC
LIMIT 1
```

### Q1481 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Does not reproduce gold's CTE chain that isolates, per segment, the customer with the minimum total 2013 CZK consumption and reports their average; instead computes a blanket segment-wide AVG(consumption) across all customers/months.

**Gold SQL (original 3NF form):**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (SELECT AVG(yearmonth__consumption) 
     FROM two_nf_yearmonth 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'SME') -
    (SELECT AVG(yearmonth__consumption) 
     FROM two_nf_yearmonth 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'LAM') AS diff_sme_lam,

    (SELECT AVG(yearmonth__consumption) 
     FROM two_nf_yearmonth 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'LAM') -
    (SELECT AVG(yearmonth__consumption) 
     FROM two_nf_yearmonth 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'KAM') AS diff_lam_kam,

    (SELECT AVG(yearmonth__consumption) 
     FROM two_nf_yearmonth 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'KAM') -
    (SELECT AVG(yearmonth__consumption) 
     FROM two_nf_yearmonth 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'SME') AS diff_kam_sme;
```

### Q1482 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a GROUP BY customers__segment that gold doesn't have (gold computes three IIF-conditioned aggregates side-by-side in one row), producing one row per segment instead of a single row with 3 percentage-change columns.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    customers__segment,
    ((SUM(CASE WHEN STRFTIME('%Y', yearmonth__date) = '2013' THEN yearmonth__consumption ELSE 0 END) -
      SUM(CASE WHEN STRFTIME('%Y', yearmonth__date) = '2012' THEN yearmonth__consumption ELSE 0 END)) /
     SUM(CASE WHEN STRFTIME('%Y', yearmonth__date) = '2012' THEN yearmonth__consumption ELSE 0 END)) * 100 AS percentage_change
FROM 
    two_nf_yearmonth
WHERE 
    customers__currency = 'EUR' AND
    customers__segment IN ('SME', 'LAM', 'KAM')
GROUP BY 
    customers__segment;
```

### Q1483 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Applies an ISO 'YYYY-MM-DD' BETWEEN range to the compact 'YYYYMM' text date column, breaking the lexicographic comparison gold's SUBSTR-free direct compact-string BETWEEN relies on.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT SUM(yearmonth__consumption) 
FROM two_nf_yearmonth 
WHERE yearmonth__customer_id = 6 
AND yearmonth__date BETWEEN '2013-08-01' AND '2013-11-30';
```

### Q1484 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic'/'Slovakia' are invented values (real codes are 'CZE'/'SVK'), and 'discount' (lowercase) instead of the real value 'Discount'.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    COUNT(DISTINCT CASE WHEN gasstations__country = 'Czech Republic' THEN gasstations__gas_station_id END) -
    COUNT(DISTINCT CASE WHEN gasstations__country = 'Slovakia' THEN gasstations__gas_station_id END) AS difference
FROM 
    two_nf_transactions
WHERE 
    gasstations__segment = 'discount';
```

### Q1486 (simple, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_transactions (one row per transaction) instead of a customer-grain source, so SUM(CASE...) counts transactions per currency rather than distinct customers; COUNT(DISTINCT CASE WHEN currency=... THEN customer_id END) would reproduce gold's customer-count difference.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    SUM(CASE WHEN customers__currency = 'CZK' THEN 1 ELSE 0 END) - 
    SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS difference
FROM 
    two_nf_transactions
WHERE 
    customers__segment = 'SME';
```

### Q1490 (moderate, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** Numerator SUM(CASE WHEN consumption>46.73...) counts qualifying yearmonth rows rather than distinct customers; needs COUNT(DISTINCT CASE WHEN consumption>46.73 THEN customer_id END) to match gold's per-customer percentage.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN yearmonth__consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT yearmonth__customer_id) 
FROM two_nf_yearmonth 
WHERE customers__segment = 'LAM';
```

### Q1493 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses LIKE '2012-02-%' (ISO-dashed pattern) against the compact 'YYYYMM' yearmonth__date column (e.g. '201202'), which never matches; gold compares the compact string directly.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN yearmonth__consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT yearmonth__customer_id) 
FROM two_nf_yearmonth 
WHERE yearmonth__date LIKE '2012-02-%';
```

### Q1498 (simple, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Drops GROUP BY SUBSTR(date,5,2) entirely and returns MAX(consumption) over ungrouped rows instead of finding the month with the highest SUM(consumption); also misapplies strftime() to the compact-format date column.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MAX(yearmonth__consumption)
FROM two_nf_yearmonth
WHERE strftime('%Y', yearmonth__date) = '2012';
```

### Q1505 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** currency='euro' is not a real domain value; the real value is 'EUR'.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT yearmonth__customer_id)
FROM two_nf_yearmonth
WHERE customers__currency = 'euro' AND yearmonth__consumption > 1000;
```

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' is an invented value; the real domain code is 'CZE'.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT products__description 
FROM two_nf_transactions 
WHERE gasstations__country = 'Czech Republic';
```

### Q1507 (simple, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_transactions' FULL OUTER JOIN chain preserves an orphan gasstations row (a chain-11 station with zero transactions) as a row with NULL transactions_1k__time; gold's INNER JOIN excludes it, and no DISTINCT-only repair removes this extra NULL row (needs an explicit transaction-id NOT NULL guard) -- verified empirically: predicted returns 3 distinct Time values (incl. one NULL) vs gold's 2.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.Time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T2.ChainID = 11
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT transactions_1k__time 
FROM two_nf_transactions 
WHERE gasstations__chain_id = 11;
```

### Q1509 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' is an invented value; the real domain code is 'CZE'.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(t.`TransactionID`)
FROM `transactions_1k` AS t
JOIN `gasstations` AS g
  ON t.`GasStationID` = g.`GasStationID`
WHERE g.`Country` = 'CZE'
  AND DATE(t.`Date`) > '2012-01-01';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT transactions_1k__transaction_id) 
FROM two_nf_transactions 
WHERE gasstations__country = 'Czech Republic' 
AND transactions_1k__date > '2012-01-01';
```

### Q1524 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects customers__currency instead of the requested gasstations__country, and filters transactions_1k__amount=548.4 instead of transactions_1k__price=548.4.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT customers__currency 
FROM two_nf_transactions 
WHERE transactions_1k__date = '2012-08-24' AND transactions_1k__amount = 548.4;
```

### Q1525 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses the two_nf_yearmonth cluster (monthly 'YYYYMM' grain) instead of two_nf_transactions, so the daily date filter '2012-08-25' can never match yearmonth's compact monthly-format date column.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT yearmonth__customer_id) 
FROM two_nf_yearmonth 
WHERE yearmonth__date = '2012-08-25';
```

### Q1526 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** The inner subquery filters transactions_1k__amount=634.8 instead of the requested transactions_1k__price=634.8, resolving to the wrong customer; also the outer 2012 range is truncated to Aug25-Dec31 instead of gold's full calendar year.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    (SUM(CASE WHEN yearmonth__date BETWEEN '2012-08-25' AND '2012-12-31' THEN yearmonth__consumption ELSE 0 END) -
     SUM(CASE WHEN yearmonth__date BETWEEN '2013-01-01' AND '2013-12-31' THEN yearmonth__consumption ELSE 0 END)) /
    SUM(CASE WHEN yearmonth__date BETWEEN '2012-08-25' AND '2012-12-31' THEN yearmonth__consumption ELSE 0 END) AS consumption_decrease_rate
FROM 
    two_nf_yearmonth
WHERE 
    yearmonth__customer_id = (
        SELECT DISTINCT transactions_1k__customer_id
        FROM two_nf_transactions
        WHERE transactions_1k__date = '2012-08-25' AND transactions_1k__amount = 634.8
    );
```

### Q1528 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Substitutes customers__segment (SME/LAM/KAM) for gasstations__segment (Premium/Discount/...) and a customer count for a gas-station count -- conflates gas-station segment with customer segment throughout.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CAST(SUM(CASE WHEN customers__segment = 'premium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customers__customer_id) AS percentage_premium
FROM 
    two_nf_transactions
WHERE 
    gasstations__country = 'SVK';
```

### Q1529 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `amount`/`date` instead of `transactions_1k__amount`/`transactions_1k__date`, causing 'no such column: amount'.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    SUM(amount) AS total_spent,
    SUM(CASE WHEN date LIKE '2012-08%' THEN amount ELSE 0 END) AS august_2012_spent
FROM 
    two_nf_transactions
WHERE 
    transactions_1k__customer_id = 38508;
```

### Q1531 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** JOINs a standalone `customers` table that doesn't exist in the L2 database (customers is already merged into two_nf_transactions as customers__* columns), causing 'no such table: customers'.

**Gold SQL (original 3NF form):**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    t.transactions_1k__customer_id,
    c.customers__currency,
    AVG(t.transactions_1k__price) AS avg_price_per_item
FROM 
    two_nf_transactions t
JOIN 
    customers c ON t.transactions_1k__customer_id = c.customers__customer_id
GROUP BY 
    t.transactions_1k__customer_id, c.customers__currency
ORDER BY 
    SUM(t.transactions_1k__amount) DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the Price/Amount ratio computation, filtering raw transactions_1k__amount > 29.00 instead of (price/amount) > 29.00; also mis-applies a dashed-date LIKE pattern to yearmonth's compact 'YYYYMM' date column.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT t.transactions_1k__customer_id, y.yearmonth__consumption
FROM two_nf_transactions t
JOIN two_nf_yearmonth y ON t.transactions_1k__customer_id = y.yearmonth__customer_id
WHERE t.transactions_1k__product_id = 5
AND t.transactions_1k__amount > 29.00
AND y.yearmonth__date LIKE '2012-08-%';
```

---

## european_football_2 (40 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Match__season = 2016 does not match the real season format '2015/2016'.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT League__name
FROM two_nf_match
WHERE Match__season = 2016
GROUP BY League__name
ORDER BY SUM(Match__home_team_goals + Match__away_team_goals) DESC
LIMIT 1;
```

### Q1028 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'League' table; League data is already embedded in two_nf_match as League__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT team_away__team_long_name
FROM two_nf_match
WHERE Match__league_id = (
    SELECT League__id
    FROM two_nf_match
    JOIN League ON two_nf_match.Match__league_id = League.League__id
    WHERE League__name = 'Scotland Premier League'
) AND Match__season = 2010 AND Match__away_team_goals > Match__home_team_goals
GROUP BY team_away__team_long_name
ORDER BY COUNT(*) DESC
LIMIT 1;
```

### Q1029 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a redundant DISTINCT before ORDER BY/LIMIT 4, which can change which specific 4 rows are returned versus gold's non-deduped result if multiple Team_Attributes rows share the same top buildUpPlaySpeed value.

**Gold SQL (original 3NF form):**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_speed
FROM two_nf_team
ORDER BY Team_Attributes__buildup_play_speed DESC
LIMIT 4;
```

### Q1030 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Match__season = 2016 does not match the real season format '2015/2016'.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT League__name
FROM two_nf_match
WHERE Match__season = 2016 AND Match__home_team_goals = Match__away_team_goals
GROUP BY League__name
ORDER BY COUNT(DISTINCT Match__id) DESC
LIMIT 1;
```

### Q1031 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Reverses the subtraction order (birthday_year - current_year instead of gold's current_year - birthday_year), producing a negative value instead of a positive age; also drops the day-of-year correction CASE WHEN gold applies.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T2.Birthday) - CASE
    WHEN strftime('%m-%d','now') < strftime('%m-%d', Birthday) THEN 1
    ELSE 0
  END AS age FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE STRFTIME('%Y',t1."date") >= '2013' AND STRFTIME('%Y',t1."date") <= '2015' AND t1.sprint_speed >= 97
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT strftime('%Y', Player__birthday) - strftime('%Y', 'now') AS age
FROM two_nf_player
WHERE Player_Attributes__sprint_speed >= 97
AND Player_Attributes__date BETWEEN '2013-01-01' AND '2015-12-31';
```

### Q1032 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'League' table; League data is already embedded in two_nf_match as League__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT League__name, COUNT(DISTINCT Match__id) AS match_count
FROM two_nf_match
JOIN League ON two_nf_match.Match__league_id = League.League__id
GROUP BY League__name
ORDER BY match_count DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses BETWEEN 50 AND 60 (inclusive) instead of gold's exclusive '> 50 AND < 60', incorrectly including teams with buildUpPlaySpeed exactly 50 or 60.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Team_Attributes__team_fifa_api_id
FROM two_nf_team
WHERE Team_Attributes__buildup_play_speed BETWEEN 50 AND 60;
```

### Q1036 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'Team_Attributes' table; that data is already embedded in two_nf_team as Team_Attributes__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT team_home__team_long_name
FROM two_nf_match
JOIN two_nf_team ON two_nf_match.Match__home_team_api_id = two_nf_team.Team__team_api_id
JOIN Team_Attributes ON two_nf_team.Team__team_api_id = Team_Attributes.team_api_id
WHERE Team_Attributes.date LIKE '2012%'
AND Team_Attributes.buildup_play_passing > (
    SELECT AVG(buildup_play_passing)
    FROM Team_Attributes
    WHERE date LIKE '2012%'
);
```

### Q1037 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `preferred_foot` instead of `Player_Attributes__preferred_foot`.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT player_api_id) 
FROM two_nf_player 
WHERE strftime('%Y', birthday) BETWEEN '1987' AND '1992';
```

### Q1039 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `long_shots` instead of `Player_Attributes__long_shots`.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(long_shots)
FROM (
    SELECT DISTINCT Player_Attributes__id, long_shots
    FROM two_nf_player
    WHERE Player__player_name = 'Ahmed Samir Farag'
)
```

### Q1040 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'Player_Attributes' table inside the correlated subquery; that data is already embedded in two_nf_player.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player__player_name
FROM two_nf_player
WHERE Player__height > 180
ORDER BY (
  SELECT AVG(Player_Attributes__heading_accuracy)
  FROM two_nf_player AS p
  JOIN Player_Attributes ON p.Player__player_api_id = Player_Attributes.player_api_id
  WHERE p.Player__player_api_id = two_nf_player.Player__player_api_id
) DESC
LIMIT 10;
```

### Q1058 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `height` instead of `Player__height`.

**Gold SQL (original 3NF form):**

```sql
SELECT A FROM (SELECT AVG(finishing) result, 'highest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MAX(height) FROM Player) UNION SELECT AVG(finishing) result, 'shortest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MIN(height) FROM Player)) tmp ORDER BY result DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CASE 
        WHEN avg_highest > avg_shortest THEN 'highest'
        ELSE 'shortest'
    END AS answer
FROM (
    SELECT 
        AVG(Player_Attributes__finishing) AS avg_highest
    FROM 
        two_nf_player
    WHERE 
        Player__height = (SELECT MAX(height) FROM two_nf_player)
) AS highest_avg
JOIN (
    SELECT 
        AVG(Player_Attributes__finishing) AS avg_shortest
    FROM 
        two_nf_player
    WHERE 
        Player__height = (SELECT MIN(height) FROM two_nf_player)
) AS shortest_avg
ON 1=1;
```

### Q1068 (moderate, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT on (Player__id, overall_rating) that collapses repeated identical (player, rating) pairs across multiple qualifying dates, which gold's plain (non-deduped) JOIN counts separately -- verified empirically: gold AVG=68.945 vs predicted's 68.012.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(t2.overall_rating) AS avg_rating
FROM `Player` AS t1
JOIN `Player_Attributes` AS t2 ON t1.player_api_id = t2.player_api_id
WHERE t1.height > 170
  AND strftime('%Y', t2.`date`) BETWEEN '2010' AND '2015';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(Player_Attributes__overall_rating)
FROM (
    SELECT DISTINCT Player__id, Player_Attributes__overall_rating
    FROM two_nf_player
    WHERE Player__height > 170 AND Player_Attributes__date BETWEEN '2010-01-01' AND '2015-12-31'
)
```

### Q1078 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds an extra Player__birthday column beyond gold's single player_name column.

**Gold SQL (original 3NF form):**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT Player__player_name, Player__birthday
FROM two_nf_player
WHERE Player__player_name IN ('Aaron Lennon', 'Abdelaziz Barrada')
ORDER BY Player__birthday ASC
LIMIT 1;
```

### Q1080 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attacking_work_rate='high' instead of the requested 'low'.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Player__id) 
FROM two_nf_player 
WHERE Player_Attributes__preferred_foot = 'left' AND Player_Attributes__attacking_work_rate = 'high';
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extraneous attacking_work_rate='High' condition not present in gold, and uses wrong-case 'High' instead of the real lowercase 'high' for defensive_work_rate too.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Player__id)
FROM two_nf_player
WHERE strftime('%Y', Player__birthday) < '1986'
AND Player_Attributes__attacking_work_rate = 'High'
AND Player_Attributes__defensive_work_rate = 'High';
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's tie-preserving `HAVING COUNT(t2.id) = (SELECT MAX(match_count)...)` comparison into `ORDER BY COUNT(...) DESC LIMIT 1`, which would silently drop any tied leagues.

**Gold SQL (original 3NF form):**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT League__name
FROM two_nf_match
WHERE Match__season = '2008/2009'
GROUP BY League__name
ORDER BY COUNT(DISTINCT Match__id) DESC
LIMIT 1;
```

### Q1094 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `overall_rating` instead of `Player_Attributes__overall_rating`; also drops gold's `ORDER BY date DESC LIMIT 1` per-player 'most recent rating' selection entirely.

**Gold SQL (original 3NF form):**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
  ((SELECT overall_rating FROM two_nf_player WHERE player_name = 'Ariel Borysiuk') - 
   (SELECT overall_rating FROM two_nf_player WHERE player_name = 'Paulin Puel')) * 100.0 / 
  (SELECT overall_rating FROM two_nf_player WHERE player_name = 'Paulin Puel') AS percentage_difference;
```

### Q1098 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `team_long_name` instead of `Team__team_long_name`.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MAX(Team_Attributes__chance_creation_passing), Team_Attributes__chance_creation_passing_class
FROM two_nf_team
WHERE team_long_name = 'Ajax';
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Compares Player_Attributes__date (stored as 'YYYY-MM-DD HH:MM:SS') directly to the date-only string '2016-06-23' instead of gold's SUBSTR(date,1,10) prefix-extraction approach, so it never matches.

**Gold SQL (original 3NF form):**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT Player__player_name
FROM two_nf_player
WHERE Player_Attributes__overall_rating = 77
  AND Player_Attributes__date = '2016-06-23'
ORDER BY Player__birthday ASC
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Compares Player_Attributes__date directly to a date-only string instead of matching just the date portion of the stored datetime, as gold's SUBSTR(date,1,10) does.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player_Attributes__overall_rating
FROM two_nf_player
WHERE Player__player_name = 'Aaron Mooy'
AND Player_Attributes__date = '2016-02-04';
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Compares Player_Attributes__date directly (exact equals) to a date-only string instead of gold's LIKE '2015-05-01%' prefix match against the datetime column.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player_Attributes__attacking_work_rate
FROM two_nf_player
WHERE Player__player_name = 'Francesco Migliore'
AND Player_Attributes__date = '2015-05-01';
```

### Q1107 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Routes through two_nf_match's home_player_1_api_id link instead of directly using two_nf_player's own Player_Attributes__crossing/date columns -- an unrelated and incomplete way to find the player (misses them entirely if never listed as home_player_1).

**Gold SQL (original 3NF form):**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Match__date
FROM two_nf_match
JOIN two_nf_player ON two_nf_match.Match__home_player_1_api_id = two_nf_player.Player__player_api_id
WHERE two_nf_player.Player__player_name = 'Kevin Constant'
ORDER BY two_nf_player.Player_Attributes__crossing DESC
LIMIT 1;
```

### Q1110 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'Team_Attributes' table; that data is already embedded in two_nf_team.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_passing_class 
FROM two_nf_team 
JOIN Team_Attributes ON two_nf_team.Team__id = Team_Attributes.Team_Attributes__team_api_id 
WHERE two_nf_team.team_long_name = 'FC Lorient' AND Team_Attributes.date = '2010-02-22';
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact-matches a date-only string ('2015-09-10') against the datetime-typed Team_Attributes__date column instead of gold's LIKE '2015-09-10%' prefix match.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Team_Attributes__defence_aggression_class 
FROM two_nf_team 
WHERE Team__team_long_name = 'Hannover 96' 
AND Team_Attributes__date = '2015-09-10';
```

### Q1114 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses BETWEEN with a date-only upper bound ('2016-04-21') against the datetime-typed date column, which excludes records on the exact boundary date (since 'YYYY-MM-DD HH:MM:SS' sorts after the bare date string), unlike gold's SUBSTR(date,1,10) date-only extraction.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(Player_Attributes__overall_rating)
FROM two_nf_player
WHERE Player__player_name = 'Marko Arnautovic'
AND Player_Attributes__date BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `overall_rating` instead of `Player_Attributes__overall_rating`.

**Gold SQL (original 3NF form):**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
  ((donovan.overall_rating - bowery.overall_rating) * 100.0 / bowery.overall_rating) AS percentage_difference
FROM 
  two_nf_player AS donovan
JOIN 
  two_nf_player AS bowery
ON 
  donovan.Player__player_name = 'Landon Donovan' 
  AND bowery.Player__player_name = 'Jordan Bowery'
WHERE 
  donovan.Player_Attributes__date = '2013-07-12' 
  AND bowery.Player_Attributes__date = '2013-07-12';
```

### Q1116 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's `DENSE_RANK() OVER (ORDER BY height DESC) WHERE rank=1` entirely, returning ALL players ordered by height (no LIMIT) instead of just the tallest (possibly tied) ones.

**Gold SQL (original 3NF form):**

```sql
SELECT player_name FROM (SELECT player_name, height, DENSE_RANK() OVER (ORDER BY height DESC) as rank FROM Player) WHERE rank = 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player__player_name 
FROM two_nf_player 
ORDER BY Player__height DESC;
```

### Q1122 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Orders by Player_Attributes__strength instead of the requested overall_rating; also collapses gold's exact-max-match (which could return ties) into an arbitrary LIMIT 1.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT Player__player_name 
FROM two_nf_player 
ORDER BY Player_Attributes__strength DESC 
LIMIT 1;
```

### Q1124 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_match's player position slots (home/away_player_1..11) entirely, an unrelated table/concept, instead of the requested Player_Attributes.attacking_work_rate='high' filter on two_nf_player.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player__player_name
FROM two_nf_match
WHERE Match__home_player_1_api_id IN (
    SELECT Match__home_player_1_api_id
    FROM two_nf_match
    WHERE Match__home_player_1_api_id IS NOT NULL
    GROUP BY Match__home_player_1_api_id
    HAVING COUNT(DISTINCT Match__home_player_1_api_id) > 1
)
OR Match__home_player_2_api_id IN (
    SELECT Match__home_player_2_api_id
    FROM two_nf_match
    WHERE Match__home_player_2_api_id IS NOT NULL
    GROUP BY Match__home_player_2_api_id
    HAVING COUNT(DISTINCT Match__home_player_2_api_id) > 1
)
OR Match__home_player_3_api_id IN (
    SELECT Match__home_player_3_api_id
    FROM two_nf_match
    WHERE Match__home_player_3_api_id IS NOT NULL
    GROUP BY Match__home_player_3_api_id
    HAVING COUNT(DISTINCT Match__home_player_3_api_id) > 1
)
OR Match__home_player_4_api_id IN (
    SELECT Match__home_player_4_api_id
    FROM two_nf_match
    WHERE Match__home_player_4_api_id IS NOT NULL
    GROUP BY Match__home_player_4_api_id
    HAVING COUNT(DISTINCT Match__home_player_4_api_id) > 1
)
OR Match__home_player_5_api_id IN (
    SELECT Match__home_player_5_api_id
    FROM two_nf_match
    WHERE Match__home_player_5_api_id IS NOT NULL
    GROUP BY Match__home_player_5_api_id
    HAVING COUNT(DISTINCT Match__home_player_5_api_id) > 1
)
OR Match__home_player_6_api_id IN (
    SELECT Match__home_player_6_api_id
    FROM two_nf_match
    WHERE Match__home_player_6_api_id IS NOT NULL
    GROUP BY Match__home_player_6_api_id
    HAVING COUNT(DISTINCT Match__home_player_6_api_id) > 1
)
OR Match__home_player_7_api_id IN (
    SELECT Match__home_player_7_api_id
    FROM two_nf_match
    WHERE Match__home_player_7_api_id IS NOT NULL
    GROUP BY Match__home_player_7_api_id
    HAVING COUNT(DISTINCT Match__home_player_7_api_id) > 1
)
OR Match__home_player_8_api_id IN (
    SELECT Match__home_player_8_api_id
    FROM two_nf_match
    WHERE Match__home_player_8_api_id IS NOT NULL
    GROUP BY Match__home_player_8_api_id
    HAVING COUNT(DISTINCT Match__home_player_8_api_id) > 1
)
OR Match__home_player_9_api_id IN (
    SELECT Match__home_player_9_api_id
    FROM two_nf_match
    WHERE Match__home_player_9_api_id IS NOT NULL
    GROUP BY Match__home_player_9_api_id
    HAVING COUNT(DISTINCT Match__home_player_9_api_id) > 1
)
OR Match__home_player_10_api_id IN (
    SELECT Match__home_player_10_api_id
    FROM two_nf_match
    WHERE Match__home_player_10_api_id IS NOT NULL
    GROUP BY Match__home_player_10_api_id
    HAVING COUNT(DISTINCT Match__home_player_10_api_id) > 1
)
OR Match__home_player_11_api_id IN (
    SELECT Match__home_player_11_api_id
    FROM two_nf_match
    WHERE Match__home_player_11_api_id IS NOT NULL
    GROUP BY Match__home_player_11_api_id
    HAVING COUNT(DISTINCT Match__home_player_11_api_id) > 1
)
OR Match__away_player_1_api_id IN (
    SELECT Match__away_player_1_api_id
    FROM two_nf_match
    WHERE Match__away_player_1_api_id IS NOT NULL
    GROUP BY Match__away_player_1_api_id
    HAVING COUNT(DISTINCT Match__away_player_1_api_id) > 1
)
OR Match__away_player_2_api_id IN (
    SELECT Match__away_player_2_api_id
    FROM two_nf_match
    WHERE Match__away_player_2_api_id IS NOT NULL
    GROUP BY Match__away_player_2_api_id
    HAVING COUNT(DISTINCT Match__away_player_2_api_id) > 1
)
OR Match__away_player_3_api_id IN (
    SELECT Match__away_player_3_api_id
    FROM two_nf_match
    WHERE Match__away_player_3_api_id IS NOT NULL
    GROUP BY Match__away_player_3_api_id
    HAVING COUNT(DISTINCT Match__away_player_3_api_id) > 1
)
OR Match__away_player_4_api_id IN (
    SELECT Match__away_player_4_api_id
    FROM two_nf_match
    WHERE Match__away_player_4_api_id IS NOT NULL
    GROUP BY Match__away_player_4_api_id
    HAVING COUNT(DISTINCT Match__away_player_4_api_id) > 1
)
OR Match__away_player_5_api_id IN (
    SELECT Match__away_player_5_api_id
    FROM two_nf_match
    WHERE Match__away_player_5_api_id IS NOT NULL
    GROUP BY Match__away_player_5_api_id
    HAVING COUNT(DISTINCT Match__away_player_5_api_id) > 1
)
OR Match__away_player_6_api_id IN (
    SELECT Match__away_player_6_api_id
    FROM two_nf_match
    WHERE Match__away_player_6_api_id IS NOT NULL
    GROUP BY Match__away_player_6_api_id
    HAVING COUNT(DISTINCT Match__away_player_6_api_id) > 1
)
OR Match__away_player_7_api_id IN (
    SELECT Match__away_player_7_api_id
    FROM two_nf_match
    WHERE Match__away_player_7_api_id IS NOT NULL
    GROUP BY Match__away_player_7_api_id
    HAVING COUNT(DISTINCT Match__away_player_7_api_id) > 1
)
OR Match__away_player_8_api_id IN (
    SELECT Match__away_player_8_api_id
    FROM two_nf_match
    WHERE Match__away_player_8_api_id IS NOT NULL
    GROUP BY Match__away_player_8_api_id
    HAVING COUNT(DISTINCT Match__away_player_8_api_id) > 1
)
OR Match__away_player_9_api_id IN (
    SELECT Match__away_player_9_api_id
    FROM two_nf_match
    WHERE Match__away_player_9_api_id IS NOT NULL
    GROUP BY Match__away_player_9_api_id
    HAVING COUNT(DISTINCT Match__away_player_9_api_id) > 1
)
OR Match__away_player_10_api_id IN (
    SELECT Match__away_player_10_api_id
    FROM two_nf_match
    WHERE Match__away_player_10_api_id IS NOT NULL
    GROUP BY Match__away_player_10_api_id
    HAVING COUNT(DISTINCT Match__away_player_10_api_id) > 1
)
OR Match__away_player_11_api_id IN (
    SELECT Match__away_player_11_api_id
    FROM two_nf_match
    WHERE Match__away_player_11_api_id IS NOT NULL
    GROUP BY Match__away_player_11_api_id
    HAVING COUNT(DISTINCT Match__away_player_11_api_id) > 1
);
```

### Q1130 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** chance_creation_passing_class belongs to Team_Attributes (via two_nf_team), not to Match at all; two_nf_match has no such column.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT team_home__team_short_name 
FROM two_nf_match 
WHERE Match__chance_creation_passing_class = 'Safe'
UNION
SELECT DISTINCT team_away__team_short_name 
FROM two_nf_match 
WHERE Match__chance_creation_passing_class = 'Safe';
```

### Q1134 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Hallucinates `Player_Attributes__jumping_6`/`Player_Attributes__jumping_23` (appending the id as a suffix); the real approach needs `Player_Attributes__jumping` filtered/conditioned by `Player_Attributes__id`.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player_Attributes__jumping_6 - Player_Attributes__jumping_23 AS jumping_difference
FROM two_nf_player;
```

### Q1135 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `preferred_foot`/`potential` instead of `Player_Attributes__preferred_foot`/`Player_Attributes__potential`.

**Gold SQL (original 3NF form):**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player_Attributes__id
FROM two_nf_player
WHERE preferred_foot = 'right'
ORDER BY potential ASC
LIMIT 4;
```

### Q1136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extraneous attacking_work_rate='high' condition not present in gold.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Player__id) 
FROM two_nf_player 
WHERE Player_Attributes__crossing = (
    SELECT MAX(Player_Attributes__crossing) 
    FROM two_nf_player
) 
AND Player_Attributes__preferred_foot = 'left' 
AND Player_Attributes__attacking_work_rate = 'high';
```

### Q1139 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** League__name = 'Belgian Jupiler League' is a mistranslated/invented value; the real value is 'Belgium Jupiler League'.

**Gold SQL (original 3NF form):**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    Match__home_team_goals, 
    Match__away_team_goals 
FROM 
    two_nf_match 
WHERE 
    Match__date = '2008-09-24' 
    AND League__name = 'Belgian Jupiler League';
```

### Q1141 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `team_long_name` instead of `Team__team_long_name`.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_speed_class 
FROM two_nf_team 
WHERE team_long_name = 'KSV Cercle Brugge';
```

### Q1144 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT that collapses gold's repeated (finishing, curve) value combinations (the heaviest player(s) have multiple Player_Attributes records over time, some sharing identical values) down to unique combos only -- verified empirically.

**Gold SQL (original 3NF form):**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player_Attributes__finishing, Player_Attributes__curve
FROM two_nf_player
WHERE Player__weight = (SELECT MAX(Player__weight) FROM two_nf_player);
```

### Q1145 (simple, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'League' table; League data is already embedded in two_nf_match as League__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT League__name, COUNT(DISTINCT Match__id) AS game_count
FROM two_nf_match
JOIN League ON two_nf_match.Match__league_id = League.League__id
WHERE Match__season = '2015-2016'
GROUP BY League__name
ORDER BY game_count DESC
LIMIT 4;
```

### Q1147 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Orders by Player_Attributes__strength instead of the requested overall_rating; also collapses gold's exact-max-match into an arbitrary LIMIT 1.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Player__player_name 
FROM two_nf_player 
ORDER BY Player_Attributes__strength DESC 
LIMIT 1;
```

### Q1148 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `height` instead of `Player__height`.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN height < 180 AND Player_Attributes__strength > 70 THEN Player__id END) AS REAL) * 100 / COUNT(DISTINCT Player__id) 
FROM two_nf_player;
```

---

## financial (28 failures)

### Q89 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_district' cluster table; district data for two_nf_trans is already embedded as district__* columns (via account's district), so no such join target exists.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT trans__account_id)
FROM two_nf_trans
JOIN two_nf_account ON trans__account_id = account__account_id
JOIN two_nf_district ON account__district_id = district__district_id
WHERE trans__transaction_type_code = 'issuance' AND district__region = 'East Bohemia';
```

### Q92 (simple, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins nonexistent standalone 'client' and 'district' tables; client+district data is already embedded together in two_nf_disp (client__gender, district__average_salary), the only cluster where they co-occur.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T2.district_id)  FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' AND T2.A11 BETWEEN 6000 AND 10000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT district__district_id) 
FROM two_nf_disp 
JOIN client ON two_nf_disp.disp__client_id = client.client_id 
JOIN district ON two_nf_disp.district_id = district.district_id 
WHERE client.gender = 'F' AND district.average_salary BETWEEN 6000 AND 10000;
```

### Q93 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_client' cluster table; client/district data for this question is only available via two_nf_disp's client__*/district__* columns, not a standalone client cluster.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT client__client_id)
FROM two_nf_disp
JOIN two_nf_client ON two_nf_disp.client_id = two_nf_client.client_id
JOIN two_nf_district ON two_nf_disp.district_id = two_nf_district.district_id
WHERE two_nf_client.gender = 'M'
  AND two_nf_district.region = 'North Bohemia'
  AND two_nf_district.average_salary > 8000;
```

### Q94 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'client' table; client data is only available via two_nf_disp's client__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (SELECT account__account_id 
     FROM two_nf_disp 
     JOIN client ON two_nf_disp.disp__client_id = client.client_id 
     WHERE client.gender = 'F' 
     ORDER BY client.birth_date ASC 
     LIMIT 1) AS oldest_female_client_account,
    (SELECT MAX(district__average_salary) - MIN(district__average_salary) 
     FROM two_nf_account) AS salary_gap
```

### Q95 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'client' table; client data is only available via two_nf_disp's client__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT account__account_id
FROM two_nf_disp
JOIN client ON two_nf_disp.disp__client_id = client.client_id
JOIN account ON two_nf_disp.disp__account_id = account.account_id
JOIN district ON account.account__district_id = district.district_id
ORDER BY client.birth_date ASC, district.average_salary DESC
LIMIT 1
```

### Q98 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `l.date` on the two_nf_loan alias; the real column is `loan__date`.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT t.account__account_id
FROM two_nf_loan l
JOIN two_nf_account t ON l.loan__account_id = t.account__account_id
WHERE l.date LIKE '1997%'
AND t.statement_frequency = 'weekly'
ORDER BY l.amount ASC
LIMIT 1;
```

### Q99 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** The MAX(loan__amount) subquery is scoped only to loan__duration_months>12, without also restricting to accounts whose date falls in 1993, so it can resolve to a different (wrong) account than gold's ORDER BY amount DESC LIMIT 1 over the correctly year-scoped join -- verified empirically: predicted returns 0 rows vs gold's single row (account 10451).

**Gold SQL (original 3NF form):**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT trans__account_id
FROM two_nf_trans
WHERE trans__account_id IN (
    SELECT loan__account_id
    FROM two_nf_loan
    WHERE loan__duration_months > 12
    AND loan__amount = (
        SELECT MAX(loan__amount)
        FROM two_nf_loan
        WHERE loan__duration_months > 12
    )
)
AND strftime('%Y', account__date) = '1993';
```

### Q100 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'client' table; client/district data is only available via two_nf_disp's client__*/district__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT disp__client_id)
FROM two_nf_disp
JOIN client ON two_nf_disp.disp__client_id = client.client_id
JOIN district ON two_nf_disp.client__district_id = district.district_id
WHERE client.gender = 'F'
AND client.birth_date < '1950-01-01'
AND district.district_name = 'Sokolov';
```

### Q112 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'client' table; client data is only available via two_nf_disp's client__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT d.A2
FROM `client`  c
JOIN `disp`    di ON di.`client_id` = c.`client_id`
JOIN `account`  a  ON a.`account_id` = di.`account_id`
JOIN `district` d  ON d.`district_id` = a.`district_id`
WHERE c.`gender` = 'F'
  AND c.`birth_date` = '1976-01-29';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT district__district_name 
FROM two_nf_disp 
JOIN client ON two_nf_disp.disp__client_id = client.client_id 
JOIN account ON two_nf_disp.disp__account_id = account.account__account_id 
WHERE client.gender = 'F' AND client.birth_date = '1976-01-29';
```

### Q115 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins nonexistent 'two_nf_client'/'two_nf_district' cluster tables; the needed client+district combination only exists inside two_nf_disp.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (COUNT(CASE WHEN client__gender = 'M' THEN 1 END) * 100.0 / COUNT(*)) AS male_percentage
FROM 
    two_nf_disp
JOIN 
    two_nf_client ON two_nf_disp.client_id = two_nf_client.client_id
JOIN 
    two_nf_district ON two_nf_disp.client_id = two_nf_district.district_id
WHERE 
    two_nf_district.region = 'South Bohemia'
ORDER BY 
    two_nf_district.number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's percent-change formula between two exact dated balances (SUM(IIF(date=X,balance,0))*100/base) with an unrelated (MAX(balance)-MIN(balance))/day-count rate computed across the whole date range.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (MAX(trans__balance_after_transaction) - MIN(trans__balance_after_transaction)) / 
    (julianday('1998-12-27') - julianday('1993-03-22')) AS balance_increase_rate
FROM 
    two_nf_trans
WHERE 
    trans__account_id = (
        SELECT 
            loan__account_id
        FROM 
            two_nf_loan
        WHERE 
            loan__date = '1993-07-05' AND loan__status = 'A'
        LIMIT 1
    )
    AND trans__date BETWEEN '1993-03-22' AND '1998-12-27';
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** loan__status='A' instead of the requested status='C'.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (COUNT(DISTINCT CASE WHEN loan__status = 'A' THEN loan__loan_id END) * 100.0 / COUNT(DISTINCT loan__loan_id)) AS percentage_running_no_issue
FROM 
    two_nf_loan
WHERE 
    loan__amount < 100000;
```

### Q125 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Joins two_nf_loan and two_nf_disp, both of which carry a district__district_name column (via different district join paths -- loan via account's district, disp via client's district), so the bare reference is ambiguous.

**Gold SQL (original 3NF form):**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    district__district_name, 
    district__unemployment_rate_1996 - district__unemployment_rate_1995 AS unemployment_rate_increment
FROM 
    two_nf_loan
JOIN 
    two_nf_disp ON two_nf_loan.loan__account_id = two_nf_disp.disp__account_id
WHERE 
    two_nf_loan.status = 'Running' AND two_nf_loan.amount > 0;
```

### Q129 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** trans__type='withdrawal' is an invented value (real domain code is 'VYDAJ'); also adds an extraneous trans__transaction_type_code != 'credit_card' filter not in gold, and the added DISTINCT changes which of the top-10-by-amount transactions' districts are returned.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT district__district_name
FROM two_nf_trans
WHERE trans__type = 'withdrawal' AND trans__transaction_type_code != 'credit_card'
  AND trans__date BETWEEN '1996-01-01' AND '1996-01-31'
ORDER BY trans__amount DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Translates 'POPLATEK MESICNE' to 'Monthly' (not a real domain value) and adds an extraneous loan__status='A' filter not present in gold.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT loan__loan_id) 
FROM two_nf_loan 
WHERE loan__amount >= 250000 
AND account__statement_frequency = 'Monthly' 
AND loan__status = 'A' 
AND loan__date BETWEEN '1995-01-01' AND '1997-12-31';
```

### Q137 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Drops the required JOIN to loan (and its status IN ('C','D') filter) entirely, so it counts ALL accounts in district 1 rather than only those with a 'C' or 'D' status loan.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT account__account_id) 
FROM two_nf_account 
WHERE district__district_id = 1;
```

### Q138 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_client' cluster table; client data is only available via two_nf_disp's client__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A15 = (SELECT T3.A15 FROM district AS T3 ORDER BY T3.A15 DESC LIMIT 1, 1)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT client__client_id) 
FROM two_nf_disp 
JOIN two_nf_client ON two_nf_disp.client_id = two_nf_client.client_id 
JOIN two_nf_district ON two_nf_disp.district_id = two_nf_district.district_id 
WHERE two_nf_client.gender = 'M' 
AND two_nf_district.district_id = (
    SELECT district_id 
    FROM two_nf_district 
    ORDER BY number_crimes_1995 DESC 
    LIMIT 1 OFFSET 1
)
```

### Q145 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `two_nf_trans.amount`; the real column is `trans__amount`.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT disp__client_id
FROM two_nf_disp
JOIN two_nf_trans ON two_nf_disp.disp__account_id = two_nf_trans.trans__account_id
WHERE two_nf_trans.amount < (
    SELECT AVG(amount)
    FROM two_nf_trans
    WHERE strftime('%Y', trans__date) = '1998'
)
AND strftime('%Y', two_nf_trans.trans__date) = '1998';
```

### Q149 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects account__statement_frequency instead of the requested disp type (OWNER/DISPONENT); also substitutes an unrelated 'no loan' NOT IN subquery for gold's `type <> 'OWNER'` filter.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.`type`
FROM `district` AS T1
JOIN `account`  AS T2 ON T1.`district_id` = T2.`district_id`
JOIN `disp`     AS T3 ON T2.`account_id`  = T3.`account_id`
WHERE T3.`type` <> 'OWNER'
  AND T1.`A11`  > 8000
  AND T1.`A11` <= 9000;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT account__statement_frequency
FROM two_nf_account
WHERE account__account_id NOT IN (
    SELECT loan__account_id
    FROM two_nf_loan
)
AND district__average_salary BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_district' cluster table; district data (A15/number_crimes_1995) is not reachable that way -- there is no standalone two_nf_district cluster.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(district__number_crimes_1995)
FROM two_nf_account
JOIN two_nf_district ON two_nf_account.account__district_id = two_nf_district.district_id
WHERE two_nf_district.number_inhabitants > 4000
AND strftime('%Y', two_nf_account.account__date) >= '1997';
```

### Q159 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** trans__transaction_operation='Cash' is an invented value (real domain code is 'VYBER'); also adds a spurious trans__transaction_type_code='Withdrawal' filter (k_symbol, unrelated) not in gold, and the SELECT list drops most of gold's T4.* columns (keeps only transaction_id/date/amount).

**Gold SQL (original 3NF form):**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT trans__transaction_id, trans__date, trans__amount
FROM two_nf_trans
JOIN two_nf_disp ON two_nf_trans.trans__account_id = two_nf_disp.disp__account_id
WHERE two_nf_disp.disp__client_id = 3356 AND trans__transaction_type_code = 'Withdrawal' AND trans__transaction_operation = 'Cash';
```

### Q168 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_client' cluster table; client/district data is only available via two_nf_disp's client__*/district__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CAST(SUM(CASE WHEN client__gender = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(client__client_id) 
FROM 
    two_nf_disp 
JOIN 
    two_nf_client ON two_nf_disp.client_id = two_nf_client.client_id 
JOIN 
    two_nf_district ON two_nf_disp.district_id = two_nf_district.district_id 
WHERE 
    two_nf_district.average_salary > 10000;
```

### Q169 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_client' cluster table; the needed client+district+loan combination requires two_nf_disp's client__* columns joined to two_nf_loan, not a standalone client cluster.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (SUM(CASE WHEN loan__date BETWEEN '1996-01-01' AND '1996-12-31' THEN loan__amount ELSE 0 END) -
     SUM(CASE WHEN loan__date BETWEEN '1997-01-01' AND '1997-12-31' THEN loan__amount ELSE 0 END)) /
    SUM(CASE WHEN loan__date BETWEEN '1996-01-01' AND '1996-12-31' THEN loan__amount ELSE 0 END) AS growth_rate
FROM 
    two_nf_loan
JOIN 
    two_nf_disp ON two_nf_loan.loan__account_id = two_nf_disp.disp__account_id
JOIN 
    two_nf_client ON two_nf_disp.disp__client_id = two_nf_client.client_id
WHERE 
    two_nf_client.gender = 'M';
```

### Q173 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses the two_nf_trans cluster (regular transactions) instead of the two_nf_order cluster (standing orders) that gold's k_symbol/total_amount subquery is actually built from; also filters an invented operation value 'Debit'.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    account__statement_frequency, 
    SUM(trans__amount) AS total_debit_amount
FROM 
    two_nf_trans
WHERE 
    trans__account_id = 3 AND trans__transaction_operation = 'Debit'
GROUP BY 
    account__statement_frequency;
```

### Q186 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_client' cluster table; client data is only available via two_nf_disp's client__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN account__statement_frequency = 'weekly' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT client__client_id) 
FROM two_nf_disp 
JOIN two_nf_client ON two_nf_disp.client_id = two_nf_client.client_id 
JOIN two_nf_account ON two_nf_disp.account_id = two_nf_account.account_id 
WHERE two_nf_client.gender = 'M';
```

### Q189 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'client' table; client data is only available via two_nf_disp's client__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id  WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT account__account_id
FROM two_nf_disp
JOIN client ON two_nf_disp.disp__client_id = client.client_id
JOIN account ON two_nf_disp.disp__account_id = account.account__account_id
WHERE client.gender = 'F'
ORDER BY client.birth_date ASC, district__average_salary ASC
LIMIT 1;
```

### Q192 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References trans__transaction_type_code inside a query scoped to two_nf_loan without ever joining two_nf_trans; that column is real (in the sibling two_nf_trans cluster) and reachable only via a missing account_id join.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(loan__amount)
FROM (
    SELECT DISTINCT loan__loan_id, loan__amount
    FROM two_nf_loan
    WHERE loan__status = 'A' AND trans__transaction_type_code = 'VYDAJ'
)
```

### Q194 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'card' table; card data is already embedded in two_nf_disp as card__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT client__client_id, 
       strftime('%Y', 'now') - strftime('%Y', client__birth_date) - 
       (strftime('%m-%d', 'now') < strftime('%m-%d', client__birth_date)) AS age
FROM two_nf_disp
JOIN card ON two_nf_disp.disp__disposition_id = card.card__disposition_id
WHERE card.type = 'High Level' AND two_nf_disp.type = 'Loan';
```

---

## formula_1 (53 failures)

### Q846 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses the two_nf_results cluster (race results/status) instead of the two_nf_qualifying cluster that has the q1 qualifying time gold ranks by; drops the ORDER BY q1 DESC LIMIT 5 entirely, filtering results__status_id=1 instead.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__driver_ref_name 
FROM two_nf_results 
WHERE results__race_id = 20 AND results__status_id = 1;
```

### Q854 (simple, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_races' FULL OUTER JOIN to circuits preserves an orphan races row (circuitId=1, which doesn't exist in the circuits table at all -- a base-data gap) as a row with NULL lat/lng; gold's INNER JOIN excludes it. Verified empirically: predicted returns an extra (NULL,NULL) row alongside the correct (-34.9272,138.617) vs gold's single row; no DISTINCT-only repair removes it (needs a circuits__circuit_id IS NOT NULL guard).

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT circuits__latitude, circuits__longitude 
FROM two_nf_races 
WHERE races__name = 'Australian Grand Prix';
```

### Q857 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT: two_nf_races has one row per race, so querying without DISTINCT returns Abu Dhabi's lat/lng once per race held there (9 duplicate rows) instead of gold's single DISTINCT-deduped row -- verified empirically.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT circuits__latitude, circuits__longitude 
FROM two_nf_races 
WHERE races__name = 'Abu Dhabi Grand Prix';
```

### Q861 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time is stored as 'M:SS.sss' (e.g. '1:26.714'); predicted compares to the wrongly-reformatted exact string '0:01:54' instead of matching gold's LIKE '1:54%' prefix pattern, so it never matches real values.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__number 
FROM two_nf_qualifying 
WHERE qualifying__race_id = 903 AND qualifying__qualifying_3_time = '0:01:54';
```

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** lapTimes__time is stored as 'M:SS.sss'; predicted compares to the wrongly-reformatted exact string '0:01:27' instead of gold's LIKE '1:27%' prefix pattern.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name, drivers__url
FROM two_nf_lap_times
WHERE lapTimes__race_id = 161 AND lapTimes__time = '0:01:27';
```

### Q868 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_circuits' cluster table; circuit data is already embedded in two_nf_races as circuits__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT circuits__location, circuits__latitude, circuits__longitude 
FROM two_nf_races 
JOIN two_nf_circuits ON two_nf_races.races__circuit_id = two_nf_circuits.circuits__circuit_id 
WHERE two_nf_races.races__name = 'Malaysian Grand Prix';
```

### Q869 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Joins two_nf_results (which already carries its own constructors__url from results' own constructor join) to two_nf_constructors (which also has constructors__url), so the bare reference is ambiguous.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT constructors__url
FROM two_nf_results
JOIN two_nf_constructors ON two_nf_results.results__constructor_id = two_nf_constructors.constructors__constructor_id
WHERE two_nf_results.results__race_id = 9
ORDER BY two_nf_results.results__points DESC
LIMIT 1;
```

### Q872 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time is stored as 'M:SS.sss'; predicted compares to the wrongly-reformatted exact string '0:01:33' instead of gold's LIKE '1:33%' prefix pattern.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__driver_code
FROM two_nf_qualifying
WHERE qualifying__race_id = 45 AND qualifying__qualifying_3_time = '0:01:33';
```

### Q877 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Orders by drivers__date_of_birth ASC instead of gold's DESC, returning the oldest finisher instead of the youngest; also approximates gold's 'time IS NOT NULL' with results__status_id=1.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name, drivers__date_of_birth
FROM two_nf_results
WHERE results__race_id = 872 AND results__status_id = 1
ORDER BY drivers__date_of_birth ASC
LIMIT 1;
```

### Q879 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** results__fastest_lap_speed is stored as TEXT; predicted's MAX(...) comparison is done as a lexicographic string comparison instead of gold's CAST(...AS REAL), so it doesn't reliably find the numerically fastest lap speed.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__nationality
FROM two_nf_results
WHERE results__fastest_lap_speed = (
    SELECT MAX(results__fastest_lap_speed)
    FROM two_nf_results
)
```

### Q880 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_drivers' cluster table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT ((MAX(CASE WHEN r.`raceId` = 853 THEN CAST(r.`fastestLapSpeed` AS REAL) END) -
         MAX(CASE WHEN r.`raceId` = 854 THEN CAST(r.`fastestLapSpeed` AS REAL) END)) * 100.0) /
       MAX(CASE WHEN r.`raceId` = 854 THEN CAST(r.`fastestLapSpeed` AS REAL) END) AS percent_faster
FROM `drivers` d
JOIN `results`  r ON d.`driverId` = r.`driverId`
WHERE d.`forename` = 'Paul'
  AND d.`surname`  = 'di Resta';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    ((MAX(results__fastest_lap_speed) - MIN(results__fastest_lap_speed)) / MIN(results__fastest_lap_speed)) * 100 AS percentage_faster
FROM 
    two_nf_results
WHERE 
    results__driver_id = (
        SELECT drivers__driver_id 
        FROM two_nf_drivers 
        WHERE drivers__first_name = 'Paul' AND drivers__last_name = 'di Resta'
    )
    AND results__race_id IN (853, 854);
```

### Q881 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT drivers__first_name, drivers__last_name, 
       CAST(SUM(CASE WHEN results__status_id = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT results__result_id) AS completion_rate
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
WHERE races__date = '1983-07-16'
GROUP BY drivers__driver_id;
```

### Q884 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Substitutes races__round (season sequence number) for the calendar month (STRFTIME('%m', date)) that gold actually filters by, an unrelated attribute.

**Gold SQL (original 3NF form):**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT races__name 
FROM two_nf_races 
WHERE races__year = (SELECT MIN(races__year) FROM two_nf_races) 
AND races__round = (SELECT MIN(races__round) FROM two_nf_races WHERE races__year = (SELECT MIN(races__year) FROM two_nf_races));
```

### Q892 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT d.`forename`, d.`surname`, SUM(r.`points`) AS total_points
FROM `results` r
JOIN `drivers` d ON d.`driverId` = r.`driverId`
GROUP BY r.`driverId`
ORDER BY total_points DESC
LIMIT 1;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT drivers__first_name, drivers__last_name, SUM(points) AS total_points
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
GROUP BY two_nf_results.results__driver_id
ORDER BY total_points DESC
LIMIT 1;
```

### Q894 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_lap_times as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT lapTimes__time, drivers__first_name, drivers__last_name, races__name
FROM two_nf_lap_times
JOIN drivers ON lapTimes__driver_id = drivers__driver_id
JOIN races ON lapTimes__race_id = races__race_id
WHERE lapTimes__time = (SELECT MIN(lapTimes__time) FROM two_nf_lap_times);
```

### Q896 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses results__position (per-race finishing position) instead of the driverStandings__position (championship standings position) gold specifically requires; both are present in two_nf_results but only driverStandings__position matches the question.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN results__position != 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT results__result_id) 
FROM two_nf_results 
WHERE drivers__first_name = 'Lewis' AND drivers__last_name = 'Hamilton' AND races__year >= 2010;
```

### Q897 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    drivers__first_name, 
    drivers__last_name, 
    drivers__nationality, 
    MAX(driverStandings__points) AS max_points
FROM 
    two_nf_results
JOIN 
    drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
JOIN 
    driverStandings ON two_nf_results.driverStandings__driver_standings_id = driverStandings.driverStandings__driver_standings_id
GROUP BY 
    drivers__driver_id
ORDER BY 
    COUNT(DISTINCT driverStandings__wins) DESC
LIMIT 1;
```

### Q898 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MIN(drivers__date_of_birth), drivers__first_name, drivers__last_name
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
WHERE drivers.drivers__nationality = 'Japanese';
```

### Q901 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_circuits' cluster table; circuit data is already embedded in two_nf_races as circuits__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.name, T1.name, T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT races__name, circuits__name, circuits__location
FROM two_nf_races
JOIN two_nf_circuits ON races__circuit_id = circuits__circuit_id
WHERE races__year = 2005 AND strftime('%m', races__date) = '09';
```

### Q902 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT races__name 
FROM two_nf_results 
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id 
WHERE drivers.first_name = 'Alex' AND drivers.last_name = 'Yoong' AND two_nf_results.results__number < 20;
```

### Q904 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_lap_times as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT races__name, races__year
FROM two_nf_results
WHERE results__driver_id = (
    SELECT drivers__driver_id
    FROM drivers
    WHERE drivers__first_name = 'Michael' AND drivers__last_name = 'Schumacher'
)
ORDER BY results__fastest_lap_time ASC
LIMIT 1;
```

### Q906 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT races__name, results__points
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
WHERE drivers.first_name = 'Lewis' AND drivers.last_name = 'Hamilton'
ORDER BY races__date ASC
LIMIT 1;
```

### Q910 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT: two_nf_races has one row per race, so querying Silverstone's lat/lng without DISTINCT returns one duplicate row per race held there instead of gold's single circuit row.

**Gold SQL (original 3NF form):**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Silverstone Circuit'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT circuits__latitude, circuits__longitude 
FROM two_nf_races 
WHERE circuits__name = 'Silverstone Circuit';
```

### Q912 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters races__name (race name, e.g. 'Singapore Grand Prix') instead of circuits__name (circuit name); races__name would never equal a circuit name like 'Marina Bay Street Circuit', so this returns zero rows.

**Gold SQL (original 3NF form):**

```sql
SELECT circuitRef FROM circuits WHERE name = 'Marina Bay Street Circuit'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT circuits__circuit_ref_name 
FROM two_nf_races 
WHERE races__name = 'Marina Bay Street Circuit';
```

### Q915 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__nationality
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
ORDER BY drivers__date_of_birth ASC
LIMIT 1;
```

### Q928 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `name` on two_nf_races; the real column is `races__name`.

**Gold SQL (original 3NF form):**

```sql
SELECT d.forename, d.surname, d.driverRef FROM drivers AS d JOIN results AS r ON d.driverId = r.driverId JOIN races AS ra ON r.raceId = ra.raceId WHERE ra.name = 'Canadian Grand Prix' AND ra.year = 2007 AND r.position = 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name, drivers__driver_ref_name
FROM two_nf_results
JOIN two_nf_races ON two_nf_results.results__race_id = two_nf_races.races__race_id
WHERE two_nf_races.name = 'Canadian Grand Prix' AND two_nf_races.year = 2007 AND two_nf_results.position = 1;
```

### Q930 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_drivers' cluster table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT races__name
FROM two_nf_results
WHERE results__driver_id = (
    SELECT drivers__driver_id
    FROM two_nf_drivers
    WHERE drivers__first_name = 'Lewis' AND drivers__last_name = 'Hamilton'
)
ORDER BY results__position ASC
LIMIT 1;
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** races__name = 'AustChineseralian Grand Prix' is a garbled/invented value; the real value is 'Chinese Grand Prix'.

**Gold SQL (original 3NF form):**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT results__time 
FROM two_nf_results 
WHERE results__race_id = (
    SELECT races__race_id 
    FROM two_nf_races 
    WHERE races__year = 2008 AND races__name = 'AustChineseralian Grand Prix'
) 
AND results__position = 2;
```

### Q940 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the results__time IS NOT NULL filter, counting all participating drivers instead of only those who finished with a recorded time.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT results__driver_id) 
FROM two_nf_results 
WHERE results__race_id IN (
    SELECT races__race_id 
    FROM two_nf_races 
    WHERE races__year = 2008 AND races__name = 'Chinese Grand Prix'
)
```

### Q944 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Does not reproduce gold's CTE chain identifying the champion (positionOrder=1) vs last-place (MAX positionOrder) driver's millisecond times for the specific race; instead computes an unrelated fastest-lap-speed spread metric across the whole race.

**Gold SQL (original 3NF form):**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    ((MAX(results__fastest_lap_speed) - MIN(results__fastest_lap_speed)) / MIN(results__fastest_lap_speed)) * 100 AS percentage_faster
FROM 
    two_nf_results
WHERE 
    races__year = 1988 AND races__name = 'Australian Grand Prix';
```

### Q948 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Outer query references bare `points`; even within the derived subquery the real column name is `constructorResults__points`.

**Gold SQL (original 3NF form):**

```sql
SELECT MAX(T1.points) FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T2.nationality = 'British'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MAX(points) 
FROM (
    SELECT DISTINCT constructorResults__constructor_id, constructorResults__points 
    FROM two_nf_constructors 
    WHERE constructors__nationality = 'British'
)
```

### Q950 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Needs the two_nf_constructors cluster's constructorStandings__points (constructor championship standings) but uses two_nf_results' results__points (an individual driver's race points) instead -- an unrelated metric.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT constructors__name 
FROM two_nf_results 
WHERE results__race_id = 291 AND results__points = 0;
```

### Q955 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `T2.time` on two_nf_races (alias T2); the real column is `races__time` -- and even semantically the wrong column, since gold needs results.milliseconds/1000.0, not the race's own start time.

**Gold SQL (original 3NF form):**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(T2.time) AS avg_time_seconds
FROM two_nf_results AS T1
JOIN two_nf_races AS T2 ON T1.results__race_id = T2.races__race_id
WHERE T2.year < 1975 AND T1.position = 1
GROUP BY T2.year;
```

### Q959 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes an unrelated driverStandings__position=1 condition for gold's results.time LIKE '_:%:__.___' full-timestamp-format filter, selecting a completely different race subset.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT results__fastest_lap_number
FROM two_nf_results
WHERE results__race_id IN (
    SELECT driverStandings__race_id
    FROM two_nf_results
    WHERE driverStandings__position = 1 AND races__year = 2009
)
```

### Q960 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `fastest_lap_speed` instead of `results__fastest_lap_speed`.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T1.fastestLapSpeed) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T2.name = 'Spanish Grand Prix'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(fastest_lap_speed)
FROM (
    SELECT DISTINCT results__result_id, fastest_lap_speed
    FROM two_nf_results
    WHERE races__year = 2009 AND races__name = 'Spanish Grand Prix'
)
```

### Q962 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Moves the laps>50 condition from inside gold's numerator-only IIF(...) into a blanket WHERE filter, which incorrectly also restricts the denominator (COUNT DISTINCT driver_id) to only high-lap-count rows instead of all drivers in 2000-2005 races; the numerator also sums per-row matches instead of counting distinct qualifying drivers.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN drivers__date_of_birth < '1985-01-01' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT results__driver_id) 
FROM two_nf_results 
WHERE races__year BETWEEN 2000 AND 2005 AND results__laps >= 50;
```

### Q963 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_lap_times as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT drivers__driver_id)
FROM two_nf_lap_times
JOIN drivers ON two_nf_lap_times.drivers__driver_id = drivers.drivers__driver_id
WHERE drivers.drivers__nationality = 'French'
AND two_nf_lap_times.lapTimes__time < '02:00.00';
```

### Q964 (simple, retrieval) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_results fans out each driver into one row per race entry; `SELECT DISTINCT drivers__driver_code` dedupes on the output VALUE instead of the driver entity, collapsing gold's one-row-per-driver result (which can repeat the same code across different drivers) down to just the distinct code values -- a DISTINCT scoped to driver_id first would reproduce gold's multiset.

**Gold SQL (original 3NF form):**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__driver_code 
FROM two_nf_results 
WHERE drivers__nationality = 'American';
```

### Q967 (simple, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT drivers__driver_id)
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
WHERE drivers.nationality = 'Netherlands'
ORDER BY drivers.date_of_birth DESC
LIMIT 3;
```

### Q971 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT driverRef FROM drivers WHERE nationality = 'German' ORDER BY JULIANDAY(dob) ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT drivers__driver_ref_name 
FROM two_nf_results 
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id 
WHERE drivers.drivers__nationality = 'German' 
ORDER BY drivers.drivers__date_of_birth ASC 
LIMIT 1;
```

### Q972 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__driver_id, drivers__driver_code
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
WHERE drivers.date_of_birth LIKE '1971%'
AND two_nf_results.fastest_lap_time IS NOT NULL;
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses BETWEEN 50 AND 100 (inclusive) instead of gold's exclusive raceId<100 AND raceId>50, and drops the 'time IS NOT NULL' condition entirely, counting all disqualified entries rather than only those with a recorded time.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT results__result_id) 
FROM two_nf_results 
WHERE results__race_id BETWEEN 50 AND 100 
AND status__status = 'Disqualified';
```

### Q978 (simple, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_circuits' cluster table; circuit data is already embedded in two_nf_races as circuits__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT circuits__location, circuits__latitude, circuits__longitude 
FROM two_nf_races 
JOIN two_nf_circuits ON two_nf_races.races__circuit_id = two_nf_circuits.circuits__circuit_id 
WHERE circuits__country = 'Austria';
```

### Q981 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_drivers' cluster table; driver data is already embedded in two_nf_qualifying as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT MIN(races__year) AS year, races__name, races__date, races__time
FROM two_nf_qualifying
JOIN two_nf_drivers ON two_nf_qualifying.qualifying__driver_id = two_nf_drivers.drivers__driver_id
JOIN two_nf_races ON two_nf_qualifying.qualifying__race_id = two_nf_races.races__race_id
ORDER BY drivers__date_of_birth ASC, races__year ASC, races__round ASC
LIMIT 1;
```

### Q988 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_pit_stops as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM two_nf_pit_stops
JOIN drivers ON two_nf_pit_stops.drivers__driver_id = drivers.drivers__driver_id
WHERE drivers.drivers__nationality = 'German'
AND drivers.drivers__date_of_birth BETWEEN '1980-01-01' AND '1985-12-31'
GROUP BY drivers.drivers__driver_id
ORDER BY AVG(two_nf_pit_stops.duration) ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `two_nf_races.name`; the real column is `races__name`.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT results__time 
FROM two_nf_results 
JOIN two_nf_races ON results__race_id = two_nf_races.races__race_id 
WHERE two_nf_races.name = 'Canadian Grand Prix' AND two_nf_races.year = 2008 
ORDER BY results__position ASC 
LIMIT 1;
```

### Q990 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Joins two_nf_results (which already carries its own constructors__* columns) to two_nf_constructors (which also has constructors__constructor_ref_name), so the bare reference is ambiguous.

**Gold SQL (original 3NF form):**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT constructors__constructor_ref_name, constructors__url
FROM two_nf_results
JOIN two_nf_races ON two_nf_results.results__race_id = two_nf_races.races__race_id
JOIN two_nf_constructors ON two_nf_results.results__constructor_id = two_nf_constructors.constructors__constructor_id
WHERE two_nf_races.year = 2009 AND two_nf_races.name = 'Singapore Grand Prix' AND two_nf_results.position = 1;
```

### Q994 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Joins two_nf_results (which already carries its own constructors__constructor_id) to two_nf_constructors (which also has constructors__constructor_id), so the derived subquery's GROUP BY reference is ambiguous.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    MAX(total_points) AS score, 
    constructors__name AS name, 
    constructors__nationality AS nationality
FROM (
    SELECT 
        constructors__constructor_id, 
        SUM(results__points) AS total_points, 
        constructors__name, 
        constructors__nationality
    FROM 
        two_nf_results
    JOIN 
        two_nf_races ON two_nf_results.results__race_id = two_nf_races.races__race_id
    JOIN 
        two_nf_constructors ON two_nf_results.results__constructor_id = two_nf_constructors.constructors__constructor_id
    WHERE 
        two_nf_races.name = 'Monaco Grand Prix' 
        AND two_nf_races.year BETWEEN 1980 AND 2010
    GROUP BY 
        constructors__constructor_id
) AS subquery;
```

### Q1001 (challenging, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_circuits' cluster table; circuit data is already embedded in two_nf_races as circuits__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM two_nf_qualifying
JOIN two_nf_races ON two_nf_qualifying.qualifying__race_id = two_nf_races.races__race_id
JOIN two_nf_circuits ON two_nf_races.races__circuit_id = two_nf_circuits.circuits__circuit_id
WHERE two_nf_races.races__year = 2008
AND two_nf_races.races__round = 3
AND two_nf_circuits.circuits__name = 'Marina Bay Street Circuit'
AND two_nf_qualifying.position = 1;
```

### Q1002 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'drivers' table; driver data is already embedded in two_nf_results as drivers__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    drivers__first_name, 
    drivers__last_name, 
    drivers__nationality, 
    races__name
FROM 
    two_nf_results
JOIN 
    drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
JOIN 
    races ON two_nf_results.results__race_id = races.races__race_id
ORDER BY 
    drivers__date_of_birth DESC
LIMIT 1;
```

### Q1003 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** The outer query drops the races__name='Canadian Grand Prix' filter (present only in the subquery), so it counts ALL of that driver's accident-status results across every race instead of just the Canadian Grand Prix -- verified empirically: predicted returns 18 vs gold's 2.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT results__result_id) 
FROM two_nf_results 
WHERE results__driver_id = (
    SELECT results__driver_id 
    FROM two_nf_results 
    WHERE races__name = 'Canadian Grand Prix' 
    AND status__status = 'Accident' 
    GROUP BY results__driver_id 
    ORDER BY COUNT(DISTINCT results__result_id) DESC 
    LIMIT 1
)
AND status__status = 'Accident';
```

### Q1011 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Missing GROUP BY driver_id + MIN(milliseconds) entirely; instead orders raw lap-time rows ascending and takes the top 20, which can repeat the same driver's multiple fast laps instead of 20 distinct drivers' personal-best times.

**Gold SQL (original 3NF form):**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM two_nf_lap_times
ORDER BY lapTimes__milliseconds ASC
LIMIT 20;
```

### Q1014 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_lap_times (individual lap times during races) instead of the two_nf_results cluster's FastestLapTime field that gold's query is actually built around -- an entirely different, unrelated data source.

**Gold SQL (original 3NF form):**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MIN(lapTimes__milliseconds) AS fastest_lap_time
FROM two_nf_lap_times
JOIN two_nf_races ON lapTimes__race_id = two_nf_races.races__race_id
WHERE two_nf_races.circuits__country = 'Italy';
```

---

## student_club (29 failures)

### Q1322 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's outer `COUNT(*) FROM (... GROUP BY ... HAVING ...)` wrapping, so instead of one number (the count of qualifying events) it returns one row per qualifying event; also filters event__type='meeting' (lowercase) instead of 'Meeting'.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT event__event_id)
FROM two_nf_event
WHERE event__type = 'meeting'
GROUP BY event__event_id
HAVING COUNT(DISTINCT attendance__member_id) > 10;
```

### Q1323 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent standalone 'attendance' table; attendance data is already embedded in two_nf_event as attendance__* columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT E.`event_name`
FROM `Event` AS E
JOIN `Attendance` AS A ON E.`event_id` = A.`link_to_event`
WHERE E.`type` <> 'Fundraiser'
GROUP BY E.`event_id`
HAVING COUNT(*) > 20;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT event__event_name 
FROM two_nf_event 
WHERE event__type != 'fundraiser' 
AND event__event_id IN (
    SELECT event_id 
    FROM attendance 
    GROUP BY event_id 
    HAVING COUNT(DISTINCT member_id) > 20
)
```

### Q1331 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `income_id` instead of `income__income_id` on two_nf_member.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.amount FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Vice President'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT SUM(amount) 
FROM (
    SELECT DISTINCT income_id, amount 
    FROM two_nf_member 
    WHERE position = 'Vice President'
)
```

### Q1334 (simple, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_member's FULL OUTER JOIN to zip_code preserves an orphan zip_code row (an Illinois zip with no matching member) as a row with NULL member fields; gold's INNER JOIN excludes it. Verified empirically: predicted returns an extra blank row alongside gold's 3 rows; no DISTINCT-only repair removes it.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT member__first_name, member__last_name 
FROM two_nf_member 
WHERE zip_code__state = 'Illinois';
```

### Q1338 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** two_nf_expense has no event_name attribute (only budget__event_id); predicted substitutes its own expense__expense_date for the required event_name='October Meeting' identification instead of joining to two_nf_event, which changes which expenses match entirely.

**Gold SQL (original 3NF form):**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT expense__expense_id, expense__is_approved
FROM two_nf_expense
WHERE expense__expense_date BETWEEN '2019-10-08 00:00:00' AND '2019-10-08 23:59:59';
```

### Q1339 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `expense_id`/`cost` instead of `expense__expense_id`/`expense__cost`.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(cost) 
FROM (
    SELECT DISTINCT expense_id, cost 
    FROM two_nf_expense 
    WHERE member__first_name = 'Elijah' 
    AND member__last_name = 'Allen' 
    AND expense__expense_date BETWEEN '2023-09-01' AND '2023-10-31'
)
```

### Q1340 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `amount_spent`/`event_date` instead of `budget__amount_spent`/`event__event_date`.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
  (SELECT SUM(amount_spent) 
   FROM two_nf_event 
   WHERE event_date BETWEEN '2019-01-01' AND '2019-12-31') -
  (SELECT SUM(amount_spent) 
   FROM two_nf_event 
   WHERE event_date BETWEEN '2020-01-01' AND '2020-12-31') AS difference;
```

### Q1344 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_event (with unrelated event__notes) instead of income data (only in two_nf_member as income__notes), confusing 'Fundraising' (an income source) with an event type -- 'fundraising' isn't even a real event__type value.

**Gold SQL (original 3NF form):**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT event__notes 
FROM two_nf_event 
WHERE event__event_date = '2019-09-14' AND event__type = 'fundraising';
```

### Q1350 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_event instead of two_nf_expense (which has both expense__expense_description and budget__event_status together), and mistakenly filters event__event_name against an expense description value ('Post Cards, Posters').

**Gold SQL (original 3NF form):**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT event__status 
FROM two_nf_event 
WHERE event__event_date = '2019-08-20' AND event__event_name = 'Post Cards, Posters';
```

### Q1359 (challenging, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_budget' cluster table; budget data is embedded in two_nf_event as budget__* columns, not a standalone budget cluster.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT budget__budget_id)
FROM two_nf_budget
WHERE budget__category = 'Advertisement'
AND budget__event_id IN (
    SELECT event__event_id
    FROM two_nf_event
    WHERE event__event_name = 'Yearly Kickoff'
)
AND budget__amount_spent > (
    SELECT budget__amount_spent
    FROM two_nf_budget
    WHERE budget__category = 'Advertisement'
    AND budget__event_id IN (
        SELECT event__event_id
        FROM two_nf_event
        WHERE event__event_name = 'October Meeting'
    )
);
```

### Q1361 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `cost`/`expense_description` instead of `expense__cost`/`expense__expense_description`.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT SUM(cost) 
FROM two_nf_expense 
WHERE expense_description LIKE '%pizza%'
```

### Q1375 (moderate, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_member's FULL OUTER JOIN to major preserves an orphan major row (matching department with no matching member) as a row with NULL member fields; gold's INNER JOIN excludes it. Verified empirically: predicted returns an extra blank row alongside gold's 5 rows.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.department = 'School of Applied Sciences, Technology and Education'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM two_nf_member
WHERE major__department = 'School of Applied Sciences, Technology and Education';
```

### Q1376 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's `HAVING SUM(spent)/SUM(amount) = (SELECT MAX(ratio) FROM (...))` tie-preserving comparison into a plain `ORDER BY (amount_spent/amount) DESC LIMIT 1`, dropping the per-event SUM() aggregation (an event can have multiple budget line items) and any possibility of preserving ties; also uses 'closed' (lowercase) instead of 'Closed'.

**Gold SQL (original 3NF form):**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT event__event_name
FROM two_nf_event
WHERE event__status = 'closed'
ORDER BY (budget__amount_spent / budget__amount) DESC
LIMIT 1;
```

### Q1380 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `cost` on two_nf_expense (real column is expense__cost); more fundamentally uses the expense cluster filtered by description LIKE '%food%' instead of the budget cluster's category='Food' that gold actually sums.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT SUM(cost) 
FROM two_nf_expense 
WHERE expense_description LIKE '%food%'
```

### Q1381 (moderate, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_event's FULL OUTER JOIN chain preserves events with no attendance as orphan rows with NULL member_id, which get grouped into a spurious NULL-member group that also satisfies HAVING COUNT(DISTINCT event_id)>7; gold's INNER JOIN excludes these entirely. Verified empirically: predicted returns an extra blank-name row alongside all of gold's 29 rows.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM two_nf_event
GROUP BY member__member_id
HAVING COUNT(DISTINCT event__event_id) > 7;
```

### Q1387 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** two_nf_event's member__* comes from event ATTENDANCE, not from EXPENSE submission (gold needs the member who submitted the 'Yearly Kickoff' expense, via budget->expense->member, which lives only in two_nf_expense); also 'Budget Manager' is an invented position value (real value is 'Treasurer').

**Gold SQL (original 3NF form):**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT member__first_name, member__last_name 
FROM two_nf_event 
WHERE event__event_name = 'Yearly Kickoff' AND member__position = 'Budget Manager';
```

### Q1389 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References expense__cost without ever joining two_nf_expense; that column is real (in the sibling two_nf_expense cluster) and reachable only via a missing budget_id join -- two_nf_event has no expense data at all.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT event__event_name
FROM two_nf_event
ORDER BY expense__cost ASC, event__event_name ASC
LIMIT 1;
```

### Q1390 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `cost` instead of `expense__cost`; also references a nonexistent `expense__event_id` (the real link to an event is via expense__budget_id -> budget__event_id).

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (SELECT SUM(cost) 
     FROM two_nf_expense 
     WHERE expense__event_id = 
         (SELECT event__event_id 
          FROM two_nf_event 
          WHERE event__event_name = 'Yearly Kickoff')) * 100.0 / 
    (SELECT SUM(cost) 
     FROM two_nf_expense) AS percentage
```

### Q1398 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** budget__category='advertisement' (lowercase) instead of the real value 'Advertisement'.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT event__event_name 
FROM two_nf_event 
WHERE budget__category = 'advertisement' 
ORDER BY budget__amount_spent DESC 
LIMIT 1;
```

### Q1401 (moderate, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_budget' cluster table; budget data is embedded in two_nf_expense as budget__* columns, not a standalone budget cluster.

**Gold SQL (original 3NF form):**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT expense__cost 
FROM two_nf_expense 
WHERE expense__expense_description LIKE '%posters%' 
AND expense__budget_id IN (
    SELECT budget__budget_id 
    FROM two_nf_budget 
    WHERE budget__event_id = (
        SELECT event__event_id 
        FROM two_nf_event 
        WHERE event__event_name = 'September Speaker'
    )
);
```

### Q1403 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses 'closed' (lowercase, real value 'Closed') and entirely drops the 'remaining < 0' filter, so the top-ranked event by budget deficit needn't actually have a negative remaining balance.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT event__event_name
FROM two_nf_event
WHERE event__status = 'closed'
ORDER BY (budget__amount_spent - budget__amount) DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Joins a nonexistent 'two_nf_budget' cluster table; budget data is embedded in two_nf_expense as budget__* columns, not a standalone budget cluster.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT expense__category, SUM(expense__cost) AS total_value
FROM two_nf_expense
JOIN two_nf_budget ON expense__budget_id = budget__budget_id
JOIN two_nf_event ON budget__event_id = event__event_id
WHERE event__event_name = 'October Meeting' AND expense__is_approved = 1
GROUP BY expense__category;
```

### Q1409 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `expense_id` instead of `expense__expense_id`.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT SUM(cost) 
FROM (
    SELECT DISTINCT expense_id, cost 
    FROM two_nf_expense 
    WHERE expense_date = '2019-08-20'
)
```

### Q1410 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `cost` instead of `expense__cost`.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT member__first_name, member__last_name, SUM(cost) AS total_cost
FROM two_nf_expense
WHERE member__member_id = 'rec4BLdZHS2Blfp4v'
GROUP BY member__member_id;
```

### Q1411 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a redundant DISTINCT that collapses gold's repeated expense_description values (Sacha Harrison submitted the same description multiple times, e.g. 'Posters' x3) down to unique values only -- verified empirically: gold returns 12 rows, predicted 7.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT expense__expense_description 
FROM two_nf_expense 
WHERE member__first_name = 'Sacha' AND member__last_name = 'Harrison';
```

### Q1422 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects budget__category instead of the requested event__type.

**Gold SQL (original 3NF form):**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT budget__category 
FROM two_nf_event 
WHERE event__location = 'MU 215';
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** event__type='game' and event__status='closed' (lowercase) instead of the real values 'Game'/'Closed'.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT event__event_name 
FROM two_nf_event 
WHERE event__type = 'game' 
AND event__status = 'closed' 
AND event__event_date BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1457 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `cost` instead of `expense__cost`.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    member__first_name, 
    member__last_name, 
    member__phone
FROM 
    two_nf_expense
WHERE 
    cost > (
        SELECT 
            AVG(cost)
        FROM 
            two_nf_expense
    )
```

### Q1460 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Splits the single literal 'Water, Veggie tray, supplies' into three separate lowercase items compared via IN(...), a different (and incorrect) predicate structure that won't match the actual single compound-string value.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    member__first_name, 
    member__last_name, 
    expense__cost
FROM 
    two_nf_expense
WHERE 
    expense__expense_description IN ('water', 'veggie tray', 'supplies');
```

---

## superhero (28 failures)

### Q724 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour='blue' and colour_hair__colour='blond' (lowercase) instead of the real values 'Blue'/'Blond'.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE colour_eye__colour = 'blue' AND colour_hair__colour = 'blond';
```

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the 'height_cm IS NOT NULL AND height_cm != 0' filter entirely, including heroes with zero/missing height in the ranked output.

**Gold SQL (original 3NF form):**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name, superhero__height_cm
FROM two_nf_superhero
WHERE publisher__publisher_name = 'Marvel Comics'
ORDER BY superhero__height_cm DESC;
```

### Q728 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's `RANK() OVER (ORDER BY COUNT(id) DESC)` window-function output column entirely, substituting a bare ORDER BY without producing the PopularityRank value gold's SELECT list requires.

**Gold SQL (original 3NF form):**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT colour_eye__colour, COUNT(DISTINCT superhero__id) AS count
FROM two_nf_superhero
WHERE publisher__publisher_name = 'Marvel Comics'
GROUP BY colour_eye__colour
ORDER BY count DESC;
```

### Q730 (challenging, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT that collapses two different superhero rows sharing the same name ('Atlas') into one, whereas gold (EXISTS-based, no DISTINCT) correctly returns one row per matching hero id -- verified empirically: identical row sets except gold lists 'Atlas' twice.

**Gold SQL (original 3NF form):**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_power AS T2 INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.id = T2.hero_id)AND EXISTS (SELECT 1 FROM publisher AS T4 WHERE T4.publisher_name = 'Marvel Comics' AND T1.publisher_id = T4.id)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT t1.superhero__superhero_name
FROM two_nf_superhero t1
JOIN two_nf_hero_power t2 ON t1.superhero__id = t2.hero_power__hero_id
WHERE t1.publisher__publisher_name = 'Marvel Comics' AND t2.superpower__power_name = 'Super Strength';
```

### Q732 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_superhero's height_cm (an unrelated physical attribute) instead of the two_nf_hero_attribute cluster's attribute_value for 'Speed', which lives in an entirely separate cluster table.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id INNER JOIN attribute AS T4 ON T3.attribute_id = T4.id WHERE T4.attribute_name = 'Speed' ORDER BY T3.attribute_value LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT publisher__publisher_name
FROM two_nf_superhero
WHERE superhero__height_cm = (
    SELECT MIN(superhero__height_cm)
    FROM two_nf_superhero
)
```

### Q733 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour='gold' (lowercase) instead of the real value 'Gold'.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT superhero__id) 
FROM two_nf_superhero 
WHERE colour_eye__colour = 'gold' AND publisher__publisher_name = 'Marvel Comics';
```

### Q736 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References a nonexistent `hero_attribute__attribute_name` on two_nf_superhero; the real columns (attribute__attribute_name, hero_attribute__attribute_value) live in the separate two_nf_hero_attribute cluster, not two_nf_superhero.

**Gold SQL (original 3NF form):**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE hero_attribute__attribute_name = 'IQ' 
ORDER BY hero_attribute__attribute_value ASC 
LIMIT 1;
```

### Q738 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT that collapses 4 different superhero rows that all happen to be named 'Atlas' (each independently satisfying Durability<50) down to 1, whereas gold's EXISTS-based query (no DISTINCT) returns one row per matching hero id -- verified empirically: gold 371 rows vs predicted's 368 distinct names, differing only in the repeated 'Atlas' entries.

**Gold SQL (original 3NF form):**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_attribute AS T2 INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Durability' AND T2.attribute_value < 50 AND T1.id = T2.hero_id)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_hero_attribute 
WHERE attribute__attribute_name = 'Durability' AND hero_attribute__attribute_value < 50;
```

### Q743 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment__alignment='Selfish' is an invented value; the real domain values are only Good/Bad/Neutral/N/A (gold needs 'Bad').

**Gold SQL (original 3NF form):**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CAST(COUNT(DISTINCT CASE WHEN alignment__alignment = 'Selfish' THEN superhero__id END) AS REAL) * 100 / COUNT(DISTINCT superhero__id) AS percentage_selfish,
    COUNT(DISTINCT CASE WHEN alignment__alignment = 'Selfish' AND publisher__publisher_name = 'Marvel Comics' THEN superhero__id END) AS selfish_marvel_count
FROM 
    two_nf_superhero;
```

### Q744 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's `CASE WHEN marvel_cnt>dc_cnt THEN 'Marvel Comics' ELSE 'DC Comics' END` label column entirely, and computes the difference as DC_count - Marvel_count (reversed sign) instead of gold's Marvel_count - DC_count.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (SELECT COUNT(DISTINCT superhero__id) 
     FROM two_nf_superhero 
     WHERE publisher__publisher_name = 'DC Comics') -
    (SELECT COUNT(DISTINCT superhero__id) 
     FROM two_nf_superhero 
     WHERE publisher__publisher_name = 'Marvel Comics') AS difference;
```

### Q750 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the 'weight_kg > 0' filter, including heroes with zero/missing weight in the average.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(superhero__weight_kg)
FROM (
    SELECT DISTINCT superhero__id, superhero__weight_kg
    FROM two_nf_superhero
    WHERE gender__gender = 'Female'
)
```

### Q751 (moderate, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** Joining two_nf_hero_power to two_nf_superhero (each independently built via its own FULL OUTER JOIN chain) produces an orphan row with a NULL power_name/gender that leaks through; verified empirically: predicted's distinct power-name set has one extra blank entry vs gold's, otherwise identical.

**Gold SQL (original 3NF form):**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superpower__power_name 
FROM two_nf_hero_power 
JOIN two_nf_superhero ON two_nf_hero_power.superhero__id = two_nf_superhero.superhero__id 
WHERE two_nf_superhero.gender__gender = 'Male';
```

### Q753 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes `eye_colour_id IS NULL` for `colour='No Colour'`; 'No Colour' is itself a real catalogued colour value (colour.id=1), not a missing/NULL eye_colour_id.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE superhero__height_cm BETWEEN 170 AND 190 
AND superhero__eye_colour_id IS NULL;
```

### Q758 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** race_id=1 is the wrong id for 'Human'; the real id is 24.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT colour_hair__colour 
FROM two_nf_superhero 
WHERE superhero__race_id = 1 AND superhero__height_cm = 185;
```

### Q769 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** two_nf_superhero has no hero_attribute__* columns at all; that data (attribute_id/attribute_value for 'Durability') lives in the separate two_nf_hero_attribute cluster, which is never joined here.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT superhero__superhero_name
FROM two_nf_superhero
WHERE superhero__publisher_id = (
    SELECT publisher__id
    FROM two_nf_superhero
    WHERE publisher__publisher_name = 'Dark Horse Comics'
)
GROUP BY superhero__id
ORDER BY COUNT(DISTINCT hero_attribute__attribute_id) DESC
LIMIT 1;
```

### Q772 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects the joined colour NAME strings (colour_eye__colour etc.) instead of gold's requested raw ID columns (superhero__eye_colour_id, superhero__hair_colour_id, superhero__skin_colour_id).

**Gold SQL (original 3NF form):**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    colour_eye__colour AS eye_colour, 
    colour_hair__colour AS hair_colour, 
    colour_skin__colour AS skin_colour
FROM 
    two_nf_superhero
WHERE 
    gender__gender = 'Female' 
    AND publisher__publisher_name = 'Dark Horse Comics';
```

### Q773 (challenging, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_superhero's FULL OUTER JOIN to publisher preserves heroes whose publisher_id doesn't match any real publisher row (e.g. He-Man, She-Ra) as rows with NULL publisher_name; gold's INNER JOIN excludes them. Verified empirically: predicted has 2 extra rows ('He-Man', 'She-Ra' with blank publisher) not in gold; the eye=hair=skin colour rewrite itself is logically equivalent to gold's and not the bug.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name, T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.eye_colour_id = T1.hair_colour_id AND T1.eye_colour_id = T1.skin_colour_id
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name, publisher__publisher_name
FROM two_nf_superhero
WHERE superhero__eye_colour_id = superhero__hair_colour_id
AND superhero__hair_colour_id = superhero__skin_colour_id;
```

### Q782 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour='black' and colour_hair__colour='black' (lowercase) instead of the real value 'Black'.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE colour_eye__colour = 'black' AND colour_hair__colour = 'black';
```

### Q788 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Moves gold's Marvel-Comics condition from a CASE-conditional numerator constraint into a blanket WHERE filter, which restricts both numerator and denominator to Marvel heroes only -- computing % Female-among-Marvel instead of gold's % Marvel-among-Female.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN gender__gender = 'Female' THEN superhero__id END) AS REAL) * 100 / COUNT(DISTINCT superhero__id) 
FROM two_nf_superhero 
WHERE publisher__publisher_name = 'Marvel Comics';
```

### Q791 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `height_cm` instead of `superhero__height_cm`.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(height_cm) 
FROM (
    SELECT DISTINCT superhero__id, height_cm 
    FROM two_nf_superhero
)
```

### Q794 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses two_nf_superhero's height_cm (unrelated) instead of the two_nf_hero_attribute cluster's 'Speed' attribute_value that gold's MAX-based query is actually built around.

**Gold SQL (original 3NF form):**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
ORDER BY superhero__height_cm DESC 
LIMIT 1;
```

### Q797 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour='blue' and colour_hair__colour='brown' (lowercase) instead of the real values 'Blue'/'Brown'.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE colour_eye__colour = 'blue' AND colour_hair__colour = 'brown';
```

### Q798 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT that collapses gold's 3 repeated 'DC Comics' rows (one per matching hero name) into 1 -- verified empirically.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT publisher__publisher_name 
FROM two_nf_superhero 
WHERE superhero__superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy');
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour='blue' (lowercase) instead of the real value 'Blue' (verified no heroes have a NULL/unmatched eye colour, so this is the sole cause of the mismatch).

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN colour_eye__colour = 'blue' THEN superhero__id END) AS REAL) * 100 / COUNT(DISTINCT superhero__id) 
FROM two_nf_superhero;
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue' (lowercase) instead of 'Blue'; substitutes `colour IS NULL` for the real catalogued value `colour = 'No Colour'`; and drops the `weight_kg = 0` half of gold's OR condition, checking only `weight_kg IS NULL`.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    COUNT(DISTINCT CASE WHEN colour_eye__colour = 'blue' THEN superhero__id END) - 
    COUNT(DISTINCT CASE WHEN colour_eye__colour IS NULL THEN superhero__id END) AS difference
FROM 
    two_nf_superhero
WHERE 
    superhero__weight_kg IS NULL;
```

### Q822 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_skin__colour='green' (lowercase, should be 'Green') and alignment__alignment='villain' (invented; the real value is 'Bad').

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT superhero__id) 
FROM two_nf_superhero 
WHERE colour_skin__colour = 'green' AND alignment__alignment = 'villain';
```

### Q825 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Queries the wrong cluster (two_nf_hero_attribute) for a superpower name ('Phoenix Force' is a superpower, not a hero_attribute, and belongs in two_nf_hero_power); two_nf_hero_attribute also has no gender__gender column at all (only superhero__gender_id).

**Gold SQL (original 3NF form):**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT gender__gender
FROM two_nf_hero_attribute
WHERE attribute__attribute_name = 'Phoenix Force';
```

### Q829 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's CASE WHEN label column entirely (same restructuring miss as sibling question 744), and uses the truncated/invented value 'DC' instead of the real publisher name 'DC Comics' (guaranteeing zero DC-count matches).

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
  (SELECT COUNT(DISTINCT superhero__id) 
   FROM two_nf_superhero 
   WHERE publisher__publisher_name = 'DC') -
  (SELECT COUNT(DISTINCT superhero__id) 
   FROM two_nf_superhero 
   WHERE publisher__publisher_name = 'Marvel Comics') AS difference;
```

---

## thrombosis_prediction (49 failures)

### Q1149 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `admission_type` instead of `Patient__admission_type`; also uses invented values 'In-patient'/'Out-patient' instead of the real domain '+'/'-'.

**Gold SQL (original 3NF form):**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CASE 
        WHEN inpatient_count > outpatient_count THEN 'In-patient'
        ELSE 'Out-patient'
    END AS majority_group,
    ABS(inpatient_count - outpatient_count) * 100.0 / (inpatient_count + outpatient_count) AS deviation_percentage
FROM (
    SELECT 
        COUNT(DISTINCT CASE WHEN admission_type = 'In-patient' THEN Patient__ID END) AS inpatient_count,
        COUNT(DISTINCT CASE WHEN admission_type = 'Out-patient' THEN Patient__ID END) AS outpatient_count
    FROM two_nf_patient_examination
    WHERE Patient__sex = 'Male'
) AS counts;
```

### Q1150 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Swaps which condition is the WHERE-level population scope vs which is the CASE-conditional numerator test (gold scopes by SEX='F' and counts birth-year>1930; predicted scopes by birth-year>1930 and counts sex='Female'), computing a different percentage; also 'Female' is an invented value (real value is 'F').

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_examination 
WHERE strftime('%Y', Patient__birthday) > '1930';
```

### Q1152 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type='Inpatient'/'Outpatient' are invented values; the real domain values are '+'/'-'.

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CAST(SUM(CASE WHEN Patient__admission_type = 'Inpatient' THEN 1 ELSE 0 END) AS REAL) /
    SUM(CASE WHEN Patient__admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio
FROM 
    two_nf_patient_examination
WHERE 
    Patient__diagnosis = 'SLE';
```

### Q1153 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References Examination__diagnosis, which doesn't exist in two_nf_patient_laboratory; the correct (and available) column is Patient__diagnosis.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.Diagnosis, T2.Date FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 30609
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Examination__diagnosis, Laboratory__Date 
FROM two_nf_patient_laboratory 
WHERE Patient__ID = '30609';
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Laboratory__lactate_dehydrogenase > 171 uses a wrong/invented threshold instead of gold's specified > 500.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__birthday 
FROM two_nf_patient_laboratory 
WHERE Laboratory__lactate_dehydrogenase > 171;
```

### Q1156 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Substitutes Examination__thrombosis_degree > 0 for the requested Examination__russell_viper_venom_time = '+' (RVVT) -- unrelated columns.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID, strftime('%Y', 'now') - strftime('%Y', Patient__birthday) AS age
FROM two_nf_patient_examination
WHERE Examination__thrombosis_degree > 0;
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree='severe' is an invented categorical value; the real column is an integer degree and gold needs the value 2.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__diagnosis
FROM two_nf_patient_examination
WHERE Examination__thrombosis_degree = 'severe';
```

### Q1162 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses Patient__first_hospital_visit_date ('First Date') instead of the requested Patient__first_record_date ('Description'); also uses invented values 'Female'/'Outpatient' instead of 'F'/'-'.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_examination
WHERE Patient__sex = 'Female'
  AND strftime('%Y', Patient__first_hospital_visit_date) = '1997'
  AND Patient__admission_type = 'Outpatient';
```

### Q1164 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree='most serious' and sex='female' are invented values; the real values are the integer 1 and 'F' respectively.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID)
FROM `Patient` AS T1
JOIN `Examination` AS T2 ON T1.ID = T2.ID
WHERE T1.`SEX` = 'F'
  AND STRFTIME('%Y', T2.`Examination Date`) = '1997'
  AND T2.`Thrombosis` = 1;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_examination
WHERE Examination__thrombosis_degree = 'most serious' AND Examination__examination_date LIKE '1997%' AND Patient__sex = 'female';
```

### Q1166 (simple, retrieval) — **Nesting problem** (Wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's UNION fallback branch (for when the target patient has no non-null Symptoms record) entirely; also uses MIN(birthday) instead of gold's MAX(birthday), selecting the oldest patient instead of the youngest.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Examination__symptoms, Patient__diagnosis
FROM two_nf_patient_examination
WHERE Patient__birthday = (
    SELECT MIN(Patient__birthday)
    FROM two_nf_patient_examination
)
```

### Q1168 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Computes age using today's date ('now') instead of the requested 'First Date' (Patient__first_hospital_visit_date) as the reference point; also uses MAX(Date) as an aggregate instead of gold's ORDER BY Birthday ASC, Date DESC LIMIT 1 to pick one specific record.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    MAX(Laboratory__Date) AS last_laboratory_date,
    strftime('%Y', 'now') - strftime('%Y', Patient__birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', Patient__birthday)) AS age_at_first_hospital_visit
FROM 
    two_nf_patient_laboratory
WHERE 
    Patient__diagnosis = 'SJS'
ORDER BY 
    Patient__birthday ASC
LIMIT 1;
```

### Q1169 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References a placeholder/nonexistent `normal_value` column (an unresolved guess left in the model's own SQL); no such column exists anywhere.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    CAST(SUM(CASE WHEN Patient__sex = 'Male' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    two_nf_patient_laboratory
WHERE 
    Laboratory__uric_acid > normal_value;  -- Assuming there's a normal value threshold for abnormal uric acid
```

### Q1171 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Compares the age-at-examination expression to < 0 instead of gold's < 18.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_examination
WHERE strftime('%Y', Examination__examination_date) BETWEEN '1990' AND '1993'
AND strftime('%Y', Examination__examination_date) - strftime('%Y', Patient__birthday) < 0;
```

### Q1175 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `hemoglobin` instead of `Laboratory__hemoglobin`.

**Gold SQL (original 3NF form):**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    Patient__birthday, 
    Patient__diagnosis
FROM 
    two_nf_patient_examination
WHERE 
    hemoglobin = (
        SELECT MAX(hemoglobin) 
        FROM two_nf_patient_examination
    )
```

### Q1179 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Selects an extra column (Examination__anticardiolipin_igg) beyond the single 'aCL IgM' column gold requests; all WHERE conditions otherwise correctly map to the same filters.

**Gold SQL (original 3NF form):**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Examination__anticardiolipin_igg, Examination__anticardiolipin_igm
FROM two_nf_patient_examination
WHERE Patient__diagnosis = 'SLE'
  AND Patient__first_record_date = '1994-02-19'
  AND Examination__examination_date = '1993-11-12';
```

### Q1185 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's percent-decrease-from-November formula (SUM(CASE WHEN Date LIKE '1981-11-%'...) vs '1981-12-%') with an unrelated (MAX-MIN)/day-count rate computed across the whole date range.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    (MAX(Laboratory__total_cholesterol) - MIN(Laboratory__total_cholesterol)) / 
    (julianday(MAX(Laboratory__Date)) - julianday(MIN(Laboratory__Date))) AS decrease_rate
FROM 
    two_nf_patient_laboratory
WHERE 
    Patient__birthday = '1959-02-18' 
    AND Laboratory__Date BETWEEN '1981-11-01' AND '1981-12-31';
```

### Q1187 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References Examination__examination_date (wrong table/column; Examination data isn't part of this cluster); the correct column is Laboratory__Date, already present in two_nf_patient_laboratory.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID
FROM two_nf_patient_laboratory
WHERE Examination__examination_date BETWEEN '1987-07-06' AND '1996-01-31'
  AND Laboratory__aspartate_aminotransferase > 30
  AND Laboratory__albumin < 4;
```

### Q1189 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** The correlated AVG(...) subquery drops gold's WHERE Thrombosis=2 AND ANA Pattern='S' scoping, computing the average over the entire table instead of just the matching subset.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_examination
WHERE Examination__thrombosis_degree = 2
  AND Examination__antinuclear_antibody_pattern = 'S'
  AND Examination__anticardiolipin_igm > (
    SELECT AVG(Examination__anticardiolipin_igm) * 1.2
    FROM two_nf_patient_examination
  )
```

### Q1192 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** admission_type='outpatient clinic' is an invented value (real value '-'); total_bilirubin BETWEEN 0.3 AND 1.2 replaces gold's simple `< 2.0` with an unrelated 'normal range' band, changing both the operator structure and the threshold.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID
FROM two_nf_patient_laboratory
WHERE Patient__admission_type = 'outpatient clinic'
  AND Laboratory__Date BETWEEN '1991-10-01' AND '1991-10-31'
  AND Laboratory__total_bilirubin BETWEEN 0.3 AND 1.2;
```

### Q1195 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='Female' is an invented value; the real value is 'F'.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(Laboratory__albumin)
FROM (
    SELECT DISTINCT Patient__ID, Laboratory__albumin
    FROM two_nf_patient_laboratory
    WHERE Patient__sex = 'Female'
      AND Laboratory__platelet_count > 400
      AND Patient__diagnosis = 'SLE'
)
```

### Q1198 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses Examination__diagnosis instead of the requested Patient__diagnosis (two different real columns on different source tables); also 'Female' is an invented value (real value 'F').

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_examination 
WHERE Patient__sex = 'Female' AND Examination__diagnosis = 'APS';
```

### Q1201 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='Female' is an invented value; the real value is 'F'.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_examination 
WHERE strftime('%Y', Patient__birthday) = '1980' AND Patient__diagnosis = 'RA';
```

### Q1205 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's sex-conditional thresholds (F: UA>6.5, M: UA>8.0) with a single generic 'normal range' check (BETWEEN 2.4 AND 7.0) that ignores patient sex entirely.

**Gold SQL (original 3NF form):**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    CASE 
        WHEN Laboratory__uric_acid BETWEEN 2.4 AND 7.0 THEN 'true'
        ELSE 'false'
    END AS is_normal_range
FROM 
    two_nf_patient_laboratory
WHERE 
    Patient__ID = 57266;
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='Male' is invented (should be 'M'); the GPT threshold is changed from gold's >=60 to an unrelated >40 (a generic 'abnormal ALT' reference value, not the question's literal threshold).

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID
FROM two_nf_patient_laboratory
WHERE Patient__sex = 'Male'
AND Laboratory__alanine_aminotransferase > 40;
```

### Q1209 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** The GPT threshold is changed from gold's >60 to an unrelated >40 (a generic reference-range value, not the question's literal threshold).

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__diagnosis
FROM two_nf_patient_laboratory
WHERE Laboratory__alanine_aminotransferase > 40
ORDER BY Patient__birthday ASC;
```

### Q1220 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** urea_nitrogen=10 is a wrong/invented exact value instead of gold's UN=29.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__birthday
FROM two_nf_patient_laboratory
WHERE Laboratory__urea_nitrogen = 10
```

### Q1225 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `total_bilirubin` instead of `Laboratory__total_bilirubin`; also the threshold ('< 0.3 OR > 1.2') differs from gold's '>= 2.0'.

**Gold SQL (original 3NF form):**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__sex, GROUP_CONCAT(Patient__ID) AS Patients
FROM two_nf_patient_laboratory
WHERE total_bilirubin < 0.3 OR total_bilirubin > 1.2
GROUP BY Patient__sex;
```

### Q1227 (moderate, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** two_nf_patient_laboratory has one row per (patient, lab-date), so a patient with multiple qualifying lab records is counted multiple times in AVG(age) (age is patient-constant, so duplicate rows skew the average); gold explicitly dedupes via `SELECT DISTINCT ID, age` before averaging. Also 'Male' is invented (real value 'M') and the T-CHO threshold is lowered to >200 instead of gold's >=250.

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(CAST((strftime('%Y', 'now') - strftime('%Y', Patient__birthday)) AS REAL))
FROM two_nf_patient_laboratory
WHERE Patient__sex = 'Male' AND Laboratory__total_cholesterol > 200;
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** triglyceride threshold changed from gold's >=200 to an unrelated >150.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__triglyceride > 150 AND 
      strftime('%Y', 'now') - strftime('%Y', Patient__birthday) > 50;
```

### Q1231 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='Male' is invented (should be 'M'); the CPK threshold is changed from gold's >=250 to an unrelated >100.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Patient__sex = 'Male'
  AND Patient__birthday BETWEEN '1936-01-01' AND '1956-12-31'
  AND Laboratory__creatinine_phosphokinase > 100;
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's single GLU>=180 threshold with a symmetric 'outside normal range' OR-condition (<70 OR >110), and replaces T-CHO<250 with an unrelated BETWEEN 120 AND 200 band -- both restructured away from the question's literal thresholds.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    Patient__ID, 
    Patient__sex, 
    strftime('%Y', 'now') - strftime('%Y', Patient__birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', Patient__birthday)) AS age
FROM 
    two_nf_patient_laboratory
WHERE 
    Laboratory__blood_glucose < 70 OR Laboratory__blood_glucose > 110
    AND Laboratory__total_cholesterol >= 120 AND Laboratory__total_cholesterol <= 200;
```

### Q1235 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `red_blood_cell_count` instead of `Laboratory__red_blood_cell_count`; also restructures gold's literal RBC<3.5 threshold into a '< AVG(...)' comparison.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT 
    Patient__ID, 
    strftime('%Y', 'now') - strftime('%Y', Patient__birthday) AS age, 
    Patient__diagnosis
FROM 
    two_nf_patient_laboratory
WHERE 
    red_blood_cell_count < (SELECT AVG(red_blood_cell_count) FROM two_nf_patient_laboratory)
```

### Q1238 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hemoglobin='Normal' is an invented categorical value; the real column is numeric and gold's actual condition is the range (10,17).

**Gold SQL (original 3NF form):**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex
FROM two_nf_patient_laboratory
WHERE Patient__diagnosis = 'SLE' AND Laboratory__hemoglobin = 'Normal'
ORDER BY Patient__birthday ASC
LIMIT 1;
```

### Q1239 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `p.hematocrit` instead of `p.Laboratory__hematocrit`; also the threshold (>45) differs from gold's >=52.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT p.Patient__ID, strftime('%Y', 'now') - strftime('%Y', p.Patient__birthday) AS age
FROM two_nf_patient_laboratory p
WHERE p.hematocrit > 45 AND p.Patient__ID IN (
    SELECT Patient__ID
    FROM two_nf_patient_laboratory
    GROUP BY Patient__ID
    HAVING COUNT(DISTINCT Laboratory__ID) >= 2
)
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count thresholds changed from gold's <100/>400 to unrelated <150/>450 (generic 'normal range' cutoffs, not the question's literal thresholds).

**Gold SQL (original 3NF form):**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    COUNT(DISTINCT CASE WHEN Laboratory__platelet_count < 150 THEN Patient__ID END) AS lower_than_normal,
    COUNT(DISTINCT CASE WHEN Laboratory__platelet_count > 450 THEN Patient__ID END) AS higher_than_normal
FROM 
    two_nf_patient_laboratory;
```

### Q1243 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References bare `prothrombin_time` instead of `Laboratory__prothrombin_time`; also references a nonexistent placeholder `normal_range_upper_limit`.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE strftime('%Y', 'now') - strftime('%Y', Patient__birthday) > 55 
AND prothrombin_time > normal_range_upper_limit;
```

### Q1247 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** white_blood_cell_count BETWEEN 4000 AND 11000 assumes the wrong scale/units for a column gold itself compares against small values (3.5/9.0); also drops the '>=450' branch of gold's FG OR-condition and changes the other branch's threshold from 150 to 200; 'Male' is also an invented value (real value 'M').

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Patient__sex = 'Male'
AND Laboratory__white_blood_cell_count BETWEEN 4000 AND 11000
AND Laboratory__fibrinogen < 200;
```

### Q1251 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_g threshold changed from gold's >=2000 to an unrelated >1.0.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE Laboratory__immunoglobulin_g > 1.0;
```

### Q1252 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** Queries FROM two_nf_patient_examination, which has no Laboratory__* columns at all; gold needs both Laboratory.IGG and Examination.Symptoms together, which live in two separate, non-overlapping clusters (two_nf_patient_laboratory and two_nf_patient_examination) -- this question cannot be fully answered from either single cluster without an explicit cross-cluster JOIN on Patient__ID, which the model did not attempt.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_examination
WHERE Laboratory__immunoglobulin_g = 'Normal' AND Examination__symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_a='Normal' is an invented categorical value; the real column is numeric and gold's actual condition is the range (80,500).

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE Laboratory__immunoglobulin_a = 'Normal' 
AND Patient__first_hospital_visit_date > '1990-01-01';
```

### Q1255 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_m='Abnormal' is an invented categorical value; the real column is numeric and gold's actual condition is IGM<=40 OR IGM>=400.

**Gold SQL (original 3NF form):**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT Patient__diagnosis
FROM two_nf_patient_laboratory
WHERE Laboratory__immunoglobulin_m = 'Abnormal'
GROUP BY Patient__diagnosis
ORDER BY COUNT(DISTINCT Patient__ID) DESC
LIMIT 1;
```

### Q1256 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Substitutes Laboratory__Date IS NULL (a NOT-NULL primary-key column, always false) for the requested Patient__first_record_date IS NULL (Description); also 'abnormal' is an invented value for CRP (real value is '+').

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE Laboratory__c_reactive_protein = 'abnormal' AND Laboratory__Date IS NULL;
```

### Q1257 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** creatinine threshold changed from gold's >=1.5 to an unrelated >1.2.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__creatinine > 1.2 AND Patient__birthday > DATE('now', '-70 years')
```

### Q1265 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_ribonuclear_protein='Normal' and admission_type='Admitted' are invented values; the real values are 'negative'/'0' and '+' respectively.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE Laboratory__anti_ribonuclear_protein = 'Normal' 
AND Patient__admission_type = 'Admitted';
```

### Q1267 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_sm='Normal' is an invented value; the real domain values are 'negative'/'0'/numeric titers, as gold's `IN ('negative','0')` correctly captures.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE Laboratory__anti_sm = 'Normal' 
AND Patient__ID NOT IN (
    SELECT Patient__ID 
    FROM two_nf_patient_examination 
    WHERE Examination__thrombosis_degree > 0
);
```

### Q1270 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_scl70='normal' and sex='female' are invented values; the real values are 'negative'/'0' and 'F' respectively.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__anti_scl70 = 'normal'
AND Patient__sex = 'female'
AND Patient__ID NOT IN (
    SELECT Patient__ID
    FROM two_nf_patient_examination
    WHERE Examination__symptoms IS NOT NULL
);
```

### Q1275 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_centromere='normal', anti_ssb='normal', and sex='male' are all invented values; the real values are 'negative'/'0' and 'M' respectively.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__anti_centromere = 'normal' AND Laboratory__anti_ssb = 'normal' AND Patient__sex = 'male';
```

### Q1281 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** aspartate_aminotransferase threshold changed from gold's >=60 to an unrelated >40; also uses MIN instead of MAX for the birthday selection, picking the oldest patient instead of gold's youngest.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT MIN(Patient__birthday)
FROM two_nf_patient_laboratory
WHERE Laboratory__aspartate_aminotransferase > 40
```

### Q1302 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References Examination__thrombosis_degree in a query FROM two_nf_patient_laboratory, which has no Examination__* columns; gold needs both Laboratory.CPK and Examination.KCT/RVVT/LAC together, which live in two separate, non-overlapping clusters -- this question cannot be fully answered from either single cluster without an explicit cross-cluster JOIN on Patient__ID.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__creatinine_phosphokinase BETWEEN 10 AND 200
AND Examination__thrombosis_degree > 0;
```

---

## toxicology (38 failures)

### Q197 (moderate, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** Groups by bond__molecule_id and uses COUNT(*) to approximate oxygen-atom count, but COUNT(*) counts connected-table (bond-endpoint) rows matching 'either side is O', not the true per-atom oxygen count gold's SUM(element='o') computes -- an O-O bond undercounts to 1 instead of 2, and an O atom in multiple bonds is over-counted; no simple DISTINCT fixes this, it needs a proper per-atom dedup. Also bond_type='single'/element='O' are invented values (real '-'/'o').

**Gold SQL (original 3NF form):**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(oxygen_count)
FROM (
    SELECT DISTINCT bond__molecule_id, COUNT(*) AS oxygen_count
    FROM two_nf_connected
    WHERE bond__bond_type = 'single' AND (atom_1__element = 'O' OR atom_2__element = 'O')
    GROUP BY bond__molecule_id
)
```

### Q198 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** The derived subquery only exposes molecule__molecule_id and single_bond_count; molecule__label is never carried into the outer scope, so the outer WHERE molecule__label='carcinogenic' fails with 'no such column'. Also bond_type='single'/label='carcinogenic' are invented values (real '-'/'+').

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(single_bond_count)
FROM (
    SELECT DISTINCT molecule__molecule_id, COUNT(*) AS single_bond_count
    FROM two_nf_connected
    WHERE bond__bond_type = 'single'
    GROUP BY molecule__molecule_id
)
WHERE molecule__label = 'carcinogenic';
```

### Q200 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects molecule__label instead of the requested molecule_id; also bond_type='triple'/label LIKE '%carcinogenic%' are invented values (real domain: '#' and '+').

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT molecule__label
FROM two_nf_connected
WHERE bond__bond_type = 'triple' AND molecule__label LIKE '%carcinogenic%'
```

### Q201 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='DOUBLE' and element='C' are invented/wrong-case values (real domain: '=' and lowercase 'c'); also restricts to atom_1 endpoints only instead of gold's broader 'all atoms belonging to a molecule that has a double bond' scope.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT atom_1__atom_id) 
FROM two_nf_connected 
WHERE bond__bond_type = 'DOUBLE';
```

### Q206 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label against a bond-id-shaped value ('TR004_8_9') instead of the requested connected__bond_id; also selects both atom_1__element and atom_2__element (2 columns) instead of gold's single element column.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM two_nf_connected 
WHERE molecule__label = 'TR004_8_9';
```

### Q207 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects both atom_1__element and atom_2__element (2 columns) instead of gold's single 'element' column (one row per connected-table entry, which already spans both bond endpoints once flattened); also bond_type='double' is invented (real '=').

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element
FROM two_nf_connected
WHERE bond__bond_type = 'double'
```

### Q208 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** 'H' is an invented uppercase value (real lowercase 'h'); also restructures gold's atom-count-per-label aggregation into COUNT(DISTINCT connected__atom_id) (bond-endpoint grain, atom_1-side only), a different and incomplete counting basis.

**Gold SQL (original 3NF form):**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT molecule__label
FROM two_nf_connected
WHERE atom_1__element = 'H' OR atom_2__element = 'H'
GROUP BY molecule__label
ORDER BY COUNT(DISTINCT connected__atom_id) DESC
LIMIT 1
```

### Q212 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's tie-preserving `HAVING COUNT(*) = (SELECT MIN(cnt) FROM (...))` comparison into a plain `ORDER BY COUNT(...) ASC LIMIT 1`, which would silently drop any tied elements; also 'carcinogenic' with `!=` is an invented, nonsensical substitution for label='-'.

**Gold SQL (original 3NF form):**

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

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT atom_1__element
FROM two_nf_connected
WHERE molecule__label != 'carcinogenic'
GROUP BY atom_1__element
ORDER BY COUNT(DISTINCT atom_1__atom_id) ASC
LIMIT 1;
```

### Q215 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Requires atom_1 AND atom_2 to jointly be I/S on the same bond (a wrong, far more restrictive AND/OR structure) instead of gold's two independent per-atom CASE WHEN counts across all atoms in bond_type='-' molecules; 'I'/'S' are also wrong-case invented values (real lowercase 'i'/'s') and 'single' is invented (real '-').

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    COUNT(DISTINCT atom_1__atom_id) AS iodine_count,
    COUNT(DISTINCT atom_2__atom_id) AS sulfur_count
FROM 
    two_nf_connected
WHERE 
    (atom_1__element = 'I' AND atom_2__element = 'S')
    OR
    (atom_1__element = 'S' AND atom_2__element = 'I')
    AND
    bond__bond_type = 'single';
```

### Q218 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Restructures gold's '100 minus %-of-molecules-containing-F' (molecule grain) into a %-of-bond-rows-with-neither-endpoint-F computation (bond grain) -- a different entity and different logic entirely; also 'carcinogenic' is an invented value (real '+').

**Gold SQL (original 3NF form):**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element != 'F' AND atom_2__element != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM two_nf_connected 
WHERE molecule__label = 'carcinogenic'
```

### Q219 (challenging, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** Numerator SUM(CASE WHEN label='carcinogenic'...) counts two_nf_connected rows (many per molecule) rather than distinct molecules, while the denominator correctly uses COUNT(DISTINCT molecule_id); COUNT(DISTINCT CASE WHEN...THEN molecule_id END) would fix the mismatch. Also 'carcinogenic'/'triple' are invented values (real '+'/'#').

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN molecule__label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM two_nf_connected 
WHERE bond__bond_type = 'triple';
```

### Q220 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label = 'TR000' instead of the requested molecule__molecule_id = 'TR000' -- label holds '+'/'-' values, not molecule identifiers.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element
FROM two_nf_connected
WHERE molecule__label = 'TR000'
ORDER BY atom_1__element ASC
LIMIT 3;
```

### Q226 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label = 'TR008' instead of molecule__molecule_id = 'TR008'; also bond_type='DOUBLE' is invented (real '=').

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN bond__bond_type = 'DOUBLE' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT connected__bond_id) AS percentage_double_bonds
FROM two_nf_connected
WHERE molecule__label = 'TR008';
```

### Q227 (simple, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** Uses the connected-grain two_nf_connected table instead of the molecule-grain molecule table; SUM(CASE WHEN label='carcinogenic'...) counts rows (many per molecule) instead of distinct molecules, while the denominator correctly uses COUNT(DISTINCT molecule_id) -- COUNT(DISTINCT CASE WHEN...THEN molecule_id END) would fix it. Also 'carcinogenic' is invented (real '+').

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN molecule__label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) AS percentage_carcinogenic
FROM two_nf_connected;
```

### Q228 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label = 'TR206' instead of molecule__molecule_id = 'TR206'; also 'H' is an invented uppercase value (real lowercase 'h'), and only atom_1-side atoms are considered, missing atom_2.

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / 
       COUNT(DISTINCT atom_1__atom_id) AS percentage_hydrogen
FROM two_nf_connected
WHERE molecule__label = 'TR206';
```

### Q230 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label = 'TR060' instead of the requested molecule__molecule_id = 'TR060'.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element, molecule__label 
FROM two_nf_connected 
WHERE molecule__label = 'TR060';
```

### Q231 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label = 'TR010' instead of the requested molecule__molecule_id = 'TR010'.

**Gold SQL (original 3NF form):**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT bond__bond_type
FROM two_nf_connected
WHERE molecule__label = 'TR010'
GROUP BY bond__bond_type
ORDER BY COUNT(DISTINCT connected__bond_id) DESC
LIMIT 1;
```

### Q232 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects molecule__label instead of the requested molecule_id; bond_type='single' is invented (real '-'), and 'NOT LIKE %carcinogenic%' is a vacuous substitution for label='-' since no real label value contains that substring.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT molecule__label
FROM two_nf_connected
WHERE bond__bond_type = 'single'
AND molecule__label NOT LIKE '%carcinogenic%'
ORDER BY molecule__label ASC
LIMIT 3;
```

### Q234 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** atom_1__atom_id is TEXT-typed like 'TR009_12', not the bare integer 12 compared here; also drops the 'OR atom_id2=...' branch entirely and substitutes molecule__label (wrong column) for part of the original atom_id string.

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT connected__bond_id) 
FROM two_nf_connected 
WHERE atom_1__atom_id = 12 AND molecule__label = 'TR009';
```

### Q236 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects atom_1__element/atom_2__element instead of the requested connected__atom_id/connected__atom_id2 identifier columns.

**Gold SQL (original 3NF form):**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT bond__bond_type, atom_1__element, atom_2__element
FROM two_nf_connected
WHERE bond__bond_id = 'TR001_6_9';
```

### Q239 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** connected__atom_id is TEXT (e.g. 'TR000_19'), not matched by the bare integer 19 used here; also selects COUNT(DISTINCT atom_id2) instead of the requested COUNT(bond_id), and drops gold's SUBSTR(atom_id,-2)='19' suffix-matching logic (which matches any atom number ending in 19, not only atoms literally numbered 19).

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT COUNT(DISTINCT connected__atom_id2) 
FROM two_nf_connected 
WHERE connected__atom_id = 19;
```

### Q240 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label = 'TR004' instead of the requested molecule__molecule_id = 'TR004'.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM two_nf_connected 
WHERE molecule__label = 'TR004';
```

### Q242 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects molecule__label instead of the requested molecule_id; also atom_1__atom_id BETWEEN 21 AND 25 compares the TEXT atom_id (e.g. 'TR000_21') against bare integers, which never matches as intended.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT molecule__label 
FROM two_nf_connected 
WHERE atom_1__atom_id BETWEEN 21 AND 25 AND molecule__label LIKE '%carcinogenic%'
```

### Q243 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects bond__bond_type instead of the requested bond_id; atom_1__element='Phosphorus'/atom_2__element='Nitrogen' are invented spelled-out values (real lowercase codes 'p'/'n').

**Gold SQL (original 3NF form):**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT bond__bond_type 
FROM two_nf_connected 
WHERE atom_1__element = 'Phosphorus' AND atom_2__element = 'Nitrogen';
```

### Q244 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's tie-preserving `WHERE cnt = (SELECT MAX(cnt) FROM sub)` comparison into a plain `ORDER BY COUNT(...) DESC LIMIT 1`, which would silently drop any tied molecules; also bond_type='double' is invented (real '=').

**Gold SQL (original 3NF form):**

```sql
with sub as ( SELECT T.molecule_id, COUNT(T.bond_type) as cnt
 FROM bond AS T WHERE T.bond_type = '=' GROUP BY T.molecule_id 
) 
SELECT T1.label FROM molecule AS T1 INNER JOIN sub
 AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.cnt = (select max(cnt) from sub)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT molecule__label
FROM two_nf_connected
WHERE bond__bond_type = 'double'
GROUP BY molecule__molecule_id
ORDER BY COUNT(DISTINCT bond__bond_id) DESC
LIMIT 1;
```

### Q245 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** 'iodine' is an invented spelled-out value (real lowercase 'i'); restricts to atom_1-side atoms only (missing atom_2's iodine atoms); and averages per-atom bond-count ratios instead of gold's overall COUNT(bond_id)/COUNT(atom_id) ratio-of-totals.

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT AVG(bond_count) 
FROM (
    SELECT DISTINCT atom_1__atom_id, COUNT(connected__bond_id) AS bond_count 
    FROM two_nf_connected 
    WHERE atom_1__element = 'iodine' 
    GROUP BY atom_1__atom_id
)
```

### Q247 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes `connected__atom_id2 IS NULL` (an artifact of the FULL OUTER JOIN chain) for gold's `atom_id NOT IN (SELECT atom_id FROM connected)`, a structurally different and semantically unrelated condition.

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element 
FROM two_nf_connected 
WHERE connected__atom_id2 IS NULL
```

### Q248 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label='TR041' instead of the requested molecule__molecule_id='TR041'; also selects both atom_1__atom_id and atom_2__atom_id when gold only wants the connected table's own atom_id column; bond_type='triple' is also invented (real '#').

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__atom_id, atom_2__atom_id
FROM two_nf_connected
WHERE bond__bond_type = 'triple' AND molecule__label = 'TR041';
```

### Q249 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule__label against a bond-id-shaped value instead of the requested connected__bond_id = 'TR144_8_19'; also selects both atom_1__element and atom_2__element instead of gold's single element column.

**Gold SQL (original 3NF form):**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM two_nf_connected 
WHERE molecule__label = 'TR144_8_19';
```

### Q253 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects both atom_1__element and atom_2__element (2 columns, paired per row) instead of gold's single flattened 'element' column; also bond_type='triple' is invented (real '#').

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element
FROM two_nf_connected
WHERE bond__bond_type = 'triple'
```

### Q255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** The CASE WHEN condition checks bond_type='single' (redundant with the WHERE clause) instead of gold's molecule__label='+' condition, making the numerator always equal the denominator (a degenerate 100% result); bond_type='single' is also an invented value (real '-').

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN bond__bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT bond__bond_id) AS proportion_carcinogenic
FROM two_nf_connected
WHERE bond__bond_type = 'single';
```

### Q260 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses SUM(DISTINCT atom_id) on a TEXT-typed atom_id column instead of gold's COUNT(*), a fundamentally wrong aggregate/expression; also restructures the AND-of-two-independent-subqueries into a single OR-based row filter, and 'P'/'Br' are invented-case values (real lowercase 'p'/'br').

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT SUM(DISTINCT atom_1__atom_id) + SUM(DISTINCT atom_2__atom_id) AS total_atoms
FROM two_nf_connected
WHERE bond__bond_type = 'triple' AND (atom_1__element = 'P' OR atom_2__element = 'Br');
```

### Q263 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a GROUP BY molecule__label gold doesn't have, producing one row per molecule instead of gold's single overall percentage; also 'Cl' and 'single' are invented/wrong-case values (real 'cl'/'-').

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    molecule__label, 
    (COUNT(CASE WHEN atom_1__element = 'Cl' THEN atom_1__atom_id END) + 
     COUNT(CASE WHEN atom_2__element = 'Cl' THEN atom_2__atom_id END)) * 100.0 / 
    COUNT(DISTINCT connected__atom_id) AS chlorine_percentage
FROM 
    two_nf_connected
WHERE 
    bond__bond_type = 'single'
GROUP BY 
    molecule__label;
```

### Q268 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects both atom_1__element and atom_2__element (2 columns) instead of gold's single 'element' column -- verified empirically: gold returns 2 single-value rows ('c','o'), predicted returns 2 two-column rows ('c,o' and 'o,c').

**Gold SQL (original 3NF form):**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM two_nf_connected 
WHERE connected__bond_id = 'TR001_10_11';
```

### Q273 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Denominator uses COUNT(DISTINCT molecule_id) (counting molecules) instead of gold's atom-count denominator (COUNT(element), i.e. counting atoms); also 'Cl'/'carcinogenic' are invented values (real 'cl'/'+').

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM two_nf_connected 
WHERE molecule__label = 'carcinogenic';
```

### Q281 (challenging, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's GROUP BY element (and its COUNT(*) aggregation) entirely, substituting an arbitrary LIMIT 3 OFFSET 3 pagination instead; also drops the SUBSTR(atom_id,-2)='_4' filter and uses the invented value 'carcinogenic'.

**Gold SQL (original 3NF form):**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT molecule__molecule_id, atom_2__element
FROM two_nf_connected
WHERE molecule__label = 'carcinogenic'
ORDER BY molecule__molecule_id, atom_2__atom_id
LIMIT 3 OFFSET 3;
```

### Q282 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an unwanted *100 scaling gold doesn't have, turning a 0-1 ratio into a 0-100 percentage; also 'H' is an invented uppercase value (real lowercase 'h') and only atom_1-side atoms are considered.

**Gold SQL (original 3NF form):**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT 
    molecule__label, 
    CAST(SUM(CASE WHEN atom_1__element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(atom_1__atom_id) AS hydrogen_ratio
FROM 
    two_nf_connected
WHERE 
    molecule__molecule_id = 'TR006'
GROUP BY 
    molecule__label;
```

### Q327 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects molecule__label instead of the requested molecule_id; the label condition ('NOT LIKE %carcinogenic%') is vacuous since the real label domain is just '+'/'-', and only atom_1-side atoms are counted, missing atom_2.

**Gold SQL (original 3NF form):**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL (against two_nf_* cluster table):**

```sql
SELECT DISTINCT molecule__label
FROM two_nf_connected
WHERE molecule__label NOT LIKE '%carcinogenic%'
GROUP BY molecule__molecule_id
HAVING COUNT(DISTINCT atom_1__atom_id) > 5;
```

---

