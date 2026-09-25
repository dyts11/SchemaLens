# Qwen2.5-Coder-14B - L1.S3 -- hand-classified failures (n=317)

Every failure was read by hand and classified against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used. L1 replaces the 3NF schema with a single denormalised wide table `one_nf_0` per database (see `preprocess_data/to_1nf/specs.py`); the harness's `gold_sql` column is always the original 3NF BIRD query (executed against the 3NF database by the harness), so each entry's classification reasoning is based on a constructed reference query against the actual `one_nf_0` wide table the model targeted -- the gold_sql shown below is still the original 3NF form for readability, but the bug diagnosis in 'Reason' accounts for the wide-table translation, including checking `src/column_aliases.py` before calling any renamed column wrong, and checking for Fan-out row-duplication from `one_nf_0`'s FULL OUTER JOIN chain (measured fan-out ratios range from ~1x for toxicology to ~1300x for student_club -- see error_taxonomy.md's Fan-out category). Many classifications were additionally verified empirically by executing the gold query against the original 3NF SQLite database and an adapted form of the predicted query against the `__1nf.sqlite` wide table and diffing the actual result sets. Grouped by database, sorted by question id.

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

### Q5 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** COUNT DISTINCT uses schools__national_center_for_education_statistics_school_id instead of gold's CDSCode; Virtual='Yes' also wrong, and adds an invented Magnet='No' condition

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT `T2`.`CDSCode`)
FROM `satscores` AS T1
JOIN `schools`  AS T2 ON T1.`cds` = T2.`CDSCode`
WHERE T2.`Virtual` = 'F'
  AND T1.`AvgScrMath` > 400 AND rtype = 'S'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT one_nf_0.schools__national_center_for_education_statistics_school_id)
FROM one_nf_0
JOIN (
    SELECT satscores__county_district_school_code
    FROM one_nf_0
    WHERE satscores__average_score_math > 400
    GROUP BY satscores__county_district_school_code
) AS high_math_schools
ON one_nf_0.schools__county_district_school_code = high_math_schools.satscores__county_district_school_code
WHERE one_nf_0.schools__Virtual = 'Yes' AND one_nf_0.schools__Magnet = 'No';
```

### Q11 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** HAVING SUM(frpm__enrollment_k12) > 500 drops gold's '+ Enrollment (Ages 5-17)' term entirely

**Gold SQL (original 3NF form):**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__county_district_school_code
FROM one_nf_0
GROUP BY schools__county_district_school_code
HAVING SUM(frpm__enrollment_k12) > 500;
```

### Q12 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing rtype='S' filter (precomputed percent column is a reasonable substitute for the manual ratio)

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT MAX(frpm__percent_eligible_free_ages_5_17)
FROM one_nf_0
WHERE satscores__number_scores_1500_or_above / satscores__number_test_takers > 0.3;
```

### Q17 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** frpm__charter_school_number substituted for gold's schools.CharterNum -- two different real columns; also wraps in an unwanted AVG/GROUP BY instead of gold's row-level RANK()

**Gold SQL (original 3NF form):**

```sql
SELECT CharterNum, AvgScrWrite, 
RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank 
FROM schools AS T1  INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds 
WHERE T2.AvgScrWrite > 499 AND CharterNum is not null AND rtype = 'S'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    frpm__charter_school_number, 
    AVG(satscores__average_score_writing) AS avg_writing_score, 
    RANK() OVER (ORDER BY AVG(satscores__average_score_writing) DESC) AS rank
FROM 
    one_nf_0
WHERE 
    satscores__average_score_writing > 499
GROUP BY 
    frpm__charter_school_number;
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** wraps the enrollment difference in ABS(), which gold doesn't have

**Gold SQL (original 3NF form):**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School, 
    schools__Street, 
    schools__City, 
    schools__Zip, 
    schools__State
FROM 
    one_nf_0
WHERE 
    ABS(frpm__enrollment_k12 - frpm__enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing rtype='S' filter

**Gold SQL (original 3NF form):**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__School 
FROM one_nf_0 
WHERE frpm__percent_eligible_free_k12 > 0.1 
AND satscores__number_scores_1500_or_above > 0;
```

### Q25 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools__County substituted for gold's schools.District; also missing rtype='S' filter

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School, 
    schools__funding_type
FROM 
    one_nf_0
WHERE 
    schools__County = 'Riverside'
GROUP BY 
    schools__School, 
    schools__funding_type
HAVING 
    AVG(satscores__average_score_math) > 400;
```

### Q26 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** satscores__percent_eligible_free_or_reduced_price_meal_ages_5_17 is a hallucinated combination -- that alias belongs to frpm (as a percent, not gold's count-based FRPM Count metric), not satscores; schools__State also substituted for gold's County

**Gold SQL (original 3NF form):**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School AS school_name,
    schools__Street AS street,
    schools__City AS city,
    schools__Zip AS zip,
    schools__State AS state,
    schools__mailing_street AS mailing_street,
    schools__mailing_city AS mailing_city,
    schools__mailing_zip_code AS mailing_zip_code,
    schools__mailing_state AS mailing_state
FROM 
    one_nf_0
WHERE 
    schools__State = 'Monterey' 
    AND satscores__percent_eligible_free_or_reduced_price_meal_ages_5_17 > 800;
```

### Q27 (moderate, retrieval) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** wraps AvgScrWrite in AVG()/GROUP BY School,Phone instead of gold's row-level projection

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School, 
    AVG(satscores__average_score_writing) AS average_score_writing, 
    schools__Phone
FROM 
    one_nf_0
WHERE 
    (schools__open_date > '1991-12-31' OR schools__closed_date < '2000-01-01')
GROUP BY 
    schools__School, 
    schools__Phone;
```

### Q28 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `error` · **Reason:** frpm__funding_type doesn't exist -- FundingType lives on schools, not frpm; subquery also references unprefixed enrollment_k12/enrollment_ages_5_17

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    frpm__school_name, 
    frpm__district_type
FROM 
    one_nf_0
WHERE 
    frpm__funding_type = 'Locally Funded' AND
    ABS(frpm__enrollment_k12 - frpm__enrollment_ages_5_17) > (
        SELECT 
            AVG(ABS(enrollment_k12 - enrollment_ages_5_17))
        FROM 
            one_nf_0
        WHERE 
            frpm__funding_type = 'Locally Funded'
    )
```

### Q31 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing 'School is not NULL' filter, which could shift which 2 rows land in the LIMIT 9,2 window

**Gold SQL (original 3NF form):**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT frpm__percent_eligible_free_k12
FROM one_nf_0
ORDER BY frpm__enrollment_k12 DESC
LIMIT 9, 2;
```

### Q32 (moderate, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** adds an extra schools__School column beyond gold's single-column ratio result

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School, 
    frpm__percent_eligible_free_or_reduced_price_meal_k12
FROM 
    one_nf_0
WHERE 
    schools__school_ownership_code = 66
ORDER BY 
    frpm__free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** WHERE x = (SELECT MAX(x)) with no LIMIT could return multiple tied rows where gold's ORDER BY DESC LIMIT 1 returns exactly one; also missing rtype='S' filter

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__admin_first_name_1, 
    schools__admin_last_name_1, 
    schools__admin_first_name_2, 
    schools__admin_last_name_2, 
    schools__admin_first_name_3, 
    schools__admin_last_name_3
FROM 
    one_nf_0
WHERE 
    satscores__number_scores_1500_or_above = (
        SELECT 
            MAX(satscores__number_scores_1500_or_above)
        FROM 
            one_nf_0
    )
```

### Q37 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** frpm's FRPM-eligibility percentage substituted for gold's satscores NumGE1500/NumTstTakr ratio -- an unrelated metric

**Gold SQL (original 3NF form):**

```sql
SELECT s.Street, s.City, s.State, s.Zip 
FROM schools s JOIN satscores sat ON s.CDSCode = sat.cds 
WHERE sat.NumTstTakr > 0 AND sat.NumGE1500 IS NOT NULL AND sat.NumTstTakr IS NOT NULL  AND rtype = 'S'
AND CAST(sat.NumGE1500 AS FLOAT) / CAST(sat.NumTstTakr AS FLOAT) =
 (SELECT MIN(CAST(NumGE1500 AS FLOAT) / CAST(NumTstTakr AS FLOAT)) 
 FROM satscores WHERE NumTstTakr > 0 AND NumGE1500 IS NOT NULL AND NumTstTakr IS NOT NULL AND rtype = 'S' )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__Street, 
    schools__City, 
    schools__State, 
    schools__Zip
FROM 
    one_nf_0
WHERE 
    frpm__percent_eligible_free_or_reduced_price_meal_k12 = (
        SELECT MIN(frpm__percent_eligible_free_or_reduced_price_meal_k12) 
        FROM one_nf_0
    )
```

### Q39 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** outer query references bare 'number_test_takers' without the required satscores__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(number_test_takers)
FROM (
    SELECT DISTINCT one_nf_0.schools__county_district_school_code, one_nf_0.satscores__number_test_takers
    FROM one_nf_0
    WHERE one_nf_0.schools__County = 'Fresno'
      AND one_nf_0.schools__open_date BETWEEN '1980-01-01' AND '1980-12-31'
)
```

### Q40 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing AvgScrRead IS NOT NULL and rtype='S' filters

**Gold SQL (original 3NF form):**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__Phone
FROM one_nf_0
WHERE schools__District = 'Fresno Unified'
ORDER BY satscores__average_score_reading ASC
LIMIT 1;
```

### Q41 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's RANK() OVER PARTITION BY cname (top-5 per county) replaced by a global ORDER BY County, score DESC LIMIT 5 with no window function at all; Virtual='Yes' also wrong

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__School, schools__County, satscores__average_score_reading
FROM one_nf_0
WHERE schools__Virtual = 'Yes'
ORDER BY schools__County, satscores__average_score_reading DESC
LIMIT 5;
```

### Q46 (simple, retrieval) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** adds an unwanted GROUP BY State / MAX(enrollment_k12) not in gold; drops the DOC=31 filter entirely and selects State instead of School

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__State, MAX(frpm__enrollment_k12) AS max_enrollment
FROM one_nf_0
GROUP BY schools__State
ORDER BY max_enrollment DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** adds an unwanted GROUP BY strftime('%m',...) monthly grouping not in gold's flat COUNT/12; also AVG(DISTINCT text_id) is a nonsensical aggregate and District substituted for the DOC=52 code

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(DISTINCT schools__county_district_school_code) AS avg_schools_opened
FROM one_nf_0
WHERE schools__County = 'Alameda' 
  AND schools__District = 'Elementary School District' 
  AND strftime('%Y', schools__open_date) = '1980'
GROUP BY strftime('%m', schools__open_date);
```

### Q48 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents combined status_type values ('Merged Unified/Elementary School District') instead of gold's separate StatusType='Merged' + DOC='54'/'52' codes; also wrongly applies the County filter to the denominator subquery

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN schools__status_type = 'Merged Unified School District' THEN schools__county_district_school_code END) AS REAL) /
       COUNT(DISTINCT CASE WHEN schools__status_type = 'Merged Elementary School District' THEN schools__county_district_school_code END) AS ratio
FROM one_nf_0
WHERE schools__County = 'Orange';
```

### Q50 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools__Street substituted for gold's MailStreet/mailing_street; also missing rtype='S' and AvgScrMath IS NOT NULL filters

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School, 
    schools__Street
FROM 
    one_nf_0
ORDER BY 
    satscores__average_score_math DESC
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** frpm__county_name/is_charter_school substituted for gold's schools.County/Charter; charter value type also wrong ('N' vs an integer flag)

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT frpm__county_district_school_code)
FROM one_nf_0
WHERE frpm__county_name = 'Los Angeles'
  AND frpm__is_charter_school = 'N'
  AND frpm__percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** frpm__district_name substituted for gold's schools.City; frpm__school_type substituted for gold's EdOpsCode; also uses COUNT DISTINCT instead of gold's SUM(Enrollment)

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT frpm__county_district_school_code)
FROM one_nf_0
WHERE frpm__academic_year = 2014
  AND frpm__district_name = 'Fremont'
  AND frpm__school_type = 'State Special School';
```

### Q77 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools__grade_span_offered substituted for gold's grade_span_served; value format also wrong ('Kindergarten to 9th grade' vs 'K-9')

**Gold SQL (original 3NF form):**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__School, 
    frpm__percent_eligible_free_ages_5_17
FROM 
    one_nf_0
WHERE 
    schools__County = 'Los Angeles' 
    AND schools__grade_span_offered = 'Kindergarten to 9th grade';
```

### Q79 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools__Charter='Yes' substituted for gold's Virtual='F' -- two different real columns

**Gold SQL (original 3NF form):**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT schools__County, COUNT(DISTINCT schools__national_center_for_education_statistics_school_id) AS school_count
FROM one_nf_0
WHERE schools__County IN ('San Diego', 'Santa Barbara') AND schools__Charter = 'Yes'
GROUP BY schools__County
ORDER BY school_count DESC
LIMIT 1;
```

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** ORDER BY Longitude DESC instead of gold's ORDER BY ABS(longitude) DESC

**Gold SQL (original 3NF form):**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__grade_span_offered 
FROM one_nf_0 
ORDER BY schools__Longitude DESC 
LIMIT 1;
```

### Q83 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** grade_span_offered = 'Kindergarten to 8th' (spelled-out) vs gold's coded 'K-8'

**Gold SQL (original 3NF form):**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT schools__City, COUNT(DISTINCT schools__School) AS school_count
FROM one_nf_0
WHERE schools__grade_span_offered = 'Kindergarten to 8th' AND frpm__national_school_lunch_program_provision_status = 'Multiple Provision Types'
GROUP BY schools__City;
```

### Q85 (moderate, retrieval) — **Other** (wrong aggregate function/scaling)

**Outcome:** `wrong_answer` · **Reason:** uses the precomputed frpm__percent_eligible_free_k12 column, which is plausibly on a different scale (0-1 fraction) than gold's explicit *100 computation

**Gold SQL (original 3NF form):**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT frpm__percent_eligible_free_k12, frpm__district_code
FROM one_nf_0
WHERE schools__admin_first_name_1 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools__instruction_level_name substituted for gold's DOC=54/SOC=62 numeric codes; City value also wrong ('San Bernardino City Unified' vs 'San Bernardino')

**Gold SQL (original 3NF form):**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    schools__admin_email_1 AS email1, 
    schools__admin_email_2 AS email2, 
    schools__admin_email_3 AS email3
FROM 
    one_nf_0
WHERE 
    schools__County = 'San Bernardino' 
    AND schools__City = 'San Bernardino City Unified' 
    AND schools__open_date BETWEEN '2009-01-01' AND '2010-12-31' 
    AND schools__instruction_level_name IN ('Intermediate/Middle School', 'Unified School');
```

---

## debit_card_specializing (26 failures)

### Q1471 (simple, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(CASE WHEN customers__currency=...) counts customer-level currency across the transactions_1k x yearmonth cartesian fan-out baked into one_nf_0 instead of COUNT(DISTINCT ... customer_id); also adds an unwanted *100 scaling factor gold doesn't have

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / 
       SUM(CASE WHEN customers__currency = 'CZK' THEN 1 ELSE 0 END) AS ratio
FROM one_nf_0;
```

### Q1472 (moderate, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** gasstations__segment substituted for gold's customers.Segment -- two different real 'Segment' columns; also drops the GROUP BY CustomerID/SUM(Consumption) entirely, ordering raw fanned-out rows instead

**Gold SQL (original 3NF form):**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT customers__customer_id
FROM one_nf_0
WHERE yearmonth__date LIKE '2012%' AND gasstations__segment = 'LAM'
ORDER BY yearmonth__consumption ASC
LIMIT 1;
```

### Q1473 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) applied to a YYYYMM text column returns NULL for every row; also drops the per-customer SUM-then-average subquery structure

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(yearmonth__consumption)
FROM (
    SELECT DISTINCT yearmonth__customer_id, yearmonth__consumption
    FROM one_nf_0
    WHERE customers__segment = 'SME' AND strftime('%Y', yearmonth__date) = '2013'
)
```

### Q1476 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', yearmonth__date) applied to a YYYYMM text column returns NULL for every row

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    SUM(CASE WHEN customers__currency = 'CZK' THEN yearmonth__consumption ELSE 0 END) -
    SUM(CASE WHEN customers__currency = 'EUR' THEN yearmonth__consumption ELSE 0 END) AS consumption_difference
FROM 
    one_nf_0
WHERE 
    strftime('%Y', yearmonth__date) = '2012';
```

### Q1479 (moderate, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(yearmonth__consumption) is inflated by the transactions_1k fan-out baked into one_nf_0 (each yearmonth row is duplicated once per that customer's transaction rows); also groups by the full date instead of gold's year substring

**Gold SQL (original 3NF form):**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT yearmonth__date
FROM one_nf_0
WHERE customers__currency = 'CZK'
GROUP BY yearmonth__date
ORDER BY SUM(yearmonth__consumption) DESC
LIMIT 1
```

### Q1480 (moderate, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** drops the required month-grouping/SUM entirely, picking a single fanned-out row via ORDER BY consumption DESC LIMIT 1 instead

**Gold SQL (original 3NF form):**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT yearmonth__date
FROM one_nf_0
WHERE customers__segment = 'SME' AND yearmonth__date LIKE '2013%'
ORDER BY yearmonth__consumption DESC
LIMIT 1
```

### Q1481 (challenging, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** AVG(yearmonth__consumption) is skewed by the transactions_1k fan-out weighting more-active customers' consumption more heavily; also drops gold's entire per-customer-average/segment-min CTE structure

**Gold SQL (original 3NF form):**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SELECT AVG(yearmonth__consumption) 
     FROM one_nf_0 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'SME') -
    (SELECT AVG(yearmonth__consumption) 
     FROM one_nf_0 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'LAM') AS diff_sme_lam,

    (SELECT AVG(yearmonth__consumption) 
     FROM one_nf_0 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'LAM') -
    (SELECT AVG(yearmonth__consumption) 
     FROM one_nf_0 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'KAM') AS diff_lam_kam,

    (SELECT AVG(yearmonth__consumption) 
     FROM one_nf_0 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'KAM') -
    (SELECT AVG(yearmonth__consumption) 
     FROM one_nf_0 
     WHERE yearmonth__date LIKE '2013%' 
       AND customers__currency = 'CZK' 
       AND customers__segment = 'SME') AS diff_kam_sme;
```

### Q1482 (challenging, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** the conditional SUM(consumption) computations are inflated by the transactions_1k fan-out; also restructures gold's single-row 3-column pivot into a 3-row GROUP BY segment output

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    customers__segment,
    ((SUM(CASE WHEN yearmonth__date LIKE '2013%' THEN yearmonth__consumption ELSE 0 END) -
      SUM(CASE WHEN yearmonth__date LIKE '2012%' THEN yearmonth__consumption ELSE 0 END)) /
     SUM(CASE WHEN yearmonth__date LIKE '2012%' THEN yearmonth__consumption ELSE 0 END)) * 100 AS percentage_change
FROM 
    one_nf_0
WHERE 
    customers__currency = 'EUR' AND
    customers__segment IN ('SME', 'LAM', 'KAM')
GROUP BY 
    customers__segment;
```

### Q1483 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** date BETWEEN '2013-08-01' AND '2013-11-30' (ISO format) vs gold's YYYYMM text bounds '201308'/'201311'

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT SUM(yearmonth__consumption) 
FROM one_nf_0 
WHERE yearmonth__customer_id = 6 
AND yearmonth__date BETWEEN '2013-08-01' AND '2013-11-30';
```

### Q1484 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare gas_station_id/country/segment without the required gasstations__ prefix -- doesn't exist in the wide table under those names

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SELECT COUNT(DISTINCT gas_station_id) 
     FROM one_nf_0 
     WHERE country = 'Czech Republic' AND segment = 'discount') -
    (SELECT COUNT(DISTINCT gas_station_id) 
     FROM one_nf_0 
     WHERE country = 'Slovakia' AND segment = 'discount') AS difference;
```

### Q1486 (simple, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(CASE WHEN currency=...) counts customer-level currency across the transactions_1k x yearmonth fan-out instead of COUNT(DISTINCT ... customer_id)

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    SUM(CASE WHEN customers__currency = 'CZK' THEN 1 ELSE 0 END) - 
    SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS difference
FROM 
    one_nf_0
WHERE 
    customers__segment = 'SME';
```

### Q1490 (moderate, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** numerator SUM(CASE WHEN consumption>46.73...) counts fanned-out rows instead of COUNT(DISTINCT CASE WHEN ... customer_id); denominator correctly uses COUNT(DISTINCT customer_id)

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN yearmonth__consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT yearmonth__customer_id) 
FROM 
    one_nf_0 
WHERE 
    customers__segment = 'LAM';
```

### Q1493 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare consumption/customer_id/date without the required yearmonth__ prefix -- doesn't exist in the wide table under those names

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customer_id) 
FROM 
    one_nf_0 
WHERE 
    date BETWEEN '2012-02-01' AND '2012-02-29';
```

### Q1498 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', yearmonth__date) applied to a YYYYMM text column returns NULL; also MAX(consumption) substituted for gold's SUM(...) GROUP BY month

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT MAX(yearmonth__consumption)
FROM one_nf_0
WHERE strftime('%Y', yearmonth__date) = '2012';
```

### Q1500 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** yearmonth__date (YYYYMM text) substituted for gold's transactions_1k.Date (daily-granularity, ISO-like) for the LIKE '2012-08-%' filter

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT products__description 
FROM one_nf_0 
WHERE yearmonth__date BETWEEN '2012-08-01' AND '2012-08-31';
```

### Q1505 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** currency = 'euro' vs gold's 'EUR'

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT customers__customer_id)
FROM one_nf_0
WHERE customers__currency = 'euro' AND yearmonth__consumption > 1000;
```

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country = 'Czech Republic' vs gold's 'CZE'

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT products__description 
FROM one_nf_0 
WHERE gasstations__country = 'Czech Republic';
```

### Q1507 (simple, retrieval) — **Other** (unclear/residual)

**Outcome:** `wrong_answer` · **Reason:** structurally matches gold (correct table/column/filter, DISTINCT used) -- no clear causal bug identifiable from the SQL text alone

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.Time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T2.ChainID = 11
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT transactions_1k__time 
FROM one_nf_0 
WHERE gasstations__chain_id = 11;
```

### Q1509 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country = 'Czech Republic' vs gold's 'CZE'

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(t.`TransactionID`)
FROM `transactions_1k` AS t
JOIN `gasstations` AS g
  ON t.`GasStationID` = g.`GasStationID`
WHERE g.`Country` = 'CZE'
  AND DATE(t.`Date`) > '2012-01-01';
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT transactions_1k__transaction_id) 
FROM one_nf_0 
WHERE gasstations__country = 'Czech Republic' 
AND transactions_1k__date > '2012-01-01';
```

### Q1524 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** transactions_1k__amount substituted for gold's Price

**Gold SQL (original 3NF form):**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT gasstations__country 
FROM one_nf_0 
WHERE transactions_1k__amount = 548.4 AND transactions_1k__date = '2012-08-24';
```

### Q1525 (simple, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** numerator SUM(CASE WHEN currency='EUR'...) counts rows inflated by the yearmonth fan-out (unconstrained by the Date filter) instead of COUNT(DISTINCT CASE WHEN ... customer_id)

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customers__customer_id) 
FROM 
    one_nf_0 
WHERE 
    transactions_1k__date = '2012-08-25';
```

### Q1526 (challenging, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** self-joins one_nf_0 AS y2012/y2013 as if it still had a separate 'yearmonth' table to alias -- the flattened wide table has no such structure to self-join this way

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    (y2012.consumption - y2013.consumption) / y2012.consumption AS consumption_decrease_rate
FROM 
    one_nf_0 AS y2012
JOIN 
    one_nf_0 AS y2013 
ON 
    y2012.customers__customer_id = y2013.customers__customer_id
WHERE 
    y2012.yearmonth__date = '2012-08-25' 
    AND y2012.transactions_1k__amount = 634.8 
    AND y2013.yearmonth__date = '2013-08-25';
```

### Q1528 (simple, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** customers__segment substituted for gold's gasstations.Segment; denominator also uses COUNT(DISTINCT customer_id) instead of counting SVK gas stations

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SUM(CASE WHEN customers__segment = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT customers__customer_id)) AS percentage_premium
FROM 
    one_nf_0
WHERE 
    gasstations__country = 'SVK';
```

### Q1529 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare amount/date without the required transactions_1k__ prefix -- doesn't exist in the wide table under those names

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    SUM(amount) AS total_spent,
    SUM(CASE WHEN date LIKE '2012-08%' THEN amount ELSE 0 END) AS spent_in_august_2012
FROM 
    one_nf_0
WHERE 
    customers__customer_id = 38508;
```

### Q1531 (moderate, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(transactions_1k__amount)/AVG(transactions_1k__price) both corrupted by the yearmonth fan-out baked into one_nf_0; also uses the wrong formula for both the top-customer subquery and the weighted average

**Gold SQL (original 3NF form):**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    customers__customer_id, 
    AVG(transactions_1k__price) AS avg_price_per_item, 
    customers__currency
FROM 
    one_nf_0
WHERE 
    customers__customer_id = (
        SELECT 
            customers__customer_id
        FROM 
            one_nf_0
        GROUP BY 
            customers__customer_id
        ORDER BY 
            SUM(transactions_1k__amount) DESC
        LIMIT 1
    )
GROUP BY 
    customers__customer_id, 
    customers__currency;
```

### Q1533 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects customers__segment instead of gold's yearmonth.Consumption; also drops the /Amount division from the Price/Amount>29 filter

**Gold SQL (original 3NF form):**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT customers__segment
FROM one_nf_0
WHERE transactions_1k__amount > 29.00
  AND transactions_1k__product_id = 5
  AND yearmonth__date LIKE '2012-08%'
```

---

## european_football_2 (39 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Match__season = 2016 (bare integer) should be the string '2015/2016' -- season is stored as text 'YYYY/YYYY', so this never matches and blocks every row

**Gold SQL (original 3NF form):**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT League__name
FROM one_nf_0
WHERE Match__season = 2016
GROUP BY League__name
ORDER BY SUM(Match__home_team_goals + Match__away_team_goals) DESC
LIMIT 1;
```

### Q1028 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Match__season = 2010 should be the string '2009/2010', which blocks every row from matching regardless of the fact that gold's HAVING COUNT(*) = (SELECT MAX(win_count) FROM (...)) tie-preserving pattern is also collapsed into a plain GROUP BY/ORDER BY DESC LIMIT 1

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT team_away__team_long_name
FROM one_nf_0
WHERE Match__league_id = (
    SELECT League__id
    FROM one_nf_0
    WHERE League__name = 'Scotland Premier League'
) AND Match__season = 2010 AND Match__away_team_goals > Match__home_team_goals
GROUP BY team_away__team_long_name
ORDER BY COUNT(*) DESC
LIMIT 1;
```

### Q1029 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds a DISTINCT gold doesn't have; if the true top-4 buildUpPlaySpeed values include ties, gold's raw (non-distinct) top-4 list can differ from predicted's deduplicated list

**Gold SQL (original 3NF form):**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_speed
FROM one_nf_0
ORDER BY Team_Attributes__buildup_play_speed DESC
LIMIT 4;
```

### Q1030 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Match__season = 2016 (bare integer) should be the string '2015/2016' -- season is stored as text, so this never matches

**Gold SQL (original 3NF form):**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT League__name
FROM one_nf_0
WHERE Match__season = 2016 AND Match__home_team_goals = Match__away_team_goals
GROUP BY League__name
ORDER BY COUNT(DISTINCT Match__id) DESC
LIMIT 1;
```

### Q1031 (challenging, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes__id -- treats a wide-table column-name fragment as a standalone table; only one_nf_0 exists in the 1NF schema

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T2.Birthday) - CASE
    WHEN strftime('%m-%d','now') < strftime('%m-%d', Birthday) THEN 1
    ELSE 0
  END AS age FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE STRFTIME('%Y',t1."date") >= '2013' AND STRFTIME('%Y',t1."date") <= '2015' AND t1.sprint_speed >= 97
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player__birthday 
FROM Player_Attributes__id 
WHERE Player_Attributes__sprint_speed >= 97 
AND Player_Attributes__date BETWEEN '2013-01-01' AND '2015-12-31';
```

### Q1032 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id)... GROUP BY league_id)) tie-preserving pattern into a plain GROUP BY/ORDER BY DESC LIMIT 1, which could return a different league if multiple are tied for most matches

**Gold SQL (original 3NF form):**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT League__name, COUNT(DISTINCT Match__id) AS match_count
FROM one_nf_0
GROUP BY League__name
ORDER BY match_count DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN 50 AND 60 is inclusive of both endpoints, while gold's buildUpPlaySpeed > 50 AND < 60 strictly excludes them -- rows with exactly 50 or 60 are wrongly included

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Team_Attributes__team_fifa_api_id
FROM one_nf_0
WHERE Team_Attributes__buildup_play_speed BETWEEN 50 AND 60;
```

### Q1036 (challenging, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** the subquery's AVG(Team_Attributes__buildup_play_passing) is a cross-team global average computed over one_nf_0's fanned-out rows, where each team's 2012 attribute value is repeated once per home match that team played that season -- teams with more home matches bias the threshold; empirically verified: predicted returns 136 teams above threshold vs gold's clean 128, and a plain DISTINCT can't fix a cross-row global AVG like this, it would need a dedup-by-team subquery first

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT team_home__team_long_name
FROM one_nf_0
WHERE Team_Attributes__date LIKE '2012%'
AND Team_Attributes__buildup_play_passing > (
    SELECT AVG(Team_Attributes__buildup_play_passing)
    FROM one_nf_0
    WHERE Team_Attributes__date LIKE '2012%'
);
```

### Q1037 (challenging, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes__id -- treats a wide-table column-name fragment as a standalone table; only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT player_api_id) 
FROM Player_Attributes__id 
WHERE strftime('%Y', birthday) BETWEEN '1987' AND '1992';
```

### Q1039 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'long_shots' without the required Player_Attributes__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(long_shots)
FROM (
    SELECT DISTINCT Player_Attributes__id, long_shots
    FROM one_nf_0
    WHERE Player__player_name = 'Ahmed Samir Farag'
)
```

### Q1040 (moderate, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** though grouped and averaged correctly per player (which neutralizes the home_player_1 match-count fan-out for a within-player AVG), empirically the predicted query returns 9 of gold's 10 top players by avg heading_accuracy but swaps one borderline name ('Naldo' vs 'Sami Hyypiae') -- one_nf_0's FULL OUTER JOIN chain subtly perturbs the tied/near-tied rank-10 boundary in a way no DISTINCT-level patch fixes

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player__player_name
FROM one_nf_0
WHERE Player__height > 180
GROUP BY Player__player_api_id
ORDER BY AVG(Player_Attributes__heading_accuracy) DESC
LIMIT 10;
```

### Q1068 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'player_api_id', 'height', and 'date' without their required Player__/Player_Attributes__ prefixes -- don't exist in the wide table under those names

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(t2.overall_rating) AS avg_rating
FROM `Player` AS t1
JOIN `Player_Attributes` AS t2 ON t1.player_api_id = t2.player_api_id
WHERE t1.height > 170
  AND strftime('%Y', t2.`date`) BETWEEN '2010' AND '2015';
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(overall_rating)
FROM (
    SELECT DISTINCT player_api_id, overall_rating
    FROM one_nf_0
    WHERE height > 170 AND date BETWEEN '2010-01-01' AND '2015-12-31'
)
```

### Q1076 (challenging, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes__id (x2 subqueries) -- treats a wide-table column-name fragment as a standalone table; only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
  (SELECT AVG(ball_control) 
   FROM Player_Attributes__id 
   WHERE player_name = 'Abdou Diallo') -
  (SELECT AVG(ball_control) 
   FROM Player_Attributes__id 
   WHERE player_name = 'Aaron Appindangoye') AS difference;
```

### Q1078 (simple, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** adds an extra Player__birthday column beyond gold's single player_name column

**Gold SQL (original 3NF form):**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT Player__player_name, Player__birthday
FROM one_nf_0
WHERE Player__player_name IN ('Aaron Lennon', 'Abdelaziz Barrada')
ORDER BY Player__birthday ASC
LIMIT 1;
```

### Q1080 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes -- that table doesn't exist standalone in the 1NF schema, only one_nf_0 with Player_Attributes__ prefixed columns; attacking_work_rate = 'high' should also be 'low'

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Player_Attributes__player_api_id) 
FROM Player_Attributes 
WHERE Player_Attributes__preferred_foot = 'left' AND Player_Attributes__attacking_work_rate = 'high';
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra Player_Attributes__attacking_work_rate = 'High' condition gold doesn't have; the defensive_work_rate value also has wrong case ('High' vs the real lowercase 'high')

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Player__id)
FROM one_nf_0
WHERE Player__birthday < '1986-01-01'
AND Player_Attributes__attacking_work_rate = 'High'
AND Player_Attributes__defensive_work_rate = 'High';
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (...)) tie-preserving pattern into a plain GROUP BY/ORDER BY DESC LIMIT 1, which could return a different league if multiple are tied for most matches in that season

**Gold SQL (original 3NF form):**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT League__name
FROM one_nf_0
WHERE Match__season = '2008/2009'
GROUP BY League__name
ORDER BY COUNT(DISTINCT Match__id) DESC
LIMIT 1;
```

### Q1094 (challenging, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes__ (x3) -- a malformed, non-existent table name; only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
  ((SELECT overall_rating FROM Player_Attributes__ WHERE player_name = 'Ariel Borysiuk') - 
   (SELECT overall_rating FROM Player_Attributes__ WHERE player_name = 'Paulin Puel')) * 100.0 / 
  (SELECT overall_rating FROM Player_Attributes__ WHERE player_name = 'Paulin Puel') AS percentage_difference;
```

### Q1096 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'player_api_id' without the required Player__/Player_Attributes__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Pietro Marino'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(overall_rating)
FROM (
    SELECT DISTINCT player_api_id, overall_rating
    FROM one_nf_0
    WHERE player_name = 'Pietro Marino'
)
```

### Q1098 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** ORs in team_away__team_long_name = 'Ajax' rows, but Team_Attributes in one_nf_0 is only ever joined to the home team (home_team_api_id) -- on rows where Ajax is the away team, chance_creation_passing reflects a different (home) team's attributes entirely, not Ajax's

**Gold SQL (original 3NF form):**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT MAX(Team_Attributes__chance_creation_passing), Team_Attributes__chance_creation_passing_class
FROM one_nf_0
WHERE team_home__team_long_name = 'Ajax' OR team_away__team_long_name = 'Ajax';
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Player_Attributes__date = '2016-06-23' never matches -- stored date values carry a ' 00:00:00' time suffix (e.g. '2016-06-23 00:00:00'), so a bare equality always returns zero rows; gold uses SUBSTR(date,1,10)='2016-06-23' to correctly truncate before comparing

**Gold SQL (original 3NF form):**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT Player__player_name
FROM one_nf_0
WHERE Player_Attributes__overall_rating = 77
  AND Player_Attributes__date = '2016-06-23'
ORDER BY Player__birthday ASC
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Player_Attributes__date = '2016-02-04' never matches -- stored date values carry a ' 00:00:00' time suffix, so a bare equality always returns zero rows; gold uses SUBSTR(date,1,10)='2016-02-04'

**Gold SQL (original 3NF form):**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player_Attributes__overall_rating 
FROM one_nf_0 
WHERE Player__player_name = 'Aaron Mooy' 
AND Player_Attributes__date = '2016-02-04';
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Player_Attributes__date = '2015-05-01' never matches -- stored date values carry a ' 00:00:00' time suffix; gold uses date LIKE '2015-05-01%'

**Gold SQL (original 3NF form):**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player_Attributes__attacking_work_rate
FROM one_nf_0
WHERE Player__player_name = 'Francesco Migliore' AND Player_Attributes__date = '2015-05-01';
```

### Q1107 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects Match__date (the match fixture date) instead of gold's Player_Attributes date (the attribute snapshot date on which crossing was recorded) -- two different real date columns

**Gold SQL (original 3NF form):**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Match__date
FROM one_nf_0
WHERE Player__player_name = 'Kevin Constant'
ORDER BY Player_Attributes__crossing DESC, Match__date ASC
LIMIT 1;
```

### Q1110 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Team_Attributes__date = '2010-02-22' never matches -- stored date values carry a ' 00:00:00' time suffix; gold uses date LIKE '2010-02-22%'

**Gold SQL (original 3NF form):**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_passing_class 
FROM one_nf_0 
WHERE team_home__team_long_name = 'FC Lorient' 
AND Team_Attributes__date = '2010-02-22';
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Team_Attributes__date = '2015-09-10' never matches -- stored date values carry a ' 00:00:00' time suffix; gold uses date LIKE '2015-09-10%'

**Gold SQL (original 3NF form):**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Team_Attributes__defence_aggression_class 
FROM one_nf_0 
WHERE team_home__team_long_name = 'Hannover 96' 
AND Team_Attributes__date = '2015-09-10';
```

### Q1114 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'overall_rating' in the SELECT list without the required Player_Attributes__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(overall_rating)
FROM (
    SELECT DISTINCT Player_Attributes__id, overall_rating
    FROM one_nf_0
    WHERE Player__player_name = 'Marko Arnautovic'
      AND Player_Attributes__date BETWEEN '2007-02-22' AND '2016-04-21'
)
```

### Q1115 (challenging, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes__ (x3) -- a malformed, non-existent table name; only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
  ((SELECT overall_rating 
    FROM Player_Attributes__ 
    WHERE player_name = 'Landon Donovan' 
      AND date = '2013-07-12') - 
   (SELECT overall_rating 
    FROM Player_Attributes__ 
    WHERE player_name = 'Jordan Bowery' 
      AND date = '2013-07-12')) * 100.0 / 
  (SELECT overall_rating 
   FROM Player_Attributes__ 
   WHERE player_name = 'Jordan Bowery' 
     AND date = '2013-07-12') AS percentage_difference;
```

### Q1122 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by Player_Attributes__strength instead of gold's overall_rating -- a completely different attribute; also collapses gold's tie-preserving 'rating = MAX(...)' pattern into a single-row ORDER BY/LIMIT 1

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT Player__player_name 
FROM one_nf_0 
ORDER BY Player_Attributes__strength DESC 
LIMIT 1;
```

### Q1124 (moderate, retrieval) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** the model's response includes a leftover ```sql markdown fence as literal SQL text and was cut off mid-generation, producing an unparseable/unterminated statement; it also treats 'Player_Attributes' as a standalone table, which doesn't exist in the flattened schema

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL (against one_nf_0):**

```sql
```sql
SELECT DISTINCT Player__player_name
FROM one_nf_0
WHERE Player_Attributes__attacking_work_rate = 'High'
AND (
    Match__home_player_1_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_2_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_3_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_4_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_5_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_6_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_7_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_8_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_9_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_10_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = 'High'
    )
    OR Match__home_player_11_api_id IN (
        SELECT Player_Attributes__player_api_id
        FROM Player_Attributes
        WHERE Player_Attributes__attacking_work_rate = '
```

### Q1134 (simple, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes__id (x2) -- treats a wide-table column-name fragment as a standalone table; only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    (SELECT jumping FROM Player_Attributes__id WHERE id = 6) - 
    (SELECT jumping FROM Player_Attributes__id WHERE id = 23) AS difference;
```

### Q1135 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'preferred_foot' and 'potential' without the required Player_Attributes__ prefix -- don't exist in the wide table under those names

**Gold SQL (original 3NF form):**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player_Attributes__id
FROM one_nf_0
WHERE preferred_foot = 'right'
ORDER BY potential ASC
LIMIT 4;
```

### Q1136 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** FROM Player_Attributes -- that table doesn't exist standalone; only one_nf_0 exists with Player_Attributes__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Player_Attributes__player_api_id)
FROM Player_Attributes
WHERE Player_Attributes__crossing = (
    SELECT MAX(crossing)
    FROM Player_Attributes
)
AND Player_Attributes__preferred_foot = 'left'
AND Player_Attributes__attacking_work_rate = 'high';
```

### Q1139 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Match__date = '2008-09-24' never matches -- stored date values carry a ' 00:00:00' time suffix, needing LIKE '2008-09-24%'; League__name = 'Belgian Jupiler League' is also a wrong value (the real name is 'Belgium Jupiler League')

**Gold SQL (original 3NF form):**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    Match__home_team_goals, 
    Match__away_team_goals 
FROM 
    one_nf_0 
WHERE 
    Match__date = '2008-09-24' 
    AND League__name = 'Belgian Jupiler League';
```

### Q1141 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** ORs in team_away__team_long_name = 'KSV Cercle Brugge' rows, but Team_Attributes only ever reflects the home team (home_team_api_id) -- rows where this team played away return a different team's buildUpPlaySpeedClass value entirely

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Team_Attributes__buildup_play_speed_class 
FROM one_nf_0 
WHERE team_home__team_long_name = 'KSV Cercle Brugge' 
OR team_away__team_long_name = 'KSV Cercle Brugge';
```

### Q1144 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds an unwanted DISTINCT that collapses gold's natural duplicate (finishing, curve) rows -- repeated across the max-weight player's multiple attribute snapshots with unchanged values -- down to unique pairs, changing the row multiset gold's raw, non-deduplicated query returns

**Gold SQL (original 3NF form):**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player_Attributes__finishing, Player_Attributes__curve
FROM one_nf_0
WHERE Player__weight = (SELECT MAX(Player__weight) FROM one_nf_0);
```

### Q1145 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Match__season = 2015 (bare integer) should be the string '2015/2016' -- season is stored as text, so this never matches

**Gold SQL (original 3NF form):**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT League__name, COUNT(DISTINCT Match__id) AS game_count
FROM one_nf_0
WHERE Match__season = 2015
GROUP BY League__name
ORDER BY game_count DESC
LIMIT 4;
```

### Q1147 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by Player_Attributes__strength instead of gold's overall_rating -- a completely different attribute; also collapses gold's tie-preserving 'rating = MAX(...)' pattern into a single-row ORDER BY/LIMIT 1

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Player__player_name 
FROM one_nf_0 
ORDER BY Player_Attributes__strength DESC 
LIMIT 1;
```

### Q1148 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'height' without the required Player__ prefix -- doesn't exist in the wide table under that name; also substitutes Player_Attributes__strength for gold's overall_rating > 70

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN height < 180 AND Player_Attributes__strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Player__id) 
FROM one_nf_0;
```

---

## financial (25 failures)

### Q89 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the required account__statement_frequency = 'POPLATEK PO OBRATU' filter entirely and substitutes an unrelated card__issued_date > trans__date condition gold doesn't have; district__region also has wrong case ('East Bohemia' vs 'east Bohemia')

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT account__account_id)
FROM one_nf_0
WHERE card__issued_date > trans__date
AND district__region = 'East Bohemia';
```

### Q92 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'district_id' without a table prefix -- doesn't exist in the wide table under that name (needs client__district_id or district__district_id)

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T2.district_id)  FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' AND T2.A11 BETWEEN 6000 AND 10000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT district_id) 
FROM one_nf_0 
WHERE gender = 'F' AND average_salary BETWEEN 6000 AND 10000;
```

### Q93 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** district__region = 'North Bohemia' should be lowercase 'north Bohemia' -- same column/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT client__client_id)
FROM one_nf_0
WHERE client__gender = 'M'
  AND district__region = 'North Bohemia'
  AND district__average_salary > 8000;
```

### Q95 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'client_id' (outer WHERE and subquery SELECT) without a table prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT account__account_id
FROM one_nf_0
WHERE client_id = (
    SELECT client_id
    FROM one_nf_0
    ORDER BY client__birth_date ASC, district__average_salary DESC
    LIMIT 1
)
```

### Q98 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** account__statement_frequency = 'weekly' should be the untranslated code 'POPLATEK TYDNE'

**Gold SQL (original 3NF form):**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT account__account_id
FROM one_nf_0
WHERE loan__date LIKE '1997%'
AND account__statement_frequency = 'weekly'
ORDER BY loan__amount ASC
LIMIT 1;
```

### Q100 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against separate 'client' and 'district' tables that don't exist in the 1NF schema -- only one_nf_0 exists, with client__/district__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT client__client_id)
FROM one_nf_0
JOIN client ON one_nf_0.client__client_id = client.client_id
JOIN district ON one_nf_0.account__district_id = district.district_id
WHERE client.gender = 'F'
AND client.birth_date < '1950-01-01'
AND district.district_name = 'Sokolov';
```

### Q115 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** district__region = 'South Bohemia' should be lowercase 'south Bohemia', which blocks every row from matching; independently, COUNT(client_id)/COUNT(CASE...) without DISTINCT would also be corrupted by the trans-anchored fan-out duplicating clients across their transaction/loan/order/card rows, and GROUP BY district_id substitutes for gold's GROUP BY on number_inhabitants (A4), though unlikely to change which single district is selected

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (COUNT(CASE WHEN client__gender = 'M' THEN client__client_id END) * 100.0 / COUNT(client__client_id)) AS male_client_percentage
FROM 
    one_nf_0
WHERE 
    district__region = 'South Bohemia'
GROUP BY 
    district__district_id
ORDER BY 
    district__number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's exact date-matched balance differences (balance on 1998-12-27 minus balance on 1993-03-22, divided by the 1993-03-22 balance) with an unrelated MAX-minus-MIN-balance-over-days-elapsed rate formula; also adds an extra loan__status = 'A' filter gold doesn't have

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (MAX(trans__balance_after_transaction) - MIN(trans__balance_after_transaction)) / 
    (julianday('1998-12-27') - julianday('1993-03-22')) AS balance_increase_rate
FROM 
    one_nf_0
WHERE 
    trans__account_id = (
        SELECT 
            loan__account_id
        FROM 
            one_nf_0
        WHERE 
            loan__date = '1993-07-05' AND loan__status = 'A'
        LIMIT 1
    )
    AND trans__date BETWEEN '1993-03-22' AND '1998-12-27';
```

### Q117 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** loan__status = 'fully_paid' should be 'A' -- a fabricated code (real codes are A/B/C/D), which zeroes the numerator entirely regardless of the fact that SUM(loan__amount) is also uncontrolled for the trans-anchored fan-out duplicating each loan across its account's transaction rows

**Gold SQL (original 3NF form):**

```sql
SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SUM(CASE WHEN loan__status = 'fully_paid' THEN loan__amount ELSE 0 END) * 100.0 / SUM(loan__amount)) AS percentage_fully_paid
FROM 
    one_nf_0;
```

### Q118 (moderate, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(CASE WHEN loan__status = 'A' ...) counts one_nf_0 rows -- each qualifying loan duplicated once per its account's transaction rows via the trans-anchored fan-out -- instead of COUNT(DISTINCT CASE WHEN status='C' THEN account_id END); loan__status should also be 'C' not 'A' (a real but wrong code)

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN loan__status = 'A' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT loan__account_id) AS percentage_running
FROM 
    one_nf_0
WHERE 
    loan__amount < 100000;
```

### Q125 (challenging, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs against fictional tables client__c/disp__d/district__d that don't exist -- the model appears to have confused wide-table column-name fragments for separate joinable tables; only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT d.unemployment_rate_1996 - d.unemployment_rate_1995 AS unemployment_rate_increment
FROM one_nf_0 l
JOIN client__c ON l.loan__account_id = c.account__account_id
JOIN disp__d ON c.client_id = d.disp__client_id
JOIN district__d ON d.disp__district_id = di.district_id
WHERE l.loan__status = 'Running' AND l.loan__amount > 0;
```

### Q129 (moderate, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against a separate 'client' and 'district' table that don't exist in the 1NF schema

**Gold SQL (original 3NF form):**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT d.district_name
FROM one_nf_0 t
JOIN client c ON t.trans__account_id = c.client_id
JOIN district d ON c.client_district_id = d.district_id
WHERE t.trans__type = 'Withdrawal'
AND t.trans__date BETWEEN '1996-01-01' AND '1996-01-31'
AND t.trans__transaction_type_code != 'Credit card'
ORDER BY t.trans__amount DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters trans__date instead of gold's loan__date for the loan-date-range condition; also uses an invented frequency value ('Monthly' vs 'POPLATEK MESICNE') and adds an extra loan__status = 'approved' condition not in gold

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT loan__loan_id)
FROM one_nf_0
WHERE trans__date BETWEEN '1995-01-01' AND '1997-12-31'
  AND loan__amount >= 250000
  AND account__statement_frequency = 'Monthly'
  AND loan__status = 'approved';
```

### Q137 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops district_id=1 and loan.status IN ('C','D') filtering entirely, substituting an unrelated trans__bank='Branch location 1' / trans__transaction_type_code='running contract' condition -- real columns answering a completely different question

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT account__account_id) 
FROM one_nf_0 
WHERE trans__bank = 'Branch location 1' 
AND trans__transaction_type_code = 'running contract';
```

### Q138 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'district_id' in the ranking subquery without a table prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A15 = (SELECT T3.A15 FROM district AS T3 ORDER BY T3.A15 DESC LIMIT 1, 1)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT client__client_id)
FROM one_nf_0
WHERE client__gender = 'M'
AND client__district_id = (
    SELECT district_id
    FROM one_nf_0
    GROUP BY district_id
    ORDER BY SUM(district__number_crimes_1995) DESC
    LIMIT 1 OFFSET 1
)
```

### Q145 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects disp__client_id instead of gold's trans__account_id; also swaps the operation='VYBER KARTOU' filter for the wrong transaction_type_code column with an invented value 'credit_card'

**Gold SQL (original 3NF form):**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT disp__client_id
FROM one_nf_0
WHERE trans__date LIKE '1998%'
AND trans__amount < (
    SELECT AVG(trans__amount)
    FROM one_nf_0
    WHERE trans__date LIKE '1998%'
)
AND trans__transaction_type_code = 'credit_card';
```

### Q149 (challenging, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** account__type doesn't exist -- 'type' lives on disp (disp__type), not account; the WHERE logic is also restructured into an unrelated loan-absence subquery instead of gold's disp.type <> 'OWNER' filter

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT account__type
FROM one_nf_0
WHERE account__account_id NOT IN (
    SELECT loan__account_id
    FROM one_nf_0
)
AND district__average_salary BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters district__number_inhabitants > 4000 instead of gold's number_crimes_1995 (A15) > 4000; also adds an unwanted GROUP BY district_id that turns gold's single overall AVG into a per-district result, and drops the district_id IN (SELECT...) subquery scoping for the account-date condition

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(district__number_crimes_1995)
FROM one_nf_0
WHERE district__number_inhabitants > 4000
AND account__date >= '1997-01-01'
GROUP BY district__district_id;
```

### Q159 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** operation = 'Withdrawal' should be 'VYBER'; also adds an extra transaction_type_code = 'Cash' condition not in gold, and returns only 3 trans columns instead of all of them (gold selects T4.*)

**Gold SQL (original 3NF form):**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT trans__transaction_id, trans__date, trans__amount
FROM one_nf_0
WHERE trans__transaction_operation = 'Withdrawal' AND trans__transaction_type_code = 'Cash' AND disp__client_id = 3356;
```

### Q168 (moderate, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(CASE WHEN gender='F'...)/COUNT(client_id) counts client rows duplicated by the trans-anchored fan-out (a client's row repeats once per their transaction/loan/order/card row in one_nf_0) instead of COUNT(DISTINCT CASE WHEN gender='F' THEN client_id END)/COUNT(DISTINCT client_id) -- clients with more transactions get over-weighted in both the numerator and denominator

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN client__gender = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(client__client_id) AS percentage_women
FROM 
    one_nf_0
WHERE 
    district__average_salary > 10000;
```

### Q169 (challenging, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(loan__amount) for both the 1996 and 1997 conditional sums is inflated by the trans-anchored fan-out duplicating each loan across its account's transaction rows, in a way a simple DISTINCT can't fix (would need a per-loan dedup subquery); the numerator subtraction order is also flipped (1996-1997 instead of gold's 1997-1996) and the disp.type='OWNER' filter is dropped entirely

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SUM(CASE WHEN loan__date BETWEEN '1996-01-01' AND '1996-12-31' THEN loan__amount ELSE 0 END) -
     SUM(CASE WHEN loan__date BETWEEN '1997-01-01' AND '1997-12-31' THEN loan__amount ELSE 0 END)) /
    SUM(CASE WHEN loan__date BETWEEN '1996-01-01' AND '1996-12-31' THEN loan__amount ELSE 0 END) AS growth_rate
FROM 
    one_nf_0
WHERE 
    client__gender = 'M';
```

### Q173 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** aggregates trans__amount (actual transactions) instead of gold's order__amount (standing payment orders) -- a different real table entirely; also filters trans__transaction_operation='Debit' as an invented substitute for the k_symbol grouping

**Gold SQL (original 3NF form):**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    account__statement_frequency, 
    SUM(trans__amount) AS total_debit_amount
FROM 
    one_nf_0
WHERE 
    account__account_id = 3 AND 
    trans__transaction_operation = 'Debit' AND 
    trans__amount = 3539
GROUP BY 
    account__statement_frequency;
```

### Q186 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps which condition scopes the population (WHERE gender='M') vs which is counted (CASE frequency='weekly') relative to gold's WHERE frequency='POPLATEK TYDNE' + CASE-counted gender='M'; the invented frequency value 'weekly' (real code is 'POPLATEK TYDNE') makes the numerator deterministically zero regardless

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN account__statement_frequency = 'weekly' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT client__client_id) 
FROM one_nf_0 
WHERE client__gender = 'M';
```

### Q192 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's account__statement_frequency = 'POPLATEK PO OBRATU' filter with an unrelated trans__transaction_operation = 'Statement issuance' condition; loan__status = 'Running' is also not a real status code (real codes are A/B/C/D, and gold wants C or D)

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(loan__amount)
FROM (
    SELECT DISTINCT loan__loan_id, loan__amount
    FROM one_nf_0
    WHERE loan__status = 'Running' AND trans__transaction_operation = 'Statement issuance'
)
```

### Q194 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** self-joins one_nf_0 under aliases c/d/disp/card/loan as if they were separate tables, then references c.client_id (bare, unprefixed) which doesn't exist -- should be c.client__client_id

**Gold SQL (original 3NF form):**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT c.client_id, strftime('%Y', 'now') - strftime('%Y', c.birth_date) AS age
FROM one_nf_0 c
JOIN one_nf_0 d ON c.district_id = d.district_id
JOIN one_nf_0 disp ON c.client_id = disp.client_id
JOIN one_nf_0 card ON disp.disposition_id = card.disposition_id
JOIN one_nf_0 loan ON c.client_id = loan.account_id
WHERE card.type = 'high_level' AND loan.status = 'A';
```

---

## formula_1 (49 failures)

### Q846 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's qualifying-based ORDER BY q1 DESC LIMIT 5 ranking entirely, replacing it with an unrelated status__status = 'Eliminated' filter -- 'Eliminated' is not even a real status value in the status domain, and has nothing to do with q1 lap times

**Gold SQL (original 3NF form):**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__driver_ref_name 
FROM one_nf_0 
WHERE results__race_id = 20 AND status__status = 'Eliminated';
```

### Q847 (simple, retrieval) — **Other** (missing NULLS LAST handling)

**Outcome:** `wrong_answer` · **Reason:** predicted's plain ORDER BY qualifying_2_time ASC puts NULL q2 values first (SQLite's default null-ordering), picking a NULL-valued row instead of gold's NULLS LAST-adjusted smallest real q2 time

**Gold SQL (original 3NF form):**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__last_name
FROM one_nf_0
WHERE qualifying__race_id = 19
ORDER BY qualifying__qualifying_2_time ASC
LIMIT 1;
```

### Q854 (simple, retrieval) — **Other** (missing NULL filter)

**Outcome:** `wrong_answer` · **Reason:** one_nf_0's FULL OUTER JOIN chain introduces a spurious (NULL, NULL) row for some other 'Australian Grand Prix'-named race whose circuit doesn't align cleanly; gold's INNER JOIN silently drops such unmatched rows, but the flat one_nf_0 scan preserves them (empirically verified: predicted returns an extra all-NULL row gold doesn't have)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT circuits__latitude, circuits__longitude 
FROM one_nf_0 
WHERE races__name = 'Australian Grand Prix';
```

### Q857 (simple, retrieval) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT lets the results-anchored fan-out (~27x) multiply the single (lat, lng) row for 'Abu Dhabi Grand Prix' across every result/qualifying/lap/pitstop record of that race; empirically verified the underlying values are correct and adding DISTINCT reproduces gold's single row

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT circuits__latitude, circuits__longitude 
FROM one_nf_0 
WHERE races__name = 'Abu Dhabi Grand Prix';
```

### Q859 (simple, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'qualifying_1_time' without the required qualifying__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT T1.q1 FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 354 AND T2.forename = 'Bruno' AND T2.surname = 'Senna'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT qualifying_1_time 
FROM one_nf_0 
WHERE drivers__first_name = 'Bruno' 
AND drivers__last_name = 'Senna' 
AND qualifying__race_id = 354;
```

### Q861 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time = '0:01:54' assumes a wrong time format (real values look like '1:54.xxx', not '0:01:54') and uses exact equality instead of gold's LIKE '1:54%' prefix match -- never matches

**Gold SQL (original 3NF form):**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__number 
FROM one_nf_0 
WHERE qualifying__race_id = 903 AND qualifying__qualifying_3_time = '0:01:54';
```

### Q865 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results__position IS NOT NULL instead of gold's results__time IS NOT NULL -- different real columns; also drops gold's drivers.dob IS NOT NULL condition

**Gold SQL (original 3NF form):**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM one_nf_0
WHERE results__race_id = 592 AND results__position IS NOT NULL
ORDER BY drivers__date_of_birth ASC
LIMIT 1;
```

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** lapTimes__time = '0:01:27' assumes a wrong time format (real values look like '1:27.xxx') and uses exact equality instead of gold's LIKE '1:27%' prefix match -- never matches

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name, drivers__url
FROM one_nf_0
WHERE lapTimes__race_id = 161 AND lapTimes__time = '0:01:27';
```

### Q868 (simple, retrieval) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT lets the results-anchored fan-out multiply the single (location, lat, lng) row for 'Malaysian Grand Prix' across every result/qualifying/lap/pitstop record of that race; also selects an extra circuits__location column beyond gold's two (lat, lng)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT circuits__location, circuits__latitude, circuits__longitude 
FROM one_nf_0 
WHERE races__name = 'Malaysian Grand Prix';
```

### Q872 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time = '0:01:33' assumes a wrong time format and uses exact equality instead of gold's LIKE '1:33%' prefix match -- never matches

**Gold SQL (original 3NF form):**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__driver_code
FROM one_nf_0
WHERE results__race_id = 45
AND qualifying__qualifying_3_time = '0:01:33';
```

### Q877 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results__position IS NOT NULL instead of gold's results__time IS NOT NULL -- a different real column; also selects an extra drivers__date_of_birth column beyond gold's two

**Gold SQL (original 3NF form):**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name, drivers__date_of_birth
FROM one_nf_0
WHERE results__race_id = 872 AND results__position IS NOT NULL
ORDER BY drivers__date_of_birth DESC
LIMIT 1;
```

### Q879 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** MAX(results__fastest_lap_speed) compares the TEXT-typed column lexicographically instead of numerically -- missing gold's CAST(... AS REAL) before taking the max, which can select the wrong 'fastest' value

**Gold SQL (original 3NF form):**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__nationality
FROM one_nf_0
WHERE results__fastest_lap_speed = (
    SELECT MAX(results__fastest_lap_speed)
    FROM one_nf_0
);
```

### Q880 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'fastest_lap_speed' without the required results__ prefix -- doesn't exist in the wide table under that name

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    ((MAX(fastest_lap_speed) - MIN(fastest_lap_speed)) / MIN(fastest_lap_speed)) * 100 AS percentage_faster
FROM (
    SELECT DISTINCT 
        results__race_id, 
        fastest_lap_speed
    FROM 
        one_nf_0
    WHERE 
        drivers__first_name = 'Paul' 
        AND drivers__last_name = 'di Resta'
        AND results__race_id IN (853, 854)
) AS subquery;
```

### Q881 (moderate, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** adds a GROUP BY drivers__driver_id that gold doesn't have -- since each driver has exactly one result per race, this produces a per-driver 0%/100% breakdown instead of gold's single overall completion percentage across all results in the race

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT drivers__first_name, drivers__last_name, 
       CAST(SUM(CASE WHEN results__position IS NOT NULL THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(results__result_id) AS completion_rate
FROM one_nf_0
WHERE races__date = '1983-07-16'
GROUP BY drivers__driver_id;
```

### Q884 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** the races__date LIKE (subquery) compares against a full date string with no wildcard, so it behaves as an exact-date match instead of gold's same-year-and-month logic (STRFTIME('%m',...) comparison) -- excludes other races in the same month on a different day

**Gold SQL (original 3NF form):**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT races__name 
FROM one_nf_0 
WHERE races__year = (SELECT MIN(races__year) FROM one_nf_0) 
AND races__date LIKE (SELECT MIN(races__date) FROM one_nf_0 WHERE races__year = (SELECT MIN(races__year) FROM one_nf_0))
```

### Q892 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'points' without the required results__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT d.`forename`, d.`surname`, SUM(r.`points`) AS total_points
FROM `results` r
JOIN `drivers` d ON d.`driverId` = r.`driverId`
GROUP BY r.`driverId`
ORDER BY total_points DESC
LIMIT 1;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT drivers__first_name, drivers__last_name, SUM(points) AS total_points
FROM one_nf_0
GROUP BY drivers__driver_id
ORDER BY total_points DESC
LIMIT 1;
```

### Q894 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects and sorts by lapTimes__time (a text time string) instead of gold's milliseconds (integer) -- a different real column entirely

**Gold SQL (original 3NF form):**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT lapTimes__time, drivers__first_name, drivers__last_name, races__name
FROM one_nf_0
ORDER BY lapTimes__time ASC
LIMIT 1;
```

### Q895 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'time' without the required lapTimes__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.milliseconds) FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.year = 2009 AND T1.name = 'Malaysian Grand Prix'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(time) 
FROM (
    SELECT DISTINCT lapTimes__time 
    FROM one_nf_0 
    WHERE drivers__first_name = 'Lewis' 
    AND drivers__last_name = 'Hamilton' 
    AND races__year = 2009 
    AND races__name = 'Malaysian Grand Prix'
)
```

### Q896 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** uses results__position instead of gold's driverStandings.position (per-race finishing position vs. championship-standings position after that race are different concepts/tables); also adds a bogus circuits__circuit_id = 1 filter not in gold at all

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN results__position != 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT results__result_id) 
FROM one_nf_0 
WHERE drivers__first_name = 'Lewis' AND drivers__last_name = 'Hamilton' AND circuits__circuit_id = 1 AND races__year >= 2010;
```

### Q897 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against a separate 'driverStandings' table that doesn't exist -- only one_nf_0 exists, with driverStandings__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    drivers__first_name, 
    drivers__last_name, 
    drivers__nationality, 
    MAX(driverStandings__points) AS max_points
FROM 
    one_nf_0
JOIN 
    driverStandings ON one_nf_0.results__driver_id = driverStandings.driver_id
GROUP BY 
    drivers__driver_id
ORDER BY 
    SUM(driverStandings__wins) DESC
LIMIT 1;
```

### Q898 (simple, retrieval) — **Other** (wrong aggregate function/scaling)

**Outcome:** `wrong_answer` · **Reason:** MIN(date_of_birth) returns the OLDEST Japanese driver, the opposite of gold's intent (youngest, via ORDER BY dob DESC LIMIT 1); the accompanying first_name/last_name aren't correlated to that row since there's no GROUP BY, and the age computation itself is dropped entirely

**Gold SQL (original 3NF form):**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT MIN(drivers__date_of_birth), drivers__first_name, drivers__last_name
FROM one_nf_0
WHERE drivers__nationality = 'Japanese';
```

### Q902 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results__number < 20 (the driver's car number) instead of gold's driverStandings.position < 20 (championship standing) -- unrelated real columns

**Gold SQL (original 3NF form):**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT races__name 
FROM one_nf_0 
WHERE drivers__first_name = 'Alex' 
AND drivers__last_name = 'Yoong' 
AND results__number < 20;
```

### Q904 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by results__fastest_lap_time (a per-race best-lap text summary) instead of gold's lapTimes.milliseconds (raw per-lap timing) -- different columns/granularity, and fastest_lap_time sorts as text not numeric time

**Gold SQL (original 3NF form):**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT races__name, races__year
FROM one_nf_0
WHERE drivers__first_name = 'Michael' AND drivers__last_name = 'Schumacher'
ORDER BY results__fastest_lap_time ASC
LIMIT 1;
```

### Q909 (moderate, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** numerator SUM(CASE WHEN circuits__country='Germany'...) counts one_nf_0 rows -- each 'European Grand Prix' race duplicated once per result/qualifying/lap/pitstop row via the results-anchored fan-out -- instead of COUNT(DISTINCT CASE WHEN country='Germany' THEN races__race_id END); denominator correctly uses COUNT(DISTINCT race_id)

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN circuits__country = 'Germany' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT races__race_id) 
FROM one_nf_0 
WHERE races__name = 'European Grand Prix';
```

### Q915 (simple, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against separate 'drivers' and 'circuits' tables that don't exist -- only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT circuits__country
FROM one_nf_0
JOIN drivers ON one_nf_0.results__driver_id = drivers.drivers__driver_id
JOIN circuits ON one_nf_0.races__circuit_id = circuits.circuits__circuit_id
ORDER BY drivers.drivers__date_of_birth ASC
LIMIT 1;
```

### Q930 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `raceId IN (SELECT raceId FROM results WHERE rank=0 AND driverId=...)` subquery (filtering to races where Hamilton's result had rank=0, a distinct results field from position) entirely, replacing it with an unrelated ORDER BY results__position ASC LIMIT 1

**Gold SQL (original 3NF form):**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT races__name
FROM one_nf_0
WHERE drivers__first_name = 'Lewis' AND drivers__last_name = 'Hamilton'
ORDER BY results__position ASC
LIMIT 1;
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** races__name = 'AustChineseralian Grand Prix' is a garbled/corrupted literal (looks like 'Australian' and 'Chinese' Grand Prix merged) that matches no real race name -- should be 'Chinese Grand Prix'

**Gold SQL (original 3NF form):**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT results__time 
FROM one_nf_0 
WHERE races__year = 2008 
  AND races__name = 'AustChineseralian Grand Prix' 
  AND results__position = 2;
```

### Q940 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results__position IS NOT NULL instead of gold's results__time IS NOT NULL -- different real columns

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT results__driver_id) 
FROM one_nf_0 
WHERE races__year = 2008 AND races__name = 'Chinese Grand Prix' AND results__position IS NOT NULL;
```

### Q944 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'position_order' without the required results__ prefix -- doesn't exist in the wide table under that name; also replaces gold's specific raceId=853/854 time-difference lookup with an unrelated MAX/MIN of position_order

**Gold SQL (original 3NF form):**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    ((MAX(position_order) - MIN(position_order)) * 100.0 / MIN(position_order)) AS percentage_faster
FROM 
    one_nf_0
WHERE 
    races__year = 1988 AND races__name = 'Australian Grand Prix';
```

### Q948 (simple, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs against a fictional 'constructors__nationality' table -- only one_nf_0 exists, with constructors__nationality as a column, not a table

**Gold SQL (original 3NF form):**

```sql
SELECT MAX(T1.points) FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T2.nationality = 'British'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT MAX(points) 
FROM (
    SELECT DISTINCT constructorResults__constructor_id, constructorResults__points 
    FROM one_nf_0 
    JOIN constructors__nationality ON one_nf_0.constructors__constructor_id = constructors__nationality.constructor_id 
    WHERE constructors__nationality.nationality = 'British'
)
```

### Q950 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters/aggregates results__race_id and results__points (a driver's per-race result) instead of gold's constructorStandings (raceId, points) -- the team's cumulative championship-standing points after that race is a different concept

**Gold SQL (original 3NF form):**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT constructors__name 
FROM one_nf_0 
WHERE results__race_id = 291 AND results__points = 0;
```

### Q951 (simple, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** has two consecutive GROUP BY clauses in the same subquery ('near GROUP: syntax error') -- a malformed, unparseable statement

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT constructors__constructor_id)
FROM one_nf_0
WHERE constructors__nationality = 'Japanese'
AND constructors__constructor_id IN (
    SELECT constructors__constructor_id
    FROM one_nf_0
    GROUP BY constructors__constructor_id, races__race_id
    HAVING SUM(constructors__points) = 0
    GROUP BY constructors__constructor_id
    HAVING COUNT(DISTINCT races__race_id) = 2
)
```

### Q954 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** counts results__position IS NOT NULL instead of gold's results__time IS NOT NULL -- different real columns

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(COUNT(DISTINCT CASE WHEN results__position IS NOT NULL THEN results__result_id END) AS REAL) * 100 / COUNT(DISTINCT results__result_id) AS race_completion_percentage
FROM 
    one_nf_0
WHERE 
    drivers__nationality = 'Japanese' 
    AND races__year BETWEEN 2007 AND 2009;
```

### Q955 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** the outer query references a computed alias 'time_seconds' that the subquery never defines (the subquery only selects raw result_id/race_id/driver_id/time/milliseconds) -- gold computes AVG(milliseconds/1000.0) directly

**Gold SQL (original 3NF form):**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(time_seconds) 
FROM (
    SELECT DISTINCT results__result_id, results__race_id, results__driver_id, results__time, results__milliseconds
    FROM one_nf_0
    WHERE races__year < 1975
) AS subquery
GROUP BY races__year;
```

### Q959 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results__position = 1 (only the race winner) instead of gold's results__time LIKE '_:%:__.___' (any driver with a validly formatted classified time) -- an entirely different filtering concept

**Gold SQL (original 3NF form):**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT results__fastest_lap_number
FROM one_nf_0
WHERE races__year = 2009 AND results__position = 1;
```

### Q960 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** the subquery's SELECT list never defines 'fastest_lap_speed' as an accessible name outside itself without the results__ prefix -- doesn't exist under that bare name

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T1.fastestLapSpeed) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T2.name = 'Spanish Grand Prix'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(fastest_lap_speed)
FROM (
    SELECT DISTINCT results__result_id, fastest_lap_speed
    FROM one_nf_0
    WHERE races__year = 2009 AND races__name = 'Spanish Grand Prix'
)
```

### Q962 (challenging, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(CASE WHEN date_of_birth<'1985-01-01' THEN 1 ELSE 0 END) counts one_nf_0 rows -- each driver's row duplicated across their qualifying/lapTimes/pitStops/standings fan-out for every 2000-2005 race -- instead of COUNT(DISTINCT CASE WHEN... THEN driver_id END); it also moves the laps>50 condition out of the CASE into a blanket WHERE filter, changing which drivers populate the denominator too -- not fixable by a DISTINCT keyword alone

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN drivers__date_of_birth < '1985-01-01' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT results__driver_id) 
FROM one_nf_0 
WHERE races__year BETWEEN 2000 AND 2005 AND results__laps >= 50;
```

### Q963 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** compares lapTimes__time as raw text against a wrongly formatted '02:00.00' literal instead of gold's explicit parse-to-seconds computation and 120-second threshold -- text comparison doesn't correctly order minute values with different digit counts, and the literal format doesn't match the real 'M:SS.mmm' data anyway

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT drivers__driver_id)
FROM one_nf_0
WHERE drivers__nationality = 'French'
AND lapTimes__time < '02:00.00';
```

### Q964 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds a DISTINCT that gold doesn't have -- gold's raw query returns one row per American driver (mostly NULL/blank codes, since most drivers have no code recorded, 157 rows), which predicted's DISTINCT collapses down to just 3 unique values, drastically undercounting

**Gold SQL (original 3NF form):**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__driver_code 
FROM one_nf_0 
WHERE drivers__nationality = 'American';
```

### Q967 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** applies the nationality filter before selecting the top-3-youngest drivers, checking 'how many of the 3 youngest Dutch drivers exist' instead of gold's 'how many of the 3 youngest drivers overall are Dutch'; nationality = 'Netherlandic' is also a fabricated value (the real code is 'Dutch')

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT drivers__driver_id)
FROM one_nf_0
WHERE drivers__nationality = 'Netherlandic'
ORDER BY drivers__date_of_birth DESC
LIMIT 3;
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the 'time IS NOT NULL' condition entirely (counts ALL disqualified results in the race range, not just those with a recorded time); also BETWEEN 50 AND 100 is inclusive while gold's raceID<100 AND raceId>50 strictly excludes both endpoints

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT results__result_id) 
FROM one_nf_0 
WHERE results__race_id BETWEEN 50 AND 100 
AND status__status = 'Disqualified';
```

### Q981 (moderate, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against a separate 'drivers' table that doesn't exist -- only one_nf_0 exists, with drivers__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    MIN(races__year) AS first_race_year,
    races__name AS race_name,
    races__date AS race_date,
    races__time AS race_time
FROM 
    one_nf_0
JOIN 
    drivers ON one_nf_0.results__driver_id = drivers.driver_id
WHERE 
    drivers.date_of_birth IS NOT NULL
GROUP BY 
    one_nf_0.results__driver_id
ORDER BY 
    drivers.date_of_birth ASC
LIMIT 1;
```

### Q988 (challenging, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** AVG(pitStops__duration) GROUP BY driver is corrupted because each driver's races carry wildly different numbers of co-joined lapTimes/qualifying/standings rows (unlike a single uniform join), so pit-stop durations from races with more recorded laps are counted many more times than others; empirically verified: predicted's top-3 (Winkelhock, Lotterer, Rosberg) barely overlaps gold's (Rosberg, Sutil, Glock) -- no DISTINCT keyword fixes this, it needs a dedup-by-pitstop subquery first

**Gold SQL (original 3NF form):**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM one_nf_0
WHERE drivers__nationality = 'German'
  AND drivers__date_of_birth BETWEEN '1980-01-01' AND '1985-12-31'
GROUP BY drivers__driver_id
ORDER BY AVG(pitStops__duration) ASC
LIMIT 3;
```

### Q990 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters driverStandings__position = 1 (championship standing after the race) instead of gold's results.time LIKE '_:%:__.___' (a validly formatted classified finish time) -- unrelated real columns/concepts

**Gold SQL (original 3NF form):**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT constructors__constructor_ref_name, constructors__url
FROM one_nf_0
WHERE races__year = 2009 AND races__name = 'Singapore Grand Prix' AND driverStandings__position = 1;
```

### Q994 (challenging, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs against fictional 'constructors__name' and 'races__name' tables -- only one_nf_0 exists, with constructors__name/races__name as columns, not tables

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    c.name AS constructor_name, 
    c.nationality AS constructor_nationality, 
    SUM(r.points) AS total_points
FROM 
    one_nf_0 r
JOIN 
    constructors__name c ON r.results__constructor_id = c.constructor_id
JOIN 
    races__name ra ON r.results__race_id = ra.race_id
WHERE 
    ra.name = 'Monaco Grand Prix' 
    AND ra.year BETWEEN 1980 AND 2010
GROUP BY 
    c.constructor_id
ORDER BY 
    total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares races__name against 'Marina Bay Street Circuit' (a circuit name), when gold filters via circuits.name joined through races.circuitId -- races.name holds Grand Prix event names (e.g. 'Singapore Grand Prix'), so this never matches; also adds an arbitrary ORDER BY round LIMIT 1 OFFSET 2 not in gold, and substitutes qualifying__position=1 for gold's q3-time-based fastest-qualifier ranking

**Gold SQL (original 3NF form):**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM one_nf_0
WHERE qualifying__race_id = (
    SELECT DISTINCT races__race_id
    FROM one_nf_0
    WHERE races__name = 'Marina Bay Street Circuit' AND races__year = 2008
    ORDER BY races__round ASC
    LIMIT 1 OFFSET 2
)
AND qualifying__position = 1;
```

### Q1003 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'status_id' and 'driver_id' without their required prefixes -- don't exist in the wide table under those names; also uses status_id=19 ('+9 Laps') instead of gold's statusId=3 ('Accident')

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT status_id) 
FROM one_nf_0 
WHERE driver_id = (
    SELECT driver_id 
    FROM one_nf_0 
    WHERE races__name = 'Canadian Grand Prix' AND status_id = 19 
    GROUP BY driver_id 
    ORDER BY COUNT(DISTINCT status_id) DESC 
    LIMIT 1
)
```

### Q1011 (challenging, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's derived table computing each driver's MIN(milliseconds) (fastest single lap) entirely, replacing it with a raw, non-aggregated ORDER BY lapTimes__time ASC across all lap-time text values, unprotected from the results-anchored fan-out and text-sorted rather than numeric

**Gold SQL (original 3NF form):**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM one_nf_0
ORDER BY lapTimes__time ASC
LIMIT 20;
```

### Q1014 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** computes MIN(lapTimes__milliseconds) (every individual lap ever timed at Italian circuits) instead of gold's results.FastestLapTime (each driver's single recorded fastest lap per race) -- a different table/grain entirely; also returns milliseconds instead of gold's original time-string format

**Gold SQL (original 3NF form):**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT MIN(lapTimes__milliseconds) AS min_lap_time
FROM one_nf_0
WHERE circuits__country = 'Italy';
```

---

## student_club (30 failures)

### Q1317 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against separate 'attendance' and 'event' tables that don't exist -- only one_nf_0 exists, with attendance__/event__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT one_nf_0.member__member_id)
FROM one_nf_0
JOIN attendance ON one_nf_0.member__member_id = attendance.member_id
JOIN event ON attendance.event_id = event.event_id
WHERE one_nf_0.member__position = 'Student_Club'
AND event.event_name = 'Women''s Soccer'
AND one_nf_0.member__t_shirt_size = 'Medium';
```

### Q1322 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** references a separate 'attendance' table that doesn't exist -- only one_nf_0 exists, with attendance__event_id/attendance__member_id as columns, not a table

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT event_id)
FROM (
    SELECT event_id
    FROM attendance
    WHERE member_id IN (
        SELECT member_id
        FROM one_nf_0
        WHERE member__position = 'Student_Club'
    )
    GROUP BY event_id
    HAVING COUNT(DISTINCT member_id) > 10
)
WHERE event_id IN (
    SELECT event_id
    FROM one_nf_0
    WHERE event__type = 'Meeting'
);
```

### Q1334 (simple, retrieval) — **Other** (missing NULL filter)

**Outcome:** `wrong_answer` · **Reason:** one_nf_0's FULL OUTER JOIN chain preserves a zip_code row for an Illinois zip with no matching member (all-NULL member fields), which gold's INNER JOIN silently drops; empirically verified predicted returns an extra blank row gold doesn't have

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT member__first_name, member__last_name 
FROM one_nf_0 
WHERE zip_code__state = 'Illinois';
```

### Q1338 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** event__event_date = '2019-10-08' never matches -- stored values include a time component (e.g. '2019-10-08T12:00:00'), needing LIKE '2019-10-08%' as gold uses; also selects an extra expense_id column beyond gold's single 'approved' column

**Gold SQL (original 3NF form):**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT expense__expense_id, expense__is_approved 
FROM one_nf_0 
WHERE event__event_name = 'October Meeting' AND event__event_date = '2019-10-08';
```

### Q1339 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'expense_id' (and 'member_first_name'/'member_last_name') without the required expense__/member__ prefixes -- don't exist in the wide table under those names

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(cost)
FROM (
    SELECT DISTINCT expense_id, cost
    FROM one_nf_0
    WHERE member_first_name = 'Elijah' AND member_last_name = 'Allen'
      AND expense_date BETWEEN '2023-09-01' AND '2023-10-31'
)
```

### Q1340 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'amount_spent' without the required budget__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
  (SELECT SUM(amount_spent) 
   FROM one_nf_0 
   WHERE budget__category = 'Student_Club' AND event__event_date BETWEEN '2019-01-01' AND '2019-12-31') -
  (SELECT SUM(amount_spent) 
   FROM one_nf_0 
   WHERE budget__category = 'Student_Club' AND event__event_date BETWEEN '2020-01-01' AND '2020-12-31') AS difference;
```

### Q1344 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** income__income_source = 'fundraising' should be the real value 'Fundraising' (case) -- same column/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT income__notes 
FROM one_nf_0 
WHERE income__date_received = '2019-09-14' AND income__income_source = 'fundraising';
```

### Q1350 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** filters event__event_name/event__event_date ('Post Cards, Posters', '2019-08-20') instead of gold's expense__expense_description/expense__expense_date -- 'Post Cards, Posters' is an expense description, not an event name; also selects event__status instead of gold's budget__event_status (a separate column)

**Gold SQL (original 3NF form):**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT event__status 
FROM one_nf_0 
WHERE event__event_name = 'Post Cards, Posters' AND event__event_date = '2019-08-20';
```

### Q1359 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'budget_id' without the required budget__ prefix -- doesn't exist in the wide table under that name; also replaces gold's ratio calculation with an unrelated COUNT/subquery comparison

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT budget_id) 
FROM one_nf_0 
WHERE event_name = 'Yearly Kickoff' AND budget_category = 'Advertisement' AND amount_spent > (
    SELECT amount_spent 
    FROM one_nf_0 
    WHERE event_name = 'October Meeting' AND budget_category = 'Advertisement'
);
```

### Q1361 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'cost' without the required expense__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT SUM(cost) 
FROM one_nf_0 
WHERE expense_description LIKE '%pizza%'
```

### Q1371 (simple, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** one_nf_0 is missing 2 of the 17 real attendance records for 'Women's Soccer' entirely -- empirically verified: the base attendance-JOIN-event query gives 17 distinct members while one_nf_0 surfaces only 15 -- a data-loss artifact of the independent multi-way FULL OUTER JOIN chain (income/expense/attendance/major/budget all joined independently off the member anchor), not fixable by any DISTINCT or predicate rewrite

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.link_to_member) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'Women''s Soccer'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT attendance__member_id) 
FROM one_nf_0 
WHERE event__event_name = 'Women''s Soccer';
```

### Q1375 (moderate, retrieval) — **Other** (missing NULL filter)

**Outcome:** `wrong_answer` · **Reason:** one_nf_0's FULL OUTER JOIN chain preserves a major row for this department with no matching member (all-NULL member fields), which gold's INNER JOIN silently drops; empirically verified predicted returns an extra blank row gold doesn't have

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.department = 'School of Applied Sciences, Technology and Education'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM one_nf_0
WHERE major__department = 'School of Applied Sciences, Technology and Education';
```

### Q1376 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'event_name' without the required event__ prefix -- doesn't exist in the wide table under that name; also collapses gold's tie-preserving HAVING=MAX(ratio) subquery into a plain ORDER BY/LIMIT 1

**Gold SQL (original 3NF form):**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT event_name
FROM one_nf_0
WHERE event_status = 'closed'
ORDER BY (amount_spent / amount) DESC
LIMIT 1;
```

### Q1380 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'amount_spent' without the required budget__ prefix -- doesn't exist in the wide table under that name; category = 'food' also has wrong case (real value is 'Food')

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT SUM(amount_spent) 
FROM one_nf_0 
WHERE category = 'food';
```

### Q1381 (moderate, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** references a separate 'attendance' table that doesn't exist -- only one_nf_0 exists, with attendance__event_id/attendance__member_id as columns, not a table

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM one_nf_0
WHERE member__member_id IN (
    SELECT member_id
    FROM attendance
    GROUP BY member_id
    HAVING COUNT(DISTINCT event_id) > 7
)
```

### Q1387 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'budget__event_name', which doesn't exist -- event_name lives on event (event__event_name), not budget; also drops the position='Treasurer' filter and the expense/budget join chain entirely

**Gold SQL (original 3NF form):**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM one_nf_0
WHERE budget__event_name = 'Yearly Kickoff';
```

### Q1389 (simple, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'event_name' without the required event__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT event_name
FROM one_nf_0
WHERE event_id = (
    SELECT event_id
    FROM one_nf_0
    GROUP BY event_id
    ORDER BY SUM(cost) ASC, event_name ASC
    LIMIT 1
)
```

### Q1390 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'cost' without the required expense__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SELECT SUM(cost) 
     FROM one_nf_0 
     WHERE event_name = 'Yearly Kickoff') * 100.0 / 
    (SELECT SUM(cost) 
     FROM one_nf_0) AS percentage_cost
```

### Q1394 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra member__position = 'Student_Club' condition not in gold at all -- not even a real position value (real values are Member/Inactive/President/Vice President/Treasurer/Secretary), which blocks every row from matching

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT member__member_id) 
FROM one_nf_0 
WHERE member__position = 'Student_Club' AND major__major_name = 'Physics Teaching';
```

### Q1398 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'event_name' without the required event__ prefix -- doesn't exist in the wide table under that name; budget_category = 'advertisement' also has wrong case (real value is 'Advertisement')

**Gold SQL (original 3NF form):**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT event_name 
FROM one_nf_0 
WHERE budget_category = 'advertisement' 
ORDER BY amount_spent DESC 
LIMIT 1;
```

### Q1399 (moderate, retrieval) — **Other** (unclear/residual)

**Outcome:** `wrong_answer` · **Reason:** structurally matches gold (same filter columns/values, EXISTS is equivalent to COUNT(*)>0); empirically re-executing both the gold and adapted predicted query returns 'YES' for both -- no clear causal bug identifiable from the SQL text or execution alone

**Gold SQL (original 3NF form):**

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean' AND T3.event_name = 'Women''s Soccer'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT CASE 
    WHEN EXISTS (
        SELECT 1 
        FROM one_nf_0 
        WHERE member__first_name = 'Maya' 
        AND member__last_name = 'Mclean' 
        AND event__event_name = 'Women''s Soccer'
    ) THEN 'YES' 
    ELSE 'NO' 
END AS attended;
```

### Q1403 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'cost' in the correlated ORDER BY subquery without the required expense__ prefix -- doesn't exist in the wide table under that name; event__status = 'closed' also has wrong case (real value is 'Closed')

**Gold SQL (original 3NF form):**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT event__event_name
FROM one_nf_0
WHERE event__status = 'closed'
ORDER BY (SELECT SUM(cost) FROM one_nf_0 AS sub WHERE sub.event_id = one_nf_0.event_id) - budget__amount DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** aggregates budget__amount_spent (a pre-aggregated summary field already on the budget row) instead of gold's SUM(expense__cost) (individual expense amounts) -- a different measure entirely, and either way would still need a dedup subquery given the income/expense/attendance fan-out; also compares expense__is_approved to the integer 1 instead of the real text value 'true'

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT budget__category, SUM(budget__amount_spent) AS total_approved_value
FROM one_nf_0
WHERE event__event_name = 'October Meeting' AND expense__is_approved = 1
GROUP BY budget__category;
```

### Q1409 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'expense_id' in the subquery without the required expense__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT SUM(cost) 
FROM (
    SELECT DISTINCT expense_id, cost 
    FROM one_nf_0 
    WHERE expense_date = '2019-08-20'
)
```

### Q1410 (simple, aggregate) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** SUM(expense__cost) is inflated roughly 28x (866.25 vs 24255.0, empirically verified) by the income x expense x attendance independent fan-out baked into one_nf_0 for this member -- needs a dedup-by-expense_id subquery, not a simple DISTINCT patch; also collapses first_name/last_name into a single concatenated column instead of gold's two separate columns

**Gold SQL (original 3NF form):**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    member__first_name || ' ' || member__last_name AS full_name, 
    SUM(expense__cost) AS total_cost
FROM 
    one_nf_0
WHERE 
    member__member_id = 'rec4BLdZHS2Blfp4v'
GROUP BY 
    member__first_name, member__last_name;
```

### Q1411 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds a DISTINCT that gold doesn't have -- Sacha Harrison has 12 raw expense records where several description values repeat (e.g. 'Posters' x3, empirically verified), which predicted's DISTINCT collapses down to 7 unique descriptions

**Gold SQL (original 3NF form):**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT expense__expense_description 
FROM one_nf_0 
WHERE member__first_name = 'Sacha' AND member__last_name = 'Harrison';
```

### Q1422 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects budget__category instead of gold's event.type -- a completely different real column; also adds a DISTINCT gold doesn't have

**Gold SQL (original 3NF form):**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT budget__category 
FROM one_nf_0 
WHERE event__location = 'MU 215';
```

### Q1432 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops the member.position = 'Member' filter entirely, replacing it with an unrelated, fabricated income__income_source = 'Student_Club' condition (not even a real income source value) -- blocks every row from matching; COUNT(*) is also unprotected by DISTINCT against the income/expense/attendance fan-out

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN income__amount = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    one_nf_0 
WHERE 
    member__t_shirt_size = 'Medium' 
    AND income__income_source = 'Student_Club';
```

### Q1435 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'event_name' without the required event__ prefix -- doesn't exist in the wide table under that name; event_type='game'/status='closed' also have wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT event_name 
FROM one_nf_0 
WHERE event_type = 'game' 
AND status = 'closed' 
AND event_date BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1460 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** splits the single compound expense_description value into three separate lowercase substrings ('water','veggie tray','supplies') compared via IN, instead of gold's exact match against the full string 'Water, Veggie tray, supplies' -- none of these match; also concatenates first_name/last_name into a single column instead of gold's two

**Gold SQL (original 3NF form):**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    member__first_name || ' ' || member__last_name AS full_name, 
    expense__cost
FROM 
    one_nf_0
WHERE 
    expense__expense_description IN ('water', 'veggie tray', 'supplies');
```

---

## superhero (34 failures)

### Q717 (simple, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** aliases 'hero_power__hero_id' and 'superpower__id' as if they were standalone tables -- only one_nf_0 exists, with hero_power__/superpower__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT sp.power_name 
FROM one_nf_0 hp 
JOIN hero_power__hero_id hpw ON hp.superhero__id = hpw.hero_id 
JOIN superpower__id sp ON hpw.power_id = sp.id 
WHERE hp.superhero__superhero_name = '3-D Man';
```

### Q719 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'hero_power__power_name', which doesn't exist -- power_name lives on superpower (superpower__power_name), not hero_power

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.height_cm > 200
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT superhero__id) 
FROM one_nf_0 
WHERE hero_power__power_name = 'Super Strength' AND superhero__height_cm > 200;
```

### Q723 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'blue' should be the real value 'Blue' (case) -- same column/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT superhero__id)
FROM one_nf_0
WHERE colour_eye__colour = 'blue'
AND superpower__power_name = 'Agility';
```

### Q724 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'blue' and colour_hair__colour = 'blond' should be 'Blue'/'Blond' (case) -- same columns/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE colour_eye__colour = 'blue' AND colour_hair__colour = 'blond';
```

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's height_cm IS NOT NULL AND height_cm != 0 filter entirely, so heroes with unknown (null/zero) height are included; also selects an extra height_cm column beyond gold's single superhero_name

**Gold SQL (original 3NF form):**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name, superhero__height_cm
FROM one_nf_0
WHERE publisher__publisher_name = 'Marvel Comics'
ORDER BY superhero__height_cm DESC;
```

### Q728 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's RANK() OVER (ORDER BY COUNT(...) DESC) window function entirely -- gold returns 3 columns (colour, count, rank) while predicted returns only 2 (colour, count), so ties in count wouldn't share the same rank

**Gold SQL (original 3NF form):**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT colour_eye__colour, COUNT(DISTINCT superhero__id) AS count
FROM one_nf_0
WHERE publisher__publisher_name = 'Marvel Comics'
GROUP BY colour_eye__colour
ORDER BY count DESC;
```

### Q730 (challenging, retrieval) — **Fan-out** (Irrecoverable)

**Outcome:** `wrong_answer` · **Reason:** empirically verified: predicted's scalar-subquery equality approach (publisher_id = (SELECT...), hero_power__power_id = (SELECT...)) returns 200 of gold's 201 heroes, missing 'Atlas' -- a data-loss/NULL-interaction artifact of one_nf_0's independent hero_attribute x hero_power fan-out chain, not fixable by a simple SQL rewrite of this approach

**Gold SQL (original 3NF form):**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_power AS T2 INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.id = T2.hero_id)AND EXISTS (SELECT 1 FROM publisher AS T4 WHERE T4.publisher_name = 'Marvel Comics' AND T1.publisher_id = T4.id)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE superhero__publisher_id = (
    SELECT publisher__id 
    FROM one_nf_0 
    WHERE publisher__publisher_name = 'Marvel Comics'
) 
AND hero_power__power_id = (
    SELECT superpower__id 
    FROM one_nf_0 
    WHERE superpower__power_name = 'Super Strength'
);
```

### Q733 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'gold' should be the real value 'Gold' (case) -- same column/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT superhero__id) 
FROM one_nf_0 
WHERE colour_eye__colour = 'gold' 
AND publisher__publisher_name = 'Marvel Comics';
```

### Q736 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'hero_attribute__attribute_name', which doesn't exist -- attribute_name lives on attribute (attribute__attribute_name), not hero_attribute

**Gold SQL (original 3NF form):**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE hero_attribute__attribute_name = 'intelligence' 
ORDER BY hero_attribute__attribute_value ASC 
LIMIT 1;
```

### Q738 (simple, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'hero_attribute__attribute_name', which doesn't exist -- attribute_name lives on attribute (attribute__attribute_name), not hero_attribute

**Gold SQL (original 3NF form):**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_attribute AS T2 INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Durability' AND T2.attribute_value < 50 AND T1.id = T2.hero_id)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE hero_attribute__attribute_name = 'Durability' 
AND hero_attribute__attribute_value < 50;
```

### Q740 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'hero_attribute__attribute_name', which doesn't exist -- attribute_name lives on attribute (attribute__attribute_name), not hero_attribute

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.attribute_name = 'Strength' AND T2.attribute_value = 100 AND T4.gender = 'Female'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT superhero__id)
FROM one_nf_0
WHERE gender__gender = 'Female'
AND hero_attribute__attribute_name = 'Strength'
AND hero_attribute__attribute_value = 100;
```

### Q743 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment__alignment = 'Selfish' is not a real alignment value (real values are Good/Bad/Neutral/N/A) -- should be 'Bad', and this fabricated value zeroes both output columns

**Gold SQL (original 3NF form):**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(COUNT(DISTINCT CASE WHEN alignment__alignment = 'Selfish' THEN superhero__id END) AS REAL) * 100 / COUNT(DISTINCT superhero__id) AS percentage_selfish,
    COUNT(DISTINCT CASE WHEN alignment__alignment = 'Selfish' AND publisher__publisher_name = 'Marvel Comics' THEN superhero__id END) AS selfish_marvel_count
FROM 
    one_nf_0;
```

### Q744 (challenging, aggregate) — **Other** (wrong aggregate function/scaling)

**Outcome:** `wrong_answer` · **Reason:** computes DC_count - Marvel_count instead of gold's Marvel_count - DC_count (sign flipped); also drops the CASE-computed 'publisher_with_more_superheroes' label column entirely, returning only the (differently-signed) difference

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SELECT COUNT(DISTINCT superhero__id) 
     FROM one_nf_0 
     WHERE publisher__publisher_name = 'DC Comics') -
    (SELECT COUNT(DISTINCT superhero__id) 
     FROM one_nf_0 
     WHERE publisher__publisher_name = 'Marvel Comics') AS difference;
```

### Q750 (simple, aggregate) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against a separate 'gender' table that doesn't exist -- only one_nf_0 exists, with gender__ prefixed columns; also drops the weight_kg > 0 filter

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(one_nf_0.superhero__weight_kg)
FROM (
    SELECT DISTINCT one_nf_0.superhero__id, one_nf_0.superhero__weight_kg
    FROM one_nf_0
    JOIN gender ON one_nf_0.gender__id = gender.id
    WHERE gender.gender = 'Female'
) AS distinct_females;
```

### Q751 (moderate, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against separate 'hero_power', 'superpower', and 'gender' tables that don't exist -- only one_nf_0 exists

**Gold SQL (original 3NF form):**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT sp.power_name
FROM one_nf_0 h
JOIN hero_power hp ON h.superhero__id = hp.hero_id
JOIN superpower sp ON hp.power_id = sp.id
JOIN gender g ON h.gender__id = g.id
WHERE g.gender = 'Male';
```

### Q753 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** assumes 'No Colour' means a NULL eye_colour_id, but 'No Colour' is an actual value in the colour table (colour_eye__colour = 'No Colour') -- a different, real population than heroes with no eye colour recorded at all

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE superhero__height_cm BETWEEN 170 AND 190 
AND superhero__eye_colour_id IS NULL;
```

### Q760 (challenging, aggregate) — **Fan-out** (Recoverable)

**Outcome:** `wrong_answer` · **Reason:** numerator SUM(CASE WHEN publisher='Marvel Comics' THEN 1 ELSE 0) counts one_nf_0 rows -- each hero duplicated by their own hero_attribute x hero_power fan-out -- instead of COUNT(DISTINCT CASE WHEN publisher='Marvel Comics' THEN superhero__id END); empirically verified: predicted computes 2288% instead of gold's 60.87%

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.height_cm BETWEEN 150 AND 180
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN publisher__publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT superhero__id) 
FROM one_nf_0 
WHERE superhero__height_cm BETWEEN 150 AND 180;
```

### Q761 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restricts the average-weight subquery to Male heroes only (WHERE gender_id = Male), instead of gold's average across ALL heroes with weight_kg > 0 regardless of gender; also drops the weight_kg > 0 exclusion, and the average is further skewed by the hero_attribute x hero_power fan-out since each hero's weight is duplicated by their own attribute/power count

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id WHERE T2.gender = 'Male' AND T1.weight_kg * 100 > ( SELECT AVG(weight_kg) FROM superhero WHERE weight_kg > 0) * 79
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name
FROM one_nf_0
WHERE superhero__gender_id = (
    SELECT gender__id
    FROM one_nf_0
    WHERE gender__gender = 'Male'
)
AND superhero__weight_kg > (
    SELECT AVG(superhero__weight_kg)
    FROM one_nf_0
    WHERE superhero__gender_id = (
        SELECT gender__id
        FROM one_nf_0
        WHERE gender__gender = 'Male'
    )
) * 0.79;
```

### Q766 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'hero_attribute__attribute_name', which doesn't exist -- attribute_name lives on attribute (attribute__attribute_name), not hero_attribute

**Gold SQL (original 3NF form):**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__full_name
FROM one_nf_0
WHERE hero_attribute__attribute_name = 'Strength'
AND hero_attribute__attribute_value = (
    SELECT MAX(hero_attribute__attribute_value)
    FROM one_nf_0
    WHERE hero_attribute__attribute_name = 'Strength'
)
```

### Q769 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by COUNT(hero_power__power_id) instead of gold's hero_attribute__attribute_value for the 'Durability' ATTRIBUTE -- Durability is an attribute (a 0-100 score), not a super-power name; filtering superpower__power_name='Durability' targets an unrelated real column/table

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT superhero__superhero_name
FROM (
    SELECT DISTINCT superhero__id, superhero__superhero_name, hero_power__power_id
    FROM one_nf_0
    WHERE publisher__publisher_name = 'Dark Horse Comics' AND superpower__power_name = 'Durability'
)
GROUP BY superhero__id
ORDER BY COUNT(hero_power__power_id) DESC
LIMIT 1;
```

### Q772 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects the joined colour__colour name strings (colour_eye__colour, colour_hair__colour, colour_skin__colour) instead of gold's raw eye_colour_id/hair_colour_id/skin_colour_id integer FK values -- different columns/representations entirely

**Gold SQL (original 3NF form):**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    colour_eye__colour AS eye_colour, 
    colour_hair__colour AS hair_colour, 
    colour_skin__colour AS skin_colour
FROM 
    one_nf_0
WHERE 
    gender__gender = 'Female' 
    AND publisher__publisher_name = 'Dark Horse Comics';
```

### Q773 (challenging, retrieval) — **Other** (missing NULL filter)

**Outcome:** `wrong_answer` · **Reason:** one_nf_0's FULL OUTER JOIN preserves He-Man and She-Ra despite their publisher_id not matching any real publisher (NULL publisher_name), which gold's INNER JOIN drops; empirically verified predicted returns 159 rows vs gold's 157, with exactly these 2 extra blank-publisher rows

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name, T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.eye_colour_id = T1.hair_colour_id AND T1.eye_colour_id = T1.skin_colour_id
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    superhero__superhero_name, 
    publisher__publisher_name
FROM 
    one_nf_0
WHERE 
    superhero__eye_colour_id = superhero__hair_colour_id 
    AND superhero__hair_colour_id = superhero__skin_colour_id;
```

### Q775 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_skin__colour = 'blue' should be 'Blue' (case) -- zeroes the numerator regardless of the fact that COUNT(*) denominator is also uncontrolled for the hero_attribute x hero_power fan-out

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN colour_skin__colour = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    one_nf_0 
WHERE 
    gender__gender = 'Female';
```

### Q782 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'black' and colour_hair__colour = 'black' should be 'Black' (case) -- same columns/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE colour_eye__colour = 'black' AND colour_hair__colour = 'black';
```

### Q788 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restricts the entire query to Marvel Comics heroes via WHERE, computing 'what % of Marvel heroes are female' instead of gold's 'what % of all female heroes (any publisher) are also Marvel' -- the population scope and the counted condition are swapped relative to gold

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN one_nf_0.gender__gender = 'Female' THEN one_nf_0.superhero__id END) AS REAL) * 100 / COUNT(DISTINCT one_nf_0.superhero__id) 
FROM one_nf_0 
WHERE one_nf_0.publisher__publisher_name = 'Marvel Comics';
```

### Q791 (simple, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'height_cm' without the required superhero__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(height_cm) 
FROM (
    SELECT DISTINCT superhero__id, height_cm 
    FROM one_nf_0
)
```

### Q792 (simple, retrieval) — **Invalid SQL** (wrong table)

**Outcome:** `error` · **Reason:** JOINs one_nf_0 against separate 'hero_power' and 'superpower' tables that don't exist -- only one_nf_0 exists, with hero_power__/superpower__ prefixed columns

**Gold SQL (original 3NF form):**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = 'Abomination'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT sp.power_name 
FROM one_nf_0 h 
JOIN hero_power hp ON h.superhero__id = hp.hero_id 
JOIN superpower sp ON hp.power_id = sp.id 
WHERE h.superhero__superhero_name = 'Abomination';
```

### Q794 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'hero_attribute__attribute_name', which doesn't exist -- attribute_name lives on attribute (attribute__attribute_name), not hero_attribute

**Gold SQL (original 3NF form):**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE hero_attribute__attribute_name = 'Speed' 
ORDER BY hero_attribute__attribute_value DESC 
LIMIT 1;
```

### Q797 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'blue' and colour_hair__colour = 'brown' should be 'Blue'/'Brown' (case) -- same columns/structure, just wrong case

**Gold SQL (original 3NF form):**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE colour_eye__colour = 'blue' AND colour_hair__colour = 'brown';
```

### Q798 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds a DISTINCT that gold doesn't have -- all 3 named heroes are published by DC Comics, so gold's raw (non-distinct) result has 3 duplicate 'DC Comics' rows (empirically verified), which predicted's DISTINCT collapses to 1

**Gold SQL (original 3NF form):**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT publisher__publisher_name 
FROM one_nf_0 
WHERE superhero__superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy');
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'blue' should be the real value 'Blue' (case) -- the numerator/denominator are otherwise correctly DISTINCT-protected

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN colour_eye__colour = 'blue' THEN superhero__id END) AS REAL) * 100 / COUNT(DISTINCT superhero__id) 
FROM one_nf_0;
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** colour_eye__colour = 'blue' should be 'Blue' (case), and the second term should check colour_eye__colour = 'No Colour' (a real colour value, id=1) instead of IS NULL (assumes a missing FK instead of the actual 'No Colour' value); also drops the 'weight_kg = 0 OR' half of gold's filter, checking only IS NULL

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    COUNT(DISTINCT CASE WHEN colour_eye__colour = 'blue' THEN superhero__id END) - 
    COUNT(DISTINCT CASE WHEN colour_eye__colour IS NULL THEN superhero__id END) AS difference
FROM 
    one_nf_0
WHERE 
    superhero__weight_kg IS NULL;
```

### Q822 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour_skin__colour = 'green' should be 'Green' (case) and alignment__alignment = 'villain' should be 'Bad' -- same columns/structure, just wrong values/case

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT superhero__id) 
FROM one_nf_0 
WHERE colour_skin__colour = 'green' AND alignment__alignment = 'villain';
```

### Q829 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** publisher_name = 'DC' should be 'DC Comics' (the real full name) -- doesn't match anything, zeroing that count entirely; also drops the CASE-computed 'publisher_with_more_superheroes' label column, returning only the (now wrong) difference

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (SELECT COUNT(DISTINCT superhero__id) 
     FROM one_nf_0 
     WHERE publisher__publisher_name = 'DC') -
    (SELECT COUNT(DISTINCT superhero__id) 
     FROM one_nf_0 
     WHERE publisher__publisher_name = 'Marvel Comics') AS difference;
```

---

## thrombosis_prediction (47 failures)

### Q1149 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** sex='Male'/admission_type='In-patient'/'Out-patient' should be the real codes 'M'/'+'/'-' -- zeroes both counts entirely; also replaces gold's in_count/out_count ratio*100 formula with an unrelated ABS-difference-over-sum percentage

**Gold SQL (original 3NF form):**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CASE 
        WHEN inpatient_count > outpatient_count THEN 'In-patient'
        ELSE 'Out-patient'
    END AS majority_group,
    ABS(inpatient_count - outpatient_count) * 100.0 / (inpatient_count + outpatient_count) AS deviation_percentage
FROM (
    SELECT 
        COUNT(DISTINCT CASE WHEN Patient__admission_type = 'In-patient' THEN Patient__ID END) AS inpatient_count,
        COUNT(DISTINCT CASE WHEN Patient__admission_type = 'Out-patient' THEN Patient__ID END) AS outpatient_count
    FROM one_nf_0
    WHERE Patient__sex = 'Male'
) AS counts;
```

### Q1150 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Female' should be 'F'; also moves the sex condition into the CASE numerator instead of gold's WHERE-level population restriction, so the denominator becomes ALL patients instead of just female patients

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' AND strftime('%Y', Patient__birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM one_nf_0;
```

### Q1152 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type = 'Inpatient'/'Outpatient' should be the real codes '+'/'-' -- same columns/structure, just wrong values

**Gold SQL (original 3NF form):**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN Patient__admission_type = 'Inpatient' THEN 1 ELSE 0 END) AS REAL) /
    SUM(CASE WHEN Patient__admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio
FROM 
    one_nf_0
WHERE 
    Patient__diagnosis = 'SLE';
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Laboratory__lactate_dehydrogenase > 245 substitutes a generic clinical reference threshold for gold's specific cutoff of 500

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__birthday
FROM one_nf_0
WHERE Laboratory__lactate_dehydrogenase > 245;
```

### Q1156 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters Examination__thrombosis_degree = 'positive' instead of gold's Russell viper venom time (RVVT) = '+' -- a completely different real column, and 'positive' isn't even a valid value for thrombosis_degree (a numeric 0-3 scale)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID, strftime('%Y', 'now') - strftime('%Y', Patient__birthday) AS age
FROM one_nf_0
WHERE Examination__thrombosis_degree = 'positive';
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree = 'severe' should be the numeric code 2 -- thrombosis_degree is a 0-3 numeric scale, not a text severity label

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__diagnosis
FROM one_nf_0
WHERE Examination__thrombosis_degree = 'severe';
```

### Q1162 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters Patient__first_hospital_visit_date (aliased from 'First Date') instead of gold's Patient__first_record_date (aliased from 'Description') -- two different real date columns; sex='Female'/admission_type='Outpatient' should also be 'F'/'-'

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Patient__sex = 'Female'
  AND strftime('%Y', Patient__first_hospital_visit_date) = '1997'
  AND Patient__admission_type = 'Outpatient';
```

### Q1164 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree = 'most serious' should be the numeric code 1; sex = 'female' should be 'F' -- both wrong representations of real values

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID)
FROM `Patient` AS T1
JOIN `Examination` AS T2 ON T1.ID = T2.ID
WHERE T1.`SEX` = 'F'
  AND STRFTIME('%Y', T2.`Examination Date`) = '1997'
  AND T2.`Thrombosis` = 1;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__examination_date LIKE '1997%'
  AND Examination__thrombosis_degree = 'most serious'
  AND Patient__sex = 'female';
```

### Q1166 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's UNION fallback branch entirely (which supplies a NULL-symptoms row if the oldest patient has no Examination record at all); also uses MIN(birthday) instead of gold's MAX(birthday), selecting the OLDEST patient instead of the youngest (MAX birthday = most recent birthdate = youngest)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Examination__symptoms, Patient__diagnosis
FROM one_nf_0
WHERE Patient__birthday = (
    SELECT MIN(Patient__birthday)
    FROM one_nf_0
)
```

### Q1168 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects Patient__first_hospital_visit_date instead of gold's Laboratory.Date (the lab reading date) -- a different table/column entirely; the age calculation also uses today's date instead of gold's age-at-first-visit ('First Date' minus Birthday)

**Gold SQL (original 3NF form):**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    Patient__first_hospital_visit_date, 
    strftime('%Y', 'now') - strftime('%Y', Patient__birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', Patient__birthday)) AS age_at_first_hospital_visit
FROM 
    one_nf_0
WHERE 
    Patient__diagnosis = 'SJS'
ORDER BY 
    Patient__birthday ASC
LIMIT 1;
```

### Q1169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's two separate sex-specific UA thresholds (male<=8.0, female<=6.5) into a single WHERE uric_acid>7.0 filter applied identically to both -- wrong direction and wrong thresholds; sex values 'Male'/'Female' should also be 'M'/'F'

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN Patient__sex = 'Male' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    one_nf_0
WHERE 
    Laboratory__uric_acid > 7.0;
```

### Q1171 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** age < 0 should be age < 18 -- an arithmetic threshold typo that excludes virtually all patients instead of selecting minors

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__examination_date BETWEEN '1990-01-01' AND '1993-12-31'
AND strftime('%Y', Examination__examination_date) - strftime('%Y', Patient__birthday) < 0;
```

### Q1175 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'Hemoglobin' without the required Laboratory__ prefix -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    Patient__birthday, 
    Examination__diagnosis
FROM 
    one_nf_0
WHERE 
    (Patient__ID, Hemoglobin) IN (
        SELECT 
            Patient__ID, 
            MAX(Hemoglobin)
        FROM 
            one_nf_0
    )
```

### Q1179 (moderate, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** selects both anticardiolipin_igg and anticardiolipin_igm when gold wants only the single 'aCL IgM' column

**Gold SQL (original 3NF form):**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Examination__anticardiolipin_igg, Examination__anticardiolipin_igm
FROM one_nf_0
WHERE Patient__diagnosis = 'SLE' AND Patient__first_record_date = '1994-02-19'
AND Examination__examination_date = '1993-11-12';
```

### Q1185 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's Nov-1981-vs-Dec-1981 total-cholesterol percentage-decrease formula (conditional SUM by month) with an unrelated (MAX-MIN)/(days-elapsed) rate-per-day computation

**Gold SQL (original 3NF form):**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (MAX(Laboratory__total_cholesterol) - MIN(Laboratory__total_cholesterol)) / 
    (julianday(MAX(Laboratory__Date)) - julianday(MIN(Laboratory__Date))) AS decrease_rate
FROM 
    one_nf_0
WHERE 
    Patient__birthday = '1959-02-18' 
    AND Laboratory__Date BETWEEN '1981-11-01' AND '1981-12-31';
```

### Q1187 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters Laboratory__aspartate_aminotransferase (GOT) instead of gold's alanine_aminotransferase (GPT) -- different real columns; also filters Examination__examination_date instead of gold's Laboratory.Date for the date range

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID
FROM one_nf_0
WHERE Laboratory__aspartate_aminotransferase > 30
  AND Laboratory__albumin < 4
  AND Examination__examination_date BETWEEN '1987-07-06' AND '1996-01-31';
```

### Q1189 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** the AVG(anticardiolipin_igm) subquery drops the Thrombosis=2 AND ANA Pattern='S' scoping filters entirely, computing 1.2x the overall average across ALL rows instead of gold's average within the same filtered subgroup

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__thrombosis_degree = 2
  AND Examination__antinuclear_antibody_pattern = 'S'
  AND Examination__anticardiolipin_igm > (
    SELECT AVG(Examination__anticardiolipin_igm) * 1.2
    FROM one_nf_0
  )
```

### Q1192 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type = 'Outpatient Clinic' should be '-'; also substitutes a generic clinical 'normal range' (0.3-1.2) for gold's actual threshold (T-BIL < 2.0, no lower bound)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID
FROM one_nf_0
WHERE Patient__admission_type = 'Outpatient Clinic'
  AND Laboratory__Date BETWEEN '1991-10-01' AND '1991-10-31'
  AND Laboratory__total_bilirubin BETWEEN 0.3 AND 1.2;
```

### Q1195 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references bare 'patient_id' (lowercase, unprefixed) without the required Patient__ID naming -- doesn't exist in the wide table under that name

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(albumin)
FROM (
    SELECT DISTINCT patient_id, albumin
    FROM one_nf_0
    WHERE patient_sex = 'Female'
      AND platelet_count > 400
      AND diagnosis = 'SLE'
)
```

### Q1198 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Female' should be 'F' -- same column/structure, just wrong value

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE Patient__sex = 'Female' AND Patient__diagnosis = 'APS';
```

### Q1201 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Female' should be 'F' -- same column/structure, just wrong value

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE strftime('%Y', Patient__birthday) = '1980' AND Patient__diagnosis = 'RA';
```

### Q1205 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's sex-specific UA threshold check (F: >6.5, M: >8.0) with a generic 'normal range' band check (BETWEEN 2.4 AND 7.0) that ignores the patient's sex entirely

**Gold SQL (original 3NF form):**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    CASE 
        WHEN Laboratory__uric_acid BETWEEN 2.4 AND 7.0 THEN 'true'
        ELSE 'false'
    END AS uric_acid_normal_range
FROM one_nf_0
WHERE Patient__ID = 57266;
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Male' should be 'M'; alanine_aminotransferase > 40 also substitutes a generic clinical reference threshold for gold's specific cutoff of 60 (and drops the inclusive >= boundary)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID
FROM one_nf_0
WHERE Patient__sex = 'Male' AND Laboratory__alanine_aminotransferase > 40;
```

### Q1209 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alanine_aminotransferase > 40 substitutes a generic clinical reference threshold for gold's specific cutoff of 60

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__diagnosis
FROM one_nf_0
WHERE Laboratory__alanine_aminotransferase > 40
ORDER BY Patient__birthday ASC;
```

### Q1220 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** urea_nitrogen = 4.0 substitutes a generic clinical reference value for gold's specific value of 29

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__birthday
FROM one_nf_0
WHERE Laboratory__urea_nitrogen = 4.0;
```

### Q1225 (moderate, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** groups by (sex, ID) instead of gold's GROUP BY SEX alone, and drops the GROUP_CONCAT(DISTINCT ID) aggregation entirely -- returns one row per matching patient instead of one concatenated-ID row per sex; also substitutes a generic bilirubin 'abnormal range' (<0.3 OR >1.2) for gold's actual threshold (>=2.0)

**Gold SQL (original 3NF form):**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__sex, Patient__ID, Laboratory__total_bilirubin
FROM one_nf_0
WHERE Laboratory__total_bilirubin < 0.3 OR Laboratory__total_bilirubin > 1.2
GROUP BY Patient__sex, Patient__ID;
```

### Q1227 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Male' should be 'M' (blocks every row); total_cholesterol > 200 should be >= 250; even if fixed, AVG(age) is computed directly over one_nf_0 with no DISTINCT/dedup subquery (gold explicitly dedupes to one row per patient first), so it would still be corrupted by the Laboratory x Examination fan-out

**Gold SQL (original 3NF form):**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(CAST((strftime('%Y', 'now') - strftime('%Y', Patient__birthday)) AS REAL))
FROM one_nf_0
WHERE Patient__sex = 'Male' AND Laboratory__total_cholesterol > 200;
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** triglyceride > 150 substitutes a generic clinical reference threshold for gold's specific cutoff of 200

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Laboratory__triglyceride > 150 AND 
      strftime('%Y', 'now') - strftime('%Y', Patient__birthday) > 50;
```

### Q1231 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Male' should be 'M'; creatinine_phosphokinase > 100 also substitutes a generic clinical reference threshold for gold's specific cutoff of 250

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Patient__sex = 'Male'
  AND Patient__birthday BETWEEN '1936-01-01' AND '1956-12-31'
  AND Laboratory__creatinine_phosphokinase > 100;
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** substitutes generic 'abnormal glucose' (outside 70-110) and 'normal cholesterol' (125-200) reference ranges for gold's simple thresholds (glucose>=180, cholesterol<250); the missing parentheses around the OR also make the whole condition parse as glucose<70 OR (glucose>110 AND cholesterol-in-range), an unintended logic distortion beyond just wrong values

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    Patient__ID, 
    Patient__sex, 
    strftime('%Y', 'now') - strftime('%Y', Patient__birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', Patient__birthday)) AS age
FROM 
    one_nf_0
WHERE 
    Laboratory__blood_glucose < 70 OR Laboratory__blood_glucose > 110
    AND Laboratory__total_cholesterol >= 125 AND Laboratory__total_cholesterol <= 200;
```

### Q1235 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'Patient__red_blood_cell_count', which doesn't exist -- red_blood_cell_count lives on Laboratory (Laboratory__red_blood_cell_count), not Patient

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT 
    Patient__ID, 
    Patient__diagnosis, 
    strftime('%Y', 'now') - strftime('%Y', Patient__birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', Patient__birthday)) AS age
FROM 
    one_nf_0
WHERE 
    Patient__red_blood_cell_count = (SELECT MIN(Patient__red_blood_cell_count) FROM one_nf_0)
```

### Q1238 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hemoglobin BETWEEN 13.5 AND 17.5 substitutes a generic clinical normal range for gold's actual threshold range (10 to 17)

**Gold SQL (original 3NF form):**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID, Patient__sex
FROM one_nf_0
WHERE Patient__diagnosis = 'SLE' AND Laboratory__hemoglobin BETWEEN 13.5 AND 17.5
ORDER BY Patient__birthday ASC
LIMIT 1;
```

### Q1239 (challenging, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** flattens gold's nested `ID IN (SELECT ID FROM Laboratory WHERE HCT>=52 GROUP BY ID HAVING COUNT(ID)>=2)` subquery (counting how many lab records per patient show HCT>=52) into a single outer GROUP BY/HAVING that instead counts DISTINCT Examination__ID occurrences, an unrelated tally; also substitutes a generic hematocrit 'normal range' (45-55) for gold's actual threshold (>=52)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID, strftime('%Y', 'now') - strftime('%Y', Patient__birthday) AS age
FROM one_nf_0
WHERE Laboratory__hematocrit > 45 AND Laboratory__hematocrit < 55
GROUP BY Patient__ID
HAVING COUNT(DISTINCT Examination__ID) >= 2;
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count < 150 / > 450 substitutes generic clinical reference thresholds for gold's actual values (100 and 400)

**Gold SQL (original 3NF form):**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    COUNT(DISTINCT CASE WHEN Laboratory__platelet_count < 150 THEN Patient__ID END) AS lower_than_normal,
    COUNT(DISTINCT CASE WHEN Laboratory__platelet_count > 450 THEN Patient__ID END) AS higher_than_normal
FROM 
    one_nf_0;
```

### Q1242 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** assumes platelet_count is measured in raw cells/uL (150000-450000) when the dataset stores it in the same small-number units as gold's threshold (100-400) -- a unit-scale mismatch that blocks every row from matching

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT Patient__ID
FROM one_nf_0
WHERE Laboratory__Date BETWEEN '1984-01-01' AND '1984-12-31'
  AND strftime('%Y', 'now') - strftime('%Y', Patient__birthday) < 50
  AND Laboratory__platelet_count BETWEEN 150000 AND 450000;
```

### Q1243 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Female' should be 'F' (zeroes the numerator entirely); prothrombin_time > 13.5 also substitutes a generic clinical reference threshold for gold's actual cutoff (>=14)

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE strftime('%Y', 'now') - strftime('%Y', Patient__birthday) > 55 
AND Laboratory__prothrombin_time > 13.5;
```

### Q1247 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing parentheses around the fibrinogen OR condition make the whole WHERE clause parse as (sex AND WBC AND fibrinogen<150) OR (fibrinogen>400), so the sex and WBC-range conditions don't apply to high-fibrinogen patients at all; sex='Male' should also be 'M', and the WBC range (4000-11000) uses the wrong unit scale (dataset values are in the small ~3.5-9.0 range gold uses)

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Patient__sex = 'Male'
AND Laboratory__white_blood_cell_count BETWEEN 4000 AND 11000
AND Laboratory__fibrinogen < 150 OR Laboratory__fibrinogen > 400;
```

### Q1251 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_g > 130 substitutes a generic clinical reference threshold for gold's specific cutoff of 2000

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE Laboratory__immunoglobulin_g > 130;
```

### Q1252 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_g = 'Normal' -- IGG is a numeric column (e.g. 339, 771, 430...), not a categorical text value; should be BETWEEN 900 AND 2000 as gold specifies

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Laboratory__immunoglobulin_g = 'Normal' AND Examination__symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters Examination__anticardiolipin_iga (a different antibody test, aCL IgA) instead of gold's Laboratory.IGA (immunoglobulin_a) -- two unrelated real columns; 'Normal' is also not a real value (IGA is numeric)

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__anticardiolipin_iga = 'Normal'
AND Patient__first_hospital_visit_date > '1990-01-01';
```

### Q1256 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** checks Laboratory__ID IS NULL instead of gold's Patient__first_record_date (Description) IS NULL -- an unrelated, nonsensical condition on a flat table scan; c_reactive_protein = 'abnormal' is also not a real value (should be '+')

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Laboratory__c_reactive_protein = 'abnormal'
AND Laboratory__ID IS NULL;
```

### Q1257 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** creatinine > 1.2 substitutes a generic clinical reference threshold for gold's actual cutoff (>=1.5)

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Laboratory__creatinine > 1.2 AND Patient__birthday > DATE('now', '-70 years')
```

### Q1265 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'Examination__anti_ribonuclear_protein', which doesn't exist -- anti_ribonuclear_protein (RNP) lives on Laboratory, not Examination

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE Examination__anti_ribonuclear_protein = 'Normal' 
AND Patient__admission_type IS NOT NULL;
```

### Q1267 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'Examination__anti_sm', which doesn't exist -- anti_sm lives on Laboratory, not Examination

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__anti_sm = 'normal' AND Examination__thrombosis_degree IS NULL;
```

### Q1270 (challenging, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'Examination__anti_scl70', which doesn't exist -- anti_scl70 lives on Laboratory, not Examination

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__anti_scl70 = 'normal'
  AND Patient__sex = 'female'
  AND Examination__symptoms IS NULL;
```

### Q1275 (moderate, aggregate) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** references 'Examination__anti_centromere', which doesn't exist -- anti_centromere lives on Laboratory, not Examination

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__anti_centromere = 'normal'
  AND Examination__anti_ssb = 'normal'
  AND Patient__sex = 'male';
```

### Q1281 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an entirely extra 'alanine_aminotransferase > 35' OR-condition that gold doesn't have (gold only checks GOT>=60); aspartate_aminotransferase > 40 also substitutes a generic reference threshold for gold's actual cutoff (>=60); MIN(birthday) also selects the OLDEST qualifying patient instead of gold's YOUNGEST (ORDER BY birthday DESC LIMIT 1)

**Gold SQL (original 3NF form):**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT MIN(Patient__birthday)
FROM one_nf_0
WHERE Laboratory__aspartate_aminotransferase > 40 OR Laboratory__alanine_aminotransferase > 35;
```

---

## toxicology (38 failures)

### Q197 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='single'/element='O' should be '-'/'o'; also wrongly requires the oxygen atom itself to be the one on the single-bond row instead of independently counting all oxygen atoms in molecules that merely contain >=1 single bond

**Gold SQL (original 3NF form):**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(oxygen_count)
FROM (
    SELECT DISTINCT molecule__molecule_id, COUNT(*) AS oxygen_count
    FROM one_nf_0
    WHERE atom_1__element = 'O' AND bond__bond_type = 'single'
    GROUP BY molecule__molecule_id
)
```

### Q198 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='single'/label LIKE '%carcinogenic%' should be '-'/'+'; filtering bond_type in WHERE before GROUP BY also restricts the averaging denominator to only molecules with >=1 single bond, unlike gold's per-molecule conditional SUM over all bonds

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(single_bond_count)
FROM (
    SELECT DISTINCT molecule__molecule_id, COUNT(*) AS single_bond_count
    FROM one_nf_0
    WHERE bond__bond_type = 'single' AND molecule__label LIKE '%carcinogenic%'
    GROUP BY molecule__molecule_id
)
```

### Q200 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='triple' should be '#', label='carcinogenic' should be '+' -- same columns/structure, just wrong invented literals

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT molecule__molecule_id
FROM one_nf_0
WHERE bond__bond_type = 'triple' AND molecule__label = 'carcinogenic';
```

### Q201 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='DOUBLE' should be '=', element='C' should be lowercase 'c'; also SUM(CASE...) instead of COUNT(DISTINCT CASE...) can overcount an atom across its multiple bond rows

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT atom_1__atom_id) 
FROM one_nf_0 
WHERE bond__bond_type = 'DOUBLE';
```

### Q206 (challenging, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** selects both atom_1__element and atom_2__element when gold wants only the element of the atom on the connected.atom_id side (one column)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE bond__bond_id = 'TR004_8_9';
```

### Q207 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='double' should be '='; also adds an extra atom_2__element column beyond gold's single atom.element column

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE bond__bond_type = 'double'
```

### Q208 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** element='H' should be lowercase 'h'; also ORs atom_1/atom_2 element matches together but only COUNT(DISTINCT connected__atom_id) on the atom_1 side, undercounting hydrogen atoms that only matched via atom_2

**Gold SQL (original 3NF form):**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT molecule__label
FROM one_nf_0
WHERE atom_1__element = 'H' OR atom_2__element = 'H'
GROUP BY molecule__label
ORDER BY COUNT(DISTINCT connected__atom_id) DESC
LIMIT 1
```

### Q212 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** gold's HAVING COUNT(*) = (SELECT MIN(cnt) FROM (...)) tie-preserving pattern is collapsed to a plain GROUP BY/ORDER BY ASC LIMIT 1; the WHERE label != 'carcinogenic' is also a no-op that never excludes any real row

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

**Predicted SQL (against one_nf_0):**

```sql
SELECT atom_1__element
FROM one_nf_0
WHERE molecule__label != 'carcinogenic'
GROUP BY atom_1__element
ORDER BY COUNT(DISTINCT atom_1__atom_id) ASC
LIMIT 1;
```

### Q215 (challenging, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's molecule_id IN (SELECT DISTINCT molecule_id FROM bond WHERE bond_type='-') subquery (scoping to any single-bonded molecule, then counting I and S atoms independently) is replaced by a flat WHERE requiring an I atom and an S atom to be on the SAME bond row; bond_type='single' and element values are also wrong

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    COUNT(DISTINCT atom_1__atom_id) AS iodine_count,
    COUNT(DISTINCT atom_2__atom_id) AS sulfur_count
FROM 
    one_nf_0
WHERE 
    bond__bond_type = 'single' AND
    ((atom_1__element = 'I' AND atom_2__element = 'S') OR 
     (atom_1__element = 'S' AND atom_2__element = 'I'));
```

### Q218 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** label='carcinogenic' should be '+'; also replaces gold's 100-minus-percent-of-molecules-with-fluorine formula with a row-counting SUM(CASE WHEN atom_1/2 != 'F') that counts bond rows lacking F on either side rather than molecules lacking F entirely

**Gold SQL (original 3NF form):**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element != 'F' AND atom_2__element != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM one_nf_0 
WHERE molecule__label = 'carcinogenic'
```

### Q219 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps which condition scopes the population (WHERE, should be bond_type='#') vs which is counted (CASE, should be label='+') relative to gold, in addition to using wrong literal values ('triple'/'carcinogenic' instead of '#'/'+')

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN bond__bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM one_nf_0
WHERE molecule__label = 'carcinogenic';
```

### Q220 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR000' -- label only holds '+'/'-' domain values, not molecule IDs; should filter molecule__molecule_id = 'TR000'

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element
FROM one_nf_0
WHERE molecule__label = 'TR000'
ORDER BY atom_1__element ASC
LIMIT 3;
```

### Q226 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR008' should be molecule__molecule_id = 'TR008'; bond_type='DOUBLE' should be '=' as a secondary issue

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN bond__bond_type = 'DOUBLE' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT bond__bond_id) AS percentage_double_bonds
FROM one_nf_0
WHERE molecule__label = 'TR008';
```

### Q227 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label='carcinogenic' should be '+' -- same column/structure, just wrong invented literal

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN molecule__label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) AS percentage_carcinogenic
FROM one_nf_0;
```

### Q228 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR206' should be molecule__molecule_id = 'TR206'; element='H' should be lowercase 'h' as a secondary issue

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    CAST(SUM(CASE WHEN atom_1__element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / 
    COUNT(DISTINCT atom_1__atom_id) AS percentage_hydrogen
FROM 
    one_nf_0
WHERE 
    molecule__label = 'TR206';
```

### Q230 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR060' should be molecule__molecule_id = 'TR060'; also selects 3 columns (atom_1/atom_2 element + label) instead of gold's 2 (element, label)

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element, molecule__label 
FROM one_nf_0 
WHERE molecule__label = 'TR060';
```

### Q231 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR010' should be molecule__molecule_id = 'TR010'

**Gold SQL (original 3NF form):**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT bond__bond_type
FROM one_nf_0
WHERE molecule__label = 'TR010'
GROUP BY bond__bond_type
ORDER BY COUNT(DISTINCT bond__bond_id) DESC
LIMIT 1;
```

### Q232 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT DISTINCT molecule__label returns the +/- label instead of gold's molecule_id; bond_type='single' and the no-op 'NOT LIKE %carcinogenic%' filter (should be label='-') are secondary issues

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT molecule__label
FROM one_nf_0
WHERE bond__bond_type = 'single'
AND molecule__label NOT LIKE '%carcinogenic%'
ORDER BY molecule__label ASC
LIMIT 3;
```

### Q234 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR009' should be molecule__molecule_id = 'TR009'; also filters atom_1__atom_id = 12 (bare integer) instead of the compound string atom_id 'TR009_12' and drops the OR atom_id2 side entirely

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT bond__bond_id) 
FROM one_nf_0 
WHERE atom_1__atom_id = 12 AND molecule__label = 'TR009';
```

### Q236 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects atom_1__element/atom_2__element instead of gold's atom_id/atom_id2 (connected__atom_id, connected__atom_id2) -- the question asks for the two atom IDs, not their elements

**Gold SQL (original 3NF form):**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT bond__bond_type, atom_1__element, atom_2__element
FROM one_nf_0
WHERE bond__bond_id = 'TR001_6_9';
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's SUBSTR(atom_id,-2)='19' suffix transformation, replacing it with atom_1__atom_id = 19 (a bare integer compared to a compound string atom_id, never matches); also counts connected__atom_id2 instead of bond_id

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT COUNT(DISTINCT connected__atom_id2) 
FROM one_nf_0 
WHERE atom_1__atom_id = 19;
```

### Q240 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR004' should be molecule__molecule_id = 'TR004'; also adds an extra atom_2__element column beyond gold's single atom.element column

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE molecule__label = 'TR004';
```

### Q242 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT DISTINCT molecule__label returns the +/- label instead of gold's molecule_id; also drops the SUBSTR(atom_id,-2) suffix transformation (uses a bare integer BETWEEN 21 AND 25) and label LIKE '%carcinogenic%' should be ='+'

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT molecule__label 
FROM one_nf_0 
WHERE atom_1__atom_id BETWEEN 21 AND 25 AND molecule__label LIKE '%carcinogenic%'
```

### Q243 (moderate, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's bond_id IN (SELECT bond_id FROM connected JOIN atom WHERE element='p') subquery is replaced by a flat WHERE requiring the phosphorus and nitrogen atoms to be on the same bond row (atom_1/atom_2); element values are also spelled out ('Phosphorus'/'Nitrogen') instead of the real codes 'p'/'n'

**Gold SQL (original 3NF form):**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT bond__bond_id
FROM one_nf_0
WHERE atom_1__element = 'Phosphorus' AND atom_2__element = 'Nitrogen'
```

### Q244 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** gold's WITH-CTE + WHERE cnt = (SELECT MAX(cnt) FROM sub) tie-preserving pattern is collapsed to a plain GROUP BY/ORDER BY DESC LIMIT 1; bond_type='double' should be '='

**Gold SQL (original 3NF form):**

```sql
with sub as ( SELECT T.molecule_id, COUNT(T.bond_type) as cnt
 FROM bond AS T WHERE T.bond_type = '=' GROUP BY T.molecule_id 
) 
SELECT T1.label FROM molecule AS T1 INNER JOIN sub
 AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.cnt = (select max(cnt) from sub)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT molecule__label
FROM one_nf_0
WHERE bond__bond_type = 'double'
GROUP BY molecule__molecule_id
ORDER BY COUNT(DISTINCT bond__bond_id) DESC
LIMIT 1;
```

### Q245 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='iodine' should be lowercase 'i' -- same column/structure, just wrong invented literal (spelled-out element name)

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT AVG(bond_count)
FROM (
    SELECT DISTINCT atom_1__atom_id, COUNT(connected__bond_id) AS bond_count
    FROM one_nf_0
    WHERE atom_1__element = 'iodine'
    GROUP BY atom_1__atom_id
)
```

### Q247 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** the NOT IN subqueries reference one_nf_0's own atom_1__atom_id/atom_2__atom_id columns against themselves, which is tautologically always true for any row that has that atom_id (self-referential), making the WHERE clause vacuously exclude everything instead of reproducing gold's exclusion of atoms absent from the connected table

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element 
FROM one_nf_0 
WHERE atom_1__atom_id NOT IN (
    SELECT atom_1__atom_id 
    FROM one_nf_0
) 
AND atom_1__atom_id NOT IN (
    SELECT atom_2__atom_id 
    FROM one_nf_0
)
```

### Q248 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR041' should be molecule__molecule_id = 'TR041'; bond_type='triple' should be '#' and an extra atom_2__atom_id column are secondary issues

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__atom_id, atom_2__atom_id
FROM one_nf_0
WHERE molecule__label = 'TR041' AND bond__bond_type = 'triple'
```

### Q249 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule__label = 'TR144_8_19' -- that value is a bond_id (format molecule_atomIdx_atomIdx), not a label; should filter connected__bond_id/bond__bond_id

**Gold SQL (original 3NF form):**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE molecule__label = 'TR144_8_19';
```

### Q253 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='triple' should be '#'; also adds an extra atom_2__element column beyond gold's single atom.element column

**Gold SQL (original 3NF form):**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE bond__bond_type = 'triple'
```

### Q255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** the CASE expression re-checks bond_type='single' (already filtered in WHERE, so always true) instead of checking molecule__label='+' for the numerator, collapsing the ratio to a redundant tautology; bond_type value is also wrong (should be '-')

**Gold SQL (original 3NF form):**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN bond__bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT bond__bond_id) AS proportion_carcinogenic
FROM one_nf_0
WHERE bond__bond_type = 'single';
```

### Q260 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's two molecule_id IN (SELECT...) filters (triple-bond molecules; molecules containing a p or br atom) are replaced by a flat WHERE forcing p/br onto the same bonded atom pair; also uses a nonsensical SUM(DISTINCT atom_id) instead of COUNT(*), and wrong bond_type/element values

**Gold SQL (original 3NF form):**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT SUM(DISTINCT atom_1__atom_id) + SUM(DISTINCT atom_2__atom_id) AS total_atoms
FROM one_nf_0
WHERE bond__bond_type = 'triple' AND (atom_1__element = 'P' OR atom_2__element = 'Br');
```

### Q263 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** the numerator and the denominator subquery use the identical WHERE filter, so the ratio degenerates to a constant 100% instead of reproducing gold's nested molecule_id-IN-subquery scoping; bond_type='single' and element case ('Cl' vs 'cl') are also wrong

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    (COUNT(DISTINCT atom_1__atom_id) + COUNT(DISTINCT atom_2__atom_id)) * 100.0 / 
    (SELECT COUNT(DISTINCT atom_1__atom_id) + COUNT(DISTINCT atom_2__atom_id) 
     FROM one_nf_0 
     WHERE bond__bond_type = 'single' AND (atom_1__element = 'Cl' OR atom_2__element = 'Cl')) AS percentage
FROM one_nf_0
WHERE bond__bond_type = 'single' AND (atom_1__element = 'Cl' OR atom_2__element = 'Cl');
```

### Q268 (challenging, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** selects both atom_1__element and atom_2__element when gold wants only the element of the atom on the connected.atom_id side (one column); bond_id value itself matches correctly

**Gold SQL (original 3NF form):**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE bond__bond_id = 'TR001_10_11';
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label LIKE '%carcinogenic%' should be ='+', element='Cl' should be lowercase 'cl' -- same columns/structure, just wrong literals

**Gold SQL (original 3NF form):**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT CAST(SUM(CASE WHEN atom_1__element = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT atom_1__atom_id) 
FROM one_nf_0 
WHERE molecule__label LIKE '%carcinogenic%'
```

### Q281 (challenging, retrieval) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** drops gold's GROUP BY element / COUNT(*) aggregation entirely, replacing it with an arbitrary DISTINCT + ORDER BY + LIMIT 3 OFFSET 3 row-listing that never aggregates; also selects the wrong columns (molecule_id, atom_2 element) and label='carcinogenic' is wrong

**Gold SQL (original 3NF form):**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT molecule__molecule_id, atom_2__element
FROM one_nf_0
WHERE molecule__label = 'carcinogenic'
ORDER BY molecule__molecule_id, atom_2__atom_id
LIMIT 3 OFFSET 3;
```

### Q282 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** CASE WHEN atom_1__element='H' (wrong case, should be 'h') always evaluates false, zeroing out the ratio; also adds an unwanted *100 scaling factor gold's plain fraction doesn't have and omits DISTINCT on the atom_id count

**Gold SQL (original 3NF form):**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT 
    molecule__label, 
    CAST(SUM(CASE WHEN atom_1__element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(atom_1__atom_id) AS hydrogen_ratio
FROM 
    one_nf_0
WHERE 
    molecule__molecule_id = 'TR006'
GROUP BY 
    molecule__label;
```

### Q327 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT DISTINCT molecule__label returns the +/- label instead of gold's molecule_id; the WHERE filter (NOT LIKE '%carcinogenic%') is also a no-op that never excludes any real row since no label equals that string

**Gold SQL (original 3NF form):**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL (against one_nf_0):**

```sql
SELECT DISTINCT molecule__label 
FROM one_nf_0 
WHERE molecule__label NOT LIKE '%carcinogenic%' 
GROUP BY molecule__molecule_id 
HAVING COUNT(DISTINCT atom_1__atom_id) > 5;
```

---

