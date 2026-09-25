# Qwen2.5-Coder-14B · L3·S2 — hand-classified failures (n=284)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. Predicted SQL uses S2 (abbreviated snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py`'s `"s2"` mapping (not `"s3"`) before being called a naming bug. Gold SQL always uses the original physical column name, same as every other pass. Grouped by database, sorted by question id.

| Category | Meaning |
|---|---|
| Invalid SQL | predicted SQL fails to execute |
| Schema linking | real table/column, but the wrong one for the question |
| JOIN errors | join structure itself is wrong |
| GROUP BY errors | mismatch in the `GROUP BY` clause specifically |
| Nesting problem | missing/extra subquery, CTE, window function, or set operation |
| Predicate error | filter condition wrong (value or transformation), right column/table |
| Other | wrong aggregate function/scaling, DISTINCT/DESC, or residual |

---

## california_schools (29 failures)

### Q5 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Missing rtype='S' filter; Virtual='Yes' (invented value) vs gold's 'F'; also COUNT(*) instead of COUNT(DISTINCT CDSCode).

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
FROM satscores 
JOIN schools ON satscores.cds = schools.cds_cd 
WHERE satscores.avg_scr_math > 400 AND schools.Virtual = 'Yes';
```

### Q11 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Omits the schools join needed for the 'School is not NULL' filter; also drops the '+ enroll_5_17' addend entirely.

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT cds_cd FROM frpm WHERE enroll_k12 > 500;
```

### Q12 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Divides num_ge_1500 by enroll12 (enrollment_grade_12) instead of num_tst_takr (number_test_takers); also selects frpm_5_17 (FRPM Count Ages 5-17) directly instead of computing the free-meal/enrollment ratio, and drops rtype/enrollment filters.

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
SELECT MAX(f.frpm_5_17) 
FROM frpm f 
JOIN satscores s ON f.cds_cd = s.cds 
WHERE s.num_ge_1500 / s.enroll12 > 0.3;
```

### Q17 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Join and columns are correct, but drops the 'CharterNum IS NOT NULL' and rtype='S' filters.

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
    s.charter_num, 
    ss.avg_scr_write, 
    RANK() OVER (ORDER BY ss.avg_scr_write DESC) as rank
FROM 
    satscores ss
JOIN 
    schools s ON ss.cds = s.cds_cd
WHERE 
    ss.avg_scr_write > 499;
```

### Q23 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds ABS() around the enrollment difference that gold doesn't have.

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT s.School, s.Street, s.City, s.State, s.Zip 
FROM frpm f 
JOIN schools s ON f.cds_cd = s.cds_cd 
WHERE ABS(f.enroll_k12 - f.enroll_5_17) > 30;
```

### Q24 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the rtype='S' filter (pct_free_k12 substitution for the raw ratio is scale-equivalent -- verified the two are numerically identical -- so not itself a bug).

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.School
FROM frpm f
JOIN satscores ss ON f.cds_cd = ss.cds
JOIN schools s ON f.cds_cd = s.cds_cd
WHERE f.pct_free_k12 > 0.1 AND ss.num_ge_1500 > 0;
```

### Q25 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** County='Riverside' substituted for District LIKE 'Riverside%' -- a real but different column; also collapses gold's GROUP BY sname,FundingType HAVING AVG(avg_scr_math)>400 into a flat WHERE filter with no GROUP BY/HAVING.

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
SELECT s.School, s.fund_type 
FROM schools s 
JOIN satscores ss ON s.cds_cd = ss.cds 
WHERE s.County = 'Riverside' AND ss.avg_scr_math > 400;
```

### Q26 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** enroll_5_17 (Enrollment Ages 5-17) substituted for frpm_5_17 (FRPM Count Ages 5-17); status_type ('High School') substituted for sch_type ('High Schools (Public)') -- both real but wrong columns.

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
    s.City, 
    s.State, 
    s.Zip
FROM 
    schools s
JOIN 
    frpm f ON s.cds_cd = f.cds_cd
WHERE 
    s.County = 'Monterey' 
    AND f.enroll_5_17 > 800 
    AND s.status_type = 'High School';
```

### Q27 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Predicted has no join to satscores at all (single-table query on schools), so avg_scr_write (real column on satscores) is unreachable; also comm_num used for Phone (not a real column anywhere).

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT s.School, s.avg_scr_write, s.comm_num 
FROM schools s 
WHERE s.open_dt > '1991-12-31' OR s.close_dt < '2000-01-01';
```

### Q28 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Locally Funded' (case) vs gold's 'Locally funded'.

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT s.School, s.doc_type
FROM schools s
JOIN frpm f ON s.cds_cd = f.cds_cd
WHERE f.enroll_k12 - f.enroll_5_17 > (
    SELECT AVG(f.enroll_k12 - f.enroll_5_17)
    FROM frpm f
    JOIN schools s ON f.cds_cd = s.cds_cd
    WHERE s.fund_type = 'Locally Funded'
)
AND s.fund_type = 'Locally Funded';
```

### Q31 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Missing join to schools for the 'School is not null' filter.

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT pct_free_k12 
FROM frpm 
ORDER BY enroll_k12 DESC 
LIMIT 9, 2;
```

### Q32 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** school_ownership_code (SOC) lives on schools; predicted queries frpm alone, substituting edu_opt_type='66'.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    sch_nm, 
    pct_free_k12
FROM 
    frpm
WHERE 
    cds_cd IN (
        SELECT 
            cds_cd
        FROM 
            frpm
        WHERE 
            edu_opt_type = '66'
        ORDER BY 
            free_meal_k12 DESC
        LIMIT 5
    )
ORDER BY 
    free_meal_k12 DESC;
```

### Q36 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Missing rtype='S' filter.

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
SELECT s.adm_fname1, s.adm_lname1, s.adm_fname2, s.adm_lname2, s.adm_fname3, s.adm_lname3
FROM schools s
JOIN satscores ss ON s.cds_cd = ss.cds
ORDER BY ss.num_ge_1500 DESC
LIMIT 1;
```

### Q37 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes frpm's frpm_k12 (raw FRPM Count K-12, ascending) subquery for gold's satscores num_ge_1500/num_tst_takr MIN-ratio subquery -- a wholesale wrong table/logic.

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
WHERE cds_cd = (
    SELECT cds_cd 
    FROM frpm 
    ORDER BY frpm_k12 ASC 
    LIMIT 1
)
```

### Q39 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** AVG(enroll12) (enrollment_grade_12) instead of gold's AVG(NumTstTakr) (number_test_takers) -- a different real column.

**Gold SQL:**

```sql
SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'
```

**Predicted SQL:**

```sql
SELECT AVG(enroll12) 
FROM satscores 
JOIN schools ON satscores.cds = schools.cds_cd 
WHERE schools.County = 'Fresno' 
AND schools.open_dt BETWEEN '1980-01-01' AND '1980-12-31';
```

### Q40 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops rtype='S' and AvgScrRead IS NOT NULL filters.

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.Phone 
FROM schools s 
JOIN satscores ss ON s.cds_cd = ss.cds 
WHERE s.District = 'Fresno Unified' 
ORDER BY ss.avg_scr_read ASC 
LIMIT 1;
```

### Q41 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's RANK() OVER (PARTITION BY county ORDER BY AvgScrRead DESC) window function with a GROUP BY/IN approximation; also wrong Virtual value ('Yes' vs 'F').

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
SELECT s.School
FROM schools s
JOIN satscores ss ON s.cds_cd = ss.cds
WHERE s.Virtual = 'Yes'
AND (s.County, ss.avg_scr_read) IN (
    SELECT County, MAX(avg_scr_read)
    FROM schools s2
    JOIN satscores ss2 ON s2.cds_cd = ss2.cds
    WHERE s2.Virtual = 'Yes'
    AND s2.County = s.County
    GROUP BY County
    ORDER BY MAX(avg_scr_read) DESC
    LIMIT 5
)
ORDER BY ss.avg_scr_read DESC;
```

### Q46 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters status_type='Special' instead of gold's DOC=31 (district_ownership_code); also adds an unneeded GROUP BY/MAX aggregation.

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.School, MAX(f.enroll_k12) AS max_enroll
FROM frpm f
JOIN schools s ON f.cds_cd = s.cds_cd
WHERE s.status_type = 'Special'
GROUP BY s.School
ORDER BY max_enroll DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) nested aggregate misuse.

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) AS avg_schools_opened
FROM (
    SELECT COUNT(*) 
    FROM schools
    WHERE County = 'Alameda' 
      AND District = 'Elementary School District' 
      AND strftime('%Y', open_dt) = '1980'
    GROUP BY strftime('%m', open_dt)
);
```

### Q48 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Queries frpm (dist_type/cnty_nm) instead of schools (DOC/StatusType/County); also collapses gold's two independent COUNT(*) subqueries into one CASE-based aggregate.

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
    CAST(SUM(CASE WHEN dist_type = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN dist_type = 'Elementary School District' THEN 1 ELSE 0 END) AS ratio
FROM 
    frpm
WHERE 
    cnty_nm = 'Orange';
```

### Q50 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects s.Street (the physical street column) instead of gold's s.MailStreet (mail_street) -- a genuinely different real column, not a naming variant; also drops rtype='S' and AvgScrMath IS NOT NULL filters.

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
SELECT s.School, s.Street 
FROM schools s 
JOIN satscores ss ON s.cds_cd = ss.cds 
ORDER BY ss.avg_scr_math DESC 
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** Uses precomputed pct_free_k12 (a fraction, verified numerically equal to the manual ratio) without gold's *100 scaling factor -- missing scaling, not a wrong column.

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
JOIN schools ON frpm.cds_cd = schools.cds_cd 
WHERE frpm.cnty_nm = 'Los Angeles' 
AND frpm.is_charter = 0 
AND frpm.pct_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools.County='Fremont' substituted for City='Fremont' (wrong column -- county vs city are not equivalent); schools.School LIKE '%State Special School%' substituted for EdOpsCode='SSS' (wrong column); also restructures 'Academic Year' BETWEEN 2014 AND 2015 into an exact string match '2014-2015'.

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT SUM(enroll_5_17) 
FROM frpm 
JOIN schools ON frpm.cds_cd = schools.cds_cd 
WHERE frpm.acad_yr = '2014-2015' 
AND schools.County = 'Fremont' 
AND schools.School LIKE '%State Special School%';
```

### Q77 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** low_grd/high_grd ('K'/'9') substituted for GSserved='K-9' -- different real columns on frpm vs schools; pct_frpm_5_17 selected instead of the manually-scaled FRPM Count Ages 5-17*100/Enrollment ratio (secondary, scale issue).

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    f.pct_frpm_5_17
FROM 
    schools s
JOIN 
    frpm f ON s.cds_cd = f.cds_cd
WHERE 
    s.County = 'Los Angeles' 
    AND f.low_grd = 'K' 
    AND f.high_grd = '9';
```

### Q79 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Virtual='Yes' (invented value) vs gold's 'F'; County correctly used this time (not the frpm/satscores county_name confusion seen at S3).

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT County, COUNT(*) AS school_count
FROM schools
WHERE County IN ('San Diego', 'Santa Barbara') AND Virtual = 'Yes'
GROUP BY County
ORDER BY school_count DESC
LIMIT 1;
```

### Q82 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Missing ABS() around longitude in ORDER BY, reversing which extreme is picked.

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT gs_offered 
FROM schools 
ORDER BY Longitude DESC 
LIMIT 1;
```

### Q83 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** f.low_grd='K'/f.high_grd='8' substituted for s.GSoffered='K-8' (wrong column); f.edu_opt_type substituted for f."NSLP Provision Status" (wrong column, both on frpm but different concepts).

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT 
    s.City, 
    COUNT(*) AS school_count
FROM 
    schools s
JOIN 
    frpm f ON s.cds_cd = f.cds_cd
WHERE 
    f.low_grd = 'K' AND f.high_grd = '8' AND f.edu_opt_type = 'Multiple Provision Types'
GROUP BY 
    s.City;
```

### Q85 (moderate, retrieval) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** Selects pct_free_k12 (verified equal to the raw Free Meal Count K12/Enrollment K12 ratio, unscaled) without gold's *100 factor -- a missing scaling factor, not a wrong column; WHERE filter itself matches gold exactly.

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT frpm.pct_free_k12, frpm.dist_cd 
FROM frpm 
JOIN schools ON frpm.cds_cd = schools.cds_cd 
WHERE schools.adm_fname1 = 'Alusine';
```

### Q87 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Replaces SOC=62 (school_ownership_code) and DOC=54 (district_ownership_code) with ed_ops_nm='Intermediate/Middle School' OR status_type='Unified School' -- different real columns entirely.

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT 
    adm_email1, 
    adm_email2 
FROM 
    schools 
WHERE 
    County = 'San Bernardino' 
    AND City = 'San Bernardino' 
    AND open_dt BETWEEN '2009-01-01' AND '2010-12-31' 
    AND ed_ops_nm = 'Intermediate/Middle School' 
    AND status_type = 'Unified School';
```

---

## debit_card_specializing (23 failures)

### Q1472 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Omits the customers join / Segment='LAM' filter entirely; also fails to SUM per customer, comparing to a global MIN reading instead.

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT cust_id
FROM yearmonth
WHERE date LIKE '2012%' AND consump = (SELECT MIN(consump) FROM yearmonth WHERE date LIKE '2012%')
```

### Q1473 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to yearmonth's 'YYYYMM' text format returns NULL, so the WHERE filter matches zero rows; also drops the per-customer SUM/derived-table + /12 scaling structure.

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consump) 
FROM yearmonth 
JOIN customers ON yearmonth.cust_id = customers.cust_id 
WHERE customers.seg = 'SME' AND strftime('%Y', yearmonth.date) = '2013';
```

### Q1476 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', y.date) misapplied to yearmonth.Date, stored as 'YYYYMM' text, returns NULL for all rows unlike gold's SUBSTR(Date,1,4)='2012'.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN curr = 'CZK' THEN consump ELSE 0 END) - 
    SUM(CASE WHEN curr = 'EUR' THEN consump ELSE 0 END) AS diff_consump
FROM 
    customers
JOIN 
    yearmonth ON customers.cust_id = yearmonth.cust_id
WHERE 
    strftime('%Y', yearmonth.date) = '2012';
```

### Q1479 (moderate, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Groups by strftime('%Y', date) (NULL for all rows since Date is 'YYYYMM' text) instead of gold's SUBSTR(Date,1,4), collapsing all years into one group.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT strftime('%Y', date) AS year, SUM(consump) AS total_consump
FROM yearmonth
WHERE cust_id IN (
    SELECT cust_id
    FROM customers
    WHERE curr = 'CZK'
)
GROUP BY year
ORDER BY total_consump DESC
LIMIT 1;
```

### Q1480 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to 'YYYYMM' text returns NULL, so the WHERE filter matches zero rows; the also-wrong month-extraction/aggregate-choice in GROUP BY/ORDER BY are moot.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date, MAX(consump) AS peak_consumption
FROM yearmonth
JOIN customers ON yearmonth.cust_id = customers.cust_id
WHERE customers.seg = 'SME' AND strftime('%Y', yearmonth.date) = '2013'
GROUP BY date
ORDER BY peak_consumption DESC
LIMIT 1;
```

### Q1481 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** Subqueries reference consump directly on customers (no join to yearmonth in that scope) -- a column that only exists on yearmonth; overall logic diverges hugely from gold's segment-comparison CTEs.

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(consump) 
     FROM yearmonth 
     WHERE cust_id IN (
         SELECT cust_id 
         FROM customers 
         WHERE curr = 'CZK' 
         ORDER BY consump ASC 
         LIMIT 1
     ) AND strftime('%Y', date) = '2013') - 
    (SELECT AVG(consump) 
     FROM yearmonth 
     WHERE cust_id IN (
         SELECT cust_id 
         FROM customers 
         WHERE curr = 'CZK' 
         ORDER BY consump DESC 
         LIMIT 1
     ) AND strftime('%Y', date) = '2013') AS diff_sme_lam,
    
    (SELECT AVG(consump) 
     FROM yearmonth 
     WHERE cust_id IN (
         SELECT cust_id 
         FROM customers 
         WHERE curr = 'CZK' 
         ORDER BY consump ASC 
         LIMIT 1
     ) AND strftime('%Y', date) = '2013') - 
    (SELECT AVG(consump) 
     FROM yearmonth 
     WHERE cust_id IN (
         SELECT cust_id 
         FROM customers 
         WHERE curr = 'CZK' 
         ORDER BY consump DESC 
         LIMIT 1
     ) AND strftime('%Y', date) = '2013') AS diff_lam_kam,
    
    (SELECT AVG(consump) 
     FROM yearmonth 
     WHERE cust_id IN (
         SELECT cust_id 
         FROM customers 
         WHERE curr = 'CZK' 
         ORDER BY consump ASC 
         LIMIT 1
     ) AND strftime('%Y', date) = '2013') - 
    (SELECT AVG(consump) 
     FROM yearmonth 
     WHERE cust_id IN (
         SELECT cust_id 
         FROM customers 
         WHERE curr = 'CZK' 
         ORDER BY consump DESC 
         LIMIT 1
     ) AND strftime('%Y', date) = '2013') AS diff_kam_sme;
```

### Q1482 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to yearmonth's 'YYYYMM' text returns NULL for every CASE WHEN comparison, zeroing out all sums; also restructures gold's three scalar sums into a GROUP BY c.seg aggregation.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    seg, 
    ((SUM(CASE WHEN strftime('%Y', date) = '2013' THEN consump ELSE 0 END) - SUM(CASE WHEN strftime('%Y', date) = '2012' THEN consump ELSE 0 END)) * 100.0 / SUM(CASE WHEN strftime('%Y', date) = '2012' THEN consump ELSE 0 END)) AS percentage_change
FROM 
    yearmonth
JOIN 
    customers ON yearmonth.cust_id = customers.cust_id
WHERE 
    customers.curr = 'EUR' AND customers.seg IN ('SME', 'LAM', 'KAM')
GROUP BY 
    seg;
```

### Q1483 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN uses ISO-hyphenated date bounds ('2013-08-01'/'2013-11-30') against Date stored as plain 'YYYYMM' text, so none of customer 6's monthly rows satisfy the range.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consump) 
FROM yearmonth 
WHERE cust_id = 6 AND date BETWEEN '2013-08-01' AND '2013-11-30';
```

### Q1484 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic'/'Slovakia' used instead of the stored codes 'CZE'/'SVK'; also 'discount' case differs from gold's 'Discount'.

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM gasstations WHERE ctry = 'Czech Republic' AND seg = 'discount') - 
    (SELECT COUNT(*) FROM gasstations WHERE ctry = 'Slovakia' AND seg = 'discount') AS diff;
```

### Q1490 (moderate, aggregate) -- **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** Uses INNER JOIN where gold's LEFT JOIN preserves customers with no yearmonth rows; also drops the COUNT(DISTINCT...) per-customer dedup.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consump > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM yearmonth 
JOIN customers ON yearmonth.cust_id = customers.cust_id 
WHERE customers.seg = 'LAM';
```

### Q1493 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN '2012-02-01' AND '2012-02-29' (ISO-date literals) applied to Date stored as 'YYYYMM' text ('201202') never matches lexicographically, causing zero rows instead of gold's exact match Date='201202'.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consump > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(cust_id) 
FROM yearmonth 
WHERE date BETWEEN '2012-02-01' AND '2012-02-29';
```

### Q1498 (simple, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Missing GROUP BY entirely (gold groups by month); also uses MAX instead of SUM, returning the single largest individual reading instead of the peak month's total.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consump) FROM yearmonth WHERE date LIKE '2012%'
```

### Q1505 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** currency='euro' instead of the stored code 'EUR'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.cust_id) 
FROM customers c 
JOIN yearmonth y ON c.cust_id = y.cust_id 
WHERE c.curr = 'euro' AND y.consump > 1000;
```

### Q1506 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' instead of the stored code 'CZE'.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.descr 
FROM products p 
JOIN transactions_1k t ON p.prod_id = t.prod_id 
JOIN gasstations g ON t.gs_id = g.gs_id 
WHERE g.ctry = 'Czech Republic';
```

### Q1509 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' instead of the stored code 'CZE'.

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
FROM transactions_1k t
JOIN gasstations g ON t.gs_id = g.gs_id
WHERE g.ctry = 'Czech Republic' AND t.date > '2012-01-01';
```

### Q1514 (simple, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Predicted omits DISTINCT and the (redundant, non-filtering) gasstations join that gold itself never references any column of; if multiple transactions share this exact date/time, duplicate currency values would appear.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT c.curr 
FROM customers c 
JOIN transactions_1k t 
ON c.cust_id = t.cust_id 
WHERE t.date = '2012-08-24' AND t.time = '16:25:00';
```

### Q1524 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Join and Country column are correct (gasstations); WHERE uses t.amt (Amount) instead of t.price (Price) -- a genuinely different real column.

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT DISTINCT g.ctry 
FROM transactions_1k t 
JOIN gasstations g ON t.gs_id = g.gs_id 
WHERE t.date = '2012-08-24' AND t.amt = 548.4;
```

### Q1525 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Joins yearmonth (a monthly-aggregate table with 'YYYYMM' dates) instead of gold's transactions_1k for the exact-date filter Date='2012-08-25' -- a different real table serving the same role, and the date format never matches yearmonth's Date column.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN curr = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM customers 
JOIN yearmonth ON customers.cust_id = yearmonth.cust_id 
WHERE yearmonth.date = '2012-08-25';
```

### Q1526 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Subquery uses t.amt=634.8 instead of gold's price=634.8 (different real column) to identify the customer; also misses the per-year SUM aggregation, self-joining yearmonth month-rows directly.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT (consump_2012 - consump_2013) / consump_2012 AS decrease_rate
FROM (
    SELECT 
        t.cust_id,
        y1.consump AS consump_2012,
        y2.consump AS consump_2013
    FROM 
        transactions_1k t
    JOIN 
        yearmonth y1 ON t.cust_id = y1.cust_id AND strftime('%Y-%m-%d', y1.date) = '2012-08-25'
    JOIN 
        yearmonth y2 ON t.cust_id = y2.cust_id AND strftime('%Y', y2.date) = '2013'
    WHERE 
        t.amt = 634.8 AND strftime('%Y-%m-%d', t.date) = '2012-08-25'
) subquery;
```

### Q1528 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Unnecessary JOIN to transactions_1k multiplies each gas station row by its transaction count, inflating COUNT(*)/SUM; also 'premium' case differs from gold's 'Premium'.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN g.seg = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS premium_percentage
FROM 
    gasstations g
JOIN 
    transactions_1k t ON g.gs_id = t.gs_id
WHERE 
    g.ctry = 'SVK';
```

### Q1529 (moderate, aggregate) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** Sums amt alone instead of amt*price (missing the Price multiplication) in both total_spent and the August-2012 conditional sum.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amt) AS total_spent, 
       SUM(CASE WHEN strftime('%Y-%m', date) = '2012-08' THEN amt ELSE 0 END) AS aug_2012_spent
FROM transactions_1k
WHERE cust_id = 38508;
```

### Q1531 (moderate, aggregate) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** Ranks the top customer by SUM(amt) instead of gold's SUM(amt*price); also computes average_price_per_item as plain AVG(price) instead of the amount-weighted SUM(price*amount)/SUM(amount).

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT 
    t.cust_id, 
    AVG(t.price) AS avg_price_per_item, 
    c.curr
FROM 
    transactions_1k t
JOIN 
    customers c ON t.cust_id = c.cust_id
GROUP BY 
    t.cust_id, c.curr
ORDER BY 
    SUM(t.amt) DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses Price alone (>29.00) instead of gold's Price/Amount>29.00 ratio; also date format LIKE '2012-08-%' won't match yearmonth's stored 'YYYYMM' text ('201208').

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT y.consump
FROM yearmonth y
JOIN customers c ON y.cust_id = c.cust_id
JOIN transactions_1k t ON c.cust_id = t.cust_id
WHERE t.prod_id = 5 AND t.price > 29.00 AND y.date LIKE '2012-08-%';
```

---

## european_football_2 (34 failures)

### Q1025 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season=2016 (bare integer) instead of gold's string '2015/2016' -- season is stored as 'YYYY/YYYY' text, so this never matches.

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League L 
JOIN Match M ON L.id = M.league_id 
WHERE M.season = 2016 
GROUP BY L.name 
ORDER BY SUM(M.home_goals + M.away_goals) DESC 
LIMIT 1;
```

### Q1028 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Joins Team on T1.away_team_id = T3.id instead of T3.team_api_id (id is Team's unrelated surrogate key, not the FK team_api_id, verified different value spaces) -- produces wrong team names entirely; also season=2010 instead of '2009/2010', and collapses gold's HAVING COUNT(*)=(SELECT MAX(win_count)...) tie logic into a plain ORDER BY COUNT(*) DESC LIMIT 1.

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T3.team_nm 
FROM Match AS T1 
JOIN League AS T2 ON T1.league_id = T2.id 
JOIN Team AS T3 ON T1.away_team_id = T3.id 
WHERE T2.name = 'Scotland Premier League' AND T1.season = 2010 AND T1.away_goals > T1.home_goals 
GROUP BY T3.team_nm 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1030 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season=2016 (bare integer) instead of gold's string '2015/2016'.

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League L 
JOIN Match M ON L.id = M.league_id 
WHERE M.season = 2016 AND M.home_goals = M.away_goals 
GROUP BY L.name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1031 (challenging, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- gold deduplicates identical age values across matching players/snapshots; predicted returns one row per matching Player_Attributes row instead.

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
SELECT 
    strftime('%Y', 'now') - strftime('%Y', P.bday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.bday)) AS age
FROM 
    Player P
JOIN 
    Player_Attributes PA ON P.plr_api_id = PA.plr_api_id
WHERE 
    PA.date BETWEEN '2013-01-01' AND '2015-12-31'
    AND PA.sprt_spd >= 97;
```

### Q1032 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's HAVING COUNT(m.id)=(SELECT MAX(match_count) FROM (...)) tie-preserving pattern into a plain GROUP BY + ORDER BY COUNT(*) DESC LIMIT 1, which would drop ties.

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(*) AS match_count
FROM League L
JOIN Match M ON L.id = M.league_id
GROUP BY L.id
ORDER BY match_count DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- multiple Team_Attributes rows (different dates) could share the same team_fifa_api_id within the buildUpPlaySpeed range, causing duplicate rows.

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT fifa_team_id 
FROM Team_Attributes 
WHERE bu_spd > 50 AND bu_spd < 60;
```

### Q1036 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** References TA.season, which doesn't exist on Team_Attributes (no such column) -- the actual date info is on Team_Attributes.date (already available, no join needed); season only exists on the unrelated Match table.

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T.team_nm 
FROM Team AS T 
JOIN Team_Attributes AS TA ON T.team_api_id = TA.team_api_id 
WHERE TA.season = 2012 AND TA.bu_pass > (SELECT AVG(bu_pass) FROM Team_Attributes WHERE season = 2012);
```

### Q1037 (challenging, aggregate) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Uses COUNT(*) instead of gold's COUNT(DISTINCT t1.id) -- a player with multiple Player_Attributes snapshots in the birth-year range would be counted multiple times instead of once.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN pref_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.plr_api_id = Player.plr_api_id 
WHERE strftime('%Y', Player.bday) BETWEEN '1987' AND '1992';
```

### Q1058 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Uses LIMIT inside an OVER(...) window function clause, which is invalid SQL syntax (near "LIMIT": syntax error).

**Gold SQL:**

```sql
SELECT A FROM (SELECT AVG(finishing) result, 'highest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MAX(height) FROM Player) UNION SELECT AVG(finishing) result, 'shortest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MIN(height) FROM Player)) tmp ORDER BY result DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN AVG(T1.finish) OVER (PARTITION BY T2.ht ORDER BY T2.ht DESC LIMIT 1) > AVG(T1.finish) OVER (PARTITION BY T2.ht ORDER BY T2.ht ASC LIMIT 1) THEN 'highest'
        ELSE 'shortest'
    END AS result
FROM 
    Player_Attributes AS T1
JOIN 
    Player AS T2 ON T1.plr_api_id = T2.plr_api_id;
```

### Q1076 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Two SELECT statements are concatenated without UNION or a statement separator, causing a syntax error.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT AVG(T1.ball_ctrl) AS avg_ball_ctrl_abdou
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id
WHERE T2.plr_nm = 'Abdou Diallo'
GROUP BY T2.plr_nm

SELECT AVG(T1.ball_ctrl) AS avg_ball_ctrl_aaron
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id
WHERE T2.plr_nm = 'Aaron Appindangoye'
GROUP BY T2.plr_nm;
```

### Q1080 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** atk_wr='remain' -- an invented/garbage value; real domain is 'low'/'medium'/'high' (verified).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE pref_foot = 'left' AND atk_wr = 'remain';
```

### Q1084 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** def_wr>0 misapplies a numeric comparison to a text-valued column (real values are 'low'/'medium'/'high', not numeric) -- likely matches zero rows instead of def_wr='high'; also adds an unrelated pos='GK' filter not in gold.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT pa.plr_api_id) 
FROM Player_Attributes pa 
JOIN Player p ON pa.plr_api_id = p.plr_api_id 
WHERE strftime('%Y', p.bday) < '1986' 
AND pa.pos = 'GK' 
AND pa.def_wr > 0;
```

### Q1088 (moderate, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- some distinct player_api_id values share the same player_name, so gold's DISTINCT collapses those names together while predicted returns one row per player_api_id (verified: 1109 rows vs gold's 1105).

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT plr_nm 
FROM Player 
WHERE plr_api_id IN (
    SELECT plr_api_id 
    FROM Player_Attributes 
    WHERE volleys > 70 AND dribble > 70
)
```

### Q1092 (simple, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's HAVING COUNT(t2.id)=(SELECT MAX(match_count) FROM (...)) tie-preserving pattern into a plain GROUP BY + ORDER BY COUNT(*) DESC LIMIT 1.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League L 
JOIN Match M ON L.id = M.league_id 
WHERE M.season = '2008/2009' 
GROUP BY L.name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1102 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date='2016-06-23' (exact match) never matches since Player_Attributes.date is stored as 'YYYY-MM-DD 00:00:00' (verified) -- gold's SUBSTR(date,1,10) transformation is missing.

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT plr_nm 
FROM Player 
WHERE plr_api_id IN (
    SELECT plr_api_id 
    FROM Player_Attributes 
    WHERE date = '2016-06-23' AND ovr_rtg = 77
) 
ORDER BY bday ASC 
LIMIT 1;
```

### Q1103 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date='2016-02-04' (exact match) won't match the stored 'YYYY-MM-DD 00:00:00' timestamp -- missing gold's SUBSTR(date,1,10) truncation.

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT T1.ovr_rtg FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id WHERE T2.plr_nm = 'Aaron Mooy' AND T1.date = '2016-02-04'
```

### Q1105 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date='2015-05-01' (exact match) won't match the stored 'YYYY-MM-DD 00:00:00' timestamp -- missing gold's LIKE '2015-05-01%' pattern.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.atk_wr FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id WHERE T2.plr_nm = 'Francesco Migliore' AND T1.date = '2015-05-01'
```

### Q1107 (moderate, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's secondary ORDER BY tie-break (date ASC after crossing DESC) -- if multiple dates tie for Kevin Constant's max crossing, a different date could be picked; also joins Player via player_api_id instead of gold's player_fifa_api_id.

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.date 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id 
WHERE T2.plr_nm = 'Kevin Constant' 
ORDER BY T1.cross DESC 
LIMIT 1;
```

### Q1110 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date='2010-02-22' (exact match) won't match the stored 'YYYY-MM-DD 00:00:00' timestamp -- missing gold's LIKE '2010-02-22%' pattern.

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT bu_pass_cls 
FROM Team_Attributes 
JOIN Team ON Team_Attributes.team_api_id = Team.team_api_id 
WHERE Team.team_nm = 'FC Lorient' AND Team_Attributes.date = '2010-02-22';
```

### Q1113 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date='2015-09-10' (exact match) won't match the stored 'YYYY-MM-DD 00:00:00' timestamp -- missing gold's LIKE '2015-09-10%' pattern.

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT ta.def_aggr_cls 
FROM Team_Attributes ta 
JOIN Team t ON ta.team_api_id = t.team_api_id 
WHERE t.team_nm = 'Hannover 96' AND ta.date = '2015-09-10';
```

### Q1114 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date BETWEEN '2007-02-22' AND '2016-04-21' compares against timestamps like '...00:00:00' -- since the upper bound is a bare date string, any row exactly on 2016-04-21 is lexicographically excluded (missing gold's SUBSTR(date,1,10) truncation); also joins via player_api_id instead of gold's player_fifa_api_id.

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(T1.ovr_rtg) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id 
WHERE T2.plr_nm = 'Marko Arnautovic' 
AND T1.date BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date='2013-07-12' (exact match) never matches the stored 'YYYY-MM-DD 00:00:00' timestamp values -- missing gold's SUBSTR(date,1,10) truncation, so the self-join finds no matching pair at all.

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT 
    ((p1.ovr_rtg - p2.ovr_rtg) / p2.ovr_rtg) * 100 AS percentage_difference
FROM 
    Player_Attributes p1
JOIN 
    Player_Attributes p2 ON p1.date = p2.date
JOIN 
    Player pl1 ON p1.plr_api_id = pl1.plr_api_id
JOIN 
    Player pl2 ON p2.plr_api_id = pl2.plr_api_id
WHERE 
    pl1.plr_nm = 'Landon Donovan' 
    AND pl2.plr_nm = 'Jordan Bowery' 
    AND p1.date = '2013-07-12';
```

### Q1122 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters/orders on strength (a different real Player_Attributes column) instead of gold's overall_rating; also compares Player.id to Player_Attributes.id -- two unrelated surrogate keys, not a valid link.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT plr_nm FROM Player WHERE id = (SELECT id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1124 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Joins Player.id to Player_Attributes.plr_api_id -- unrelated surrogate/FK values (verified different value spaces), not a valid key match; also applies AVG()/> comparison to atk_wr, a categorical text column, instead of gold's simple ='high' equality.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.plr_nm
FROM Player p
JOIN Player_Attributes pa ON p.id = pa.plr_api_id
WHERE pa.atk_wr > (SELECT AVG(pa2.atk_wr) FROM Player_Attributes pa2)
```

### Q1130 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extraneous cc_pass > 0 condition not in gold; if chanceCreationPassing is NULL for any 'Safe'-classified row, this comparison evaluates to NULL and incorrectly excludes it.

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T.team_abbr 
FROM Team_Attributes AS TA 
JOIN Team AS T ON TA.team_api_id = T.team_api_id 
WHERE TA.cc_pass_cls = 'Safe' AND TA.cc_pass > 0;
```

### Q1134 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Computes (gk_div - jump) per matching row instead of gold's SUM(CASE id=6 THEN jumping) - SUM(CASE id=23 THEN jumping) -- goalkeeper_diving is substituted for jumping in one term (a different, unrelated real column), and the row-vs-aggregate structure differs entirely.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL:**

```sql
SELECT (gk_div - jump) AS diff FROM Player_Attributes WHERE id = 6 OR id = 23
```

### Q1135 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** pref_foot='Right' (capitalized) vs gold's lowercase 'right'.

**Gold SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT id FROM Player_Attributes WHERE pref_foot = 'Right' ORDER BY potential ASC LIMIT 4
```

### Q1136 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extraneous atk_wr > 0 condition -- atk_wr is a categorical text column ('high'/'medium'/'low'); comparing it to 0 numerically evaluates false for all non-numeric text values, so the entire query likely returns zero rows instead of gold's count.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE cross = (SELECT MAX(cross) FROM Player_Attributes) 
AND pref_foot = 'left' 
AND atk_wr > 0;
```

### Q1139 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Belgian Jupiler League' instead of the actual stored 'Belgium Jupiler League' (verified) -- the subquery returns NULL, so league_id filter matches nothing; also date='2008-09-24' (exact match) won't match the stored 'YYYY-MM-DD 00:00:00' timestamp.

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT home_goals, away_goals 
FROM Match 
WHERE date = '2008-09-24' 
AND league_id = (SELECT id FROM League WHERE name = 'Belgian Jupiler League');
```

### Q1144 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's WHERE weight=(SELECT MAX(weight)...) tie-preserving equality into ORDER BY wt DESC LIMIT 1, which would drop any players tied for max weight.

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT finish, curve FROM Player_Attributes WHERE plr_api_id IN (SELECT plr_api_id FROM Player ORDER BY wt DESC LIMIT 1)
```

### Q1145 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2015-2016' (hyphen) instead of the actual stored format '2015/2016' (slash) -- never matches.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(*) AS game_count
FROM League L
JOIN Match M ON L.id = M.league_id
WHERE M.season = '2015-2016'
GROUP BY L.name
ORDER BY game_count DESC
LIMIT 4;
```

### Q1146 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Joins Match.away_team_id to Team.id instead of Team.team_api_id -- id is Team's unrelated surrogate primary key, not the FK; produces a mismatched/wrong team name.

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.team_nm 
FROM Match AS T1 
JOIN Team AS T2 ON T1.away_team_id = T2.id 
ORDER BY T1.away_goals DESC 
LIMIT 1;
```

### Q1147 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Orders by strength (a different real column) instead of gold's overall_rating to find the 'best' player; also collapses the MAX-equality tie-preserving pattern into ORDER BY...LIMIT 1.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT plr_nm FROM Player WHERE plr_api_id = (SELECT plr_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1148 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses strength (a different real column) instead of gold's overall_rating for the >70 threshold; also drops the outer WHERE height<180 filter (changing the denominator to ALL players, not just those under 180cm), and uses COUNT(*) instead of COUNT(DISTINCT id).

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN ht < 180 AND strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player 
JOIN Player_Attributes ON Player.plr_api_id = Player_Attributes.plr_api_id;
```

---

## financial (21 failures)

### Q89 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the frequency='POPLATEK PO OBRATU' filter entirely, replacing it with an unrelated card-issued-vs-transaction-date comparison (ca.issued_dt > t.date); also region='East Bohemia' (wrong case, real value is lowercase 'east Bohemia', verified).

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT a.acct_id) 
FROM account a 
JOIN disp d ON a.acct_id = d.acct_id 
JOIN client c ON d.client_id = c.client_id 
JOIN district dist ON c.dist_id = dist.dist_id 
JOIN card ca ON d.disp_id = ca.disp_id 
JOIN trans t ON a.acct_id = t.acct_id 
WHERE ca.issued_dt > t.date AND dist.region = 'East Bohemia';
```

### Q93 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** region='North Bohemia' (wrong case, real value is lowercase 'north Bohemia', verified).

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM client 
JOIN district ON client.dist_id = district.dist_id 
WHERE client.gender = 'M' 
AND district.region = 'North Bohemia' 
AND district.avg_sal > 8000;
```

### Q98 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an invented status='A' filter not in gold; also freq='W' is a wrong/invented abbreviation instead of the actual stored value 'POPLATEK TYDNE' (verified).

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.acct_id
FROM account a
JOIN loan l ON a.acct_id = l.acct_id
WHERE l.status = 'A' AND strftime('%Y', l.date) = '1997'
AND a.freq = 'W'
ORDER BY l.amount ASC
LIMIT 1;
```

### Q112 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Aliases disp as 'd' and selects d.dist_nm -- dist_nm doesn't exist on disp; the actual district name requires joining account and district (client->disp->account->district), both of which are omitted entirely.

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
SELECT d.dist_nm 
FROM client c 
JOIN disp d ON c.client_id = d.client_id 
WHERE c.gender = 'F' AND c.birth_dt = '1976-01-29';
```

### Q115 (challenging, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's GROUP BY T2.A4 (num_inhab) entirely -- predicted mixes an aggregate (COUNT/CASE percentage) with a non-aggregated ORDER BY on num_inhab DESC LIMIT 1, without any GROUP BY, a fundamentally different (and ambiguous) computation; also region='South Bohemia' is wrong case (real value is lowercase 'south Bohemia').

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT (COUNT(CASE WHEN c.gender = 'M' THEN 1 END) * 100.0 / COUNT(c.client_id)) AS male_percentage
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN account a ON d.acct_id = a.acct_id
JOIN district dist ON a.dist_id = dist.dist_id
WHERE dist.region = 'South Bohemia'
ORDER BY dist.num_inhab DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Computes (MAX(balance)-MIN(balance))/MIN(balance) over the ENTIRE date range BETWEEN '1993-03-22' AND '1998-12-27' instead of gold's exact before/after comparison at those two SPECIFIC dates; also adds an invented status='A' filter and an unneeded GROUP BY client_id.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(t.bal) - MIN(t.bal)) / MIN(t.bal) AS increase_rate
FROM 
    client c
JOIN 
    disp d ON c.client_id = d.client_id
JOIN 
    account a ON d.acct_id = a.acct_id
JOIN 
    loan l ON a.acct_id = l.acct_id
JOIN 
    trans t ON a.acct_id = t.acct_id
WHERE 
    l.date = '1993-07-05' AND
    l.status = 'A' AND
    t.date BETWEEN '1993-03-22' AND '1998-12-27'
GROUP BY 
    c.client_id;
```

### Q118 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='A' instead of gold's status='C' -- a different real status code.

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM loan 
WHERE amount < 100000;
```

### Q125 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters l.amount > 0 instead of gold's d.A12 (unemp_95) IS NOT NULL AND > 0 -- a completely different, unrelated real column (loan amount vs district unemployment rate); also status='A' instead of gold's 'D', and drops the '/A12*100' percentage-scaling from the computation.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.unemp_96 - d.unemp_95 AS unemp_increment
FROM loan l
JOIN account a ON l.acct_id = a.acct_id
JOIN disp d1 ON a.acct_id = d1.acct_id
JOIN client c ON d1.client_id = c.client_id
JOIN district d ON c.dist_id = d.dist_id
WHERE l.status = 'A' AND l.amount > 0;
```

### Q128 (moderate, aggregate) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Identical underlying result (verified: same 9 district names in the same order) -- only the SELECT list has 2 extra columns (dist_id, num_female_clients count) that gold doesn't return; a strict evaluator would flag this as a mismatch despite equivalent logic.

**Gold SQL:**

```sql
SELECT T2.A2 FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' GROUP BY T2.district_id, T2.A2 ORDER BY COUNT(T1.client_id) DESC LIMIT 9
```

**Predicted SQL:**

```sql
SELECT d.dist_id, d.dist_nm, COUNT(c.client_id) AS num_female_clients
FROM district d
JOIN client c ON d.dist_id = c.dist_id
WHERE c.gender = 'F'
GROUP BY d.dist_id, d.dist_nm
ORDER BY num_female_clients DESC
LIMIT 9;
```

### Q129 (moderate, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a GROUP BY dist_nm + SUM(amount) aggregation gold doesn't have -- gold ranks individual qualifying transactions by amount (LIMIT 10 transactions, possibly with duplicate district names), not aggregated per-district totals; also type='withdrawal' is an invented English value (real domain is Czech: 'VYDAJ'/'PRIJEM'/'VYBER', verified).

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT d.dist_nm
FROM district d
JOIN client c ON d.dist_id = c.dist_id
JOIN disp dp ON c.client_id = dp.client_id
JOIN account a ON dp.acct_id = a.acct_id
JOIN trans t ON a.acct_id = t.acct_id
WHERE t.type = 'withdrawal' AND t.date BETWEEN '1996-01-01' AND '1996-01-31'
GROUP BY d.dist_nm
ORDER BY SUM(t.amount) DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** freq='M' instead of gold's 'POPLATEK MESICNE' -- invented abbreviation.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM loan 
JOIN account ON loan.acct_id = account.acct_id 
WHERE loan.amount >= 250000 
AND loan.date BETWEEN '1995-01-01' AND '1997-12-31' 
AND account.freq = 'M';
```

### Q137 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Drops the loan join and the (status='C' OR status='D') filter entirely -- counts ALL accounts in district 1 regardless of loan status, instead of gold's loan-status-filtered count.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM account 
WHERE dist_id = 1;
```

### Q145 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters c.type='credit' (card.type, whose real domain is 'gold'/'classic'/'junior', verified) instead of gold's trans.operation='VYBER KARTOU' (card withdrawal operation) -- a completely different real column/table, and 'credit' isn't even a valid card.type value.

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.acct_id
FROM account a
JOIN disp d ON a.acct_id = d.acct_id
JOIN card c ON d.disp_id = c.disp_id
JOIN trans t ON a.acct_id = t.acct_id
WHERE c.type = 'credit' AND t.date LIKE '1998%' AND t.amount < (SELECT AVG(amount) FROM trans WHERE date LIKE '1998%')
```

### Q149 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** SELECT d.dist_nm -- 'd' is aliased to disp, not district; district is already joined as alias 'di', which does hold dist_nm -- an alias mix-up on an already-joined table, not a missing join; also substitutes an entirely different logic (LEFT JOIN loan IS NULL) for gold's disp.type <> 'OWNER' filter.

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
SELECT DISTINCT d.dist_nm, c.type
FROM account a
JOIN disp d ON a.acct_id = d.acct_id
JOIN client cl ON d.client_id = cl.client_id
JOIN card c ON d.disp_id = c.disp_id
JOIN district di ON a.dist_id = di.dist_id
LEFT JOIN loan l ON a.acct_id = l.acct_id
WHERE l.loan_id IS NULL AND di.avg_sal BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters d.num_inhab > 4000 (population, A4) instead of gold's crimes_95 > 4000 (A15, crime count) -- a completely different, unrelated real column; also computes AVG(crimes_95) via a direct join instead of gold's subquery-based district_id IN (...), which could double-count district crime values.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.crimes_95) 
FROM district d 
JOIN account a ON d.dist_id = a.dist_id 
WHERE d.num_inhab > 4000 AND strftime('%Y', a.date) >= '1997';
```

### Q159 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters t.type='withdrawal' (an invented value; trans.type's real domain is 'PRIJEM'/'VYDAJ'/'VYBER', verified) instead of gold's operation='VYBER' (trans.operation's real domain is different) -- type and operation are different real columns; also adds an invented op='cash' condition, and the SELECT list is missing most of gold's T4.* columns.

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT t.txn_id, t.date, t.amount
FROM trans t
JOIN disp d ON t.acct_id = d.acct_id
WHERE d.client_id = 3356 AND t.type = 'withdrawal' AND t.op = 'cash';
```

### Q169 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the disp.type='OWNER' filter entirely -- includes DISPONENT-type dispositions too, not just account owners; also drops the *100 scaling factor, computing a raw ratio instead of a percentage.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN strftime('%Y', l.date) = '1997' THEN l.amount ELSE 0 END) - 
     SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END)) / 
    SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END) AS growth_rate
FROM 
    loan l
JOIN 
    account a ON l.acct_id = a.acct_id
JOIN 
    disp d ON a.acct_id = d.acct_id
JOIN 
    client c ON d.client_id = c.client_id
WHERE 
    c.gender = 'M';
```

### Q173 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses trans (individual transaction records, filtered by type='VYDAJ' and a single amount=3539) instead of gold's "order" table (standing payment orders, aggregated via SUM(amount) GROUP BY account_id,k_symbol) -- a completely different real table/concept; also drops k_symbol from the SELECT/GROUP BY entirely.

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT 
    freq, 
    SUM(amount) AS total_debit_amount
FROM 
    account
JOIN 
    trans ON account.acct_id = trans.acct_id
WHERE 
    account.acct_id = 3 AND trans.type = 'VYDAJ' AND trans.amount = 3539
GROUP BY 
    freq;
```

### Q186 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** freq='W' instead of gold's 'POPLATEK TYDNE' -- invented abbreviation.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM client AS T1 
JOIN disp AS T2 ON T1.client_id = T2.client_id 
JOIN account AS T3 ON T2.acct_id = T3.acct_id 
WHERE T3.freq = 'W';
```

### Q192 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** status='A' instead of gold's IN ('C','D'); also entirely replaces the frequency='POPLATEK PO OBRATU' filter with an unrelated date > (SELECT MAX(date) FROM trans) condition -- a wholesale substitution unrelated to the actual question.

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(amount) 
FROM loan 
WHERE status = 'A' 
AND date > (SELECT MAX(date) FROM trans);
```

### Q194 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** card.type='HighLevel' is an invented value (real domain: 'gold'/'classic'/'junior', verified; gold wants 'gold'); also adds an entirely invented subquery restricting to clients with an active loan (status='A') that gold's query doesn't have at all.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, strftime('%Y', 'now') - strftime('%Y', c.birth_dt) AS age
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN card ca ON d.disp_id = ca.disp_id
WHERE ca.type = 'HighLevel' AND d.type = 'OWNER'
AND c.client_id IN (
    SELECT DISTINCT client_id
    FROM disp
    WHERE acct_id IN (
        SELECT acct_id
        FROM loan
        WHERE status = 'A'
    )
);
```

---

## formula_1 (40 failures)

### Q846 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Queries results (with position/statusId filters) instead of gold's qualifying table; entirely drops the ORDER BY q1 DESC LIMIT 5 logic that identifies the top-5 qualifiers.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.drv_ref 
FROM drivers d 
JOIN results r ON d.drv_id = r.drv_id 
WHERE r.race_id = 20 AND r.position > 0 AND r.status_id IN (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20);
```

### Q850 (simple, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- multiple races share the same name across different years/circuits in Germany, so duplicate race names would appear.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT races.name 
FROM races 
JOIN circuits ON races.cir_id = circuits.cir_id 
WHERE circuits.country = 'Germany';
```

### Q854 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters circuits.name='Australian Grand Prix' directly -- circuits.name holds circuit names, not race names (verified: 0 circuits named 'Australian Grand Prix'); the race name only exists on races.name, requiring the races join that's entirely dropped.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Australian Grand Prix'
```

### Q857 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters circuits.name='Abu Dhabi Grand Prix' directly -- circuits.name holds circuit names, not race names; requires the races join that's entirely dropped.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Abu Dhabi Grand Prix'
```

### Q861 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** q3='0:01:54' (exact match, wrong format) instead of gold's LIKE '1:54%' -- q3 is stored as 'M:SS.mmm' text (e.g. '1:54.325'), so the exact literal never matches.

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT number FROM qualifying WHERE race_id = 903 AND q3 = '0:01:54';
```

### Q865 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters position IS NOT NULL instead of gold's time IS NOT NULL -- different real columns on results; also drops the dob IS NOT NULL filter, so a driver with a NULL dob could incorrectly win the ORDER BY dob ASC LIMIT 1.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT fname, lname 
FROM drivers 
WHERE drv_id IN (
    SELECT drv_id 
    FROM results 
    WHERE race_id = 592 AND position IS NOT NULL
) 
ORDER BY dob ASC 
LIMIT 1;
```

### Q866 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** time='0:01:27' (exact match, wrong format) instead of gold's LIKE '1:27%' -- lap time is stored as 'M:SS.mmm' text; also drops DISTINCT.

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT d.fname, d.lname, d.url 
FROM drivers d 
JOIN laptimes lt ON d.drv_id = lt.drv_id 
WHERE lt.race_id = 161 AND lt.time = '0:01:27';
```

### Q868 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters circuits.name='Malaysian Grand Prix' directly -- circuits.name holds circuit names, not race names; requires the races join that's entirely dropped; also adds an extra location column.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT location, lat, lng FROM circuits WHERE name = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Queries constructorStandings (cumulative season standings) instead of gold's constructorResults (points earned in that specific race) -- a different real table with different semantics, despite both having a 'points' column.

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.url 
FROM constructors c 
JOIN constructorStandings cs ON c.ctor_id = cs.ctor_id 
WHERE cs.race_id = 9 
ORDER BY cs.points DESC 
LIMIT 1;
```

### Q872 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** q3='0:01:33' (exact match, wrong format) instead of gold's LIKE '1:33%' pattern.

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT d.code 
FROM drivers d 
JOIN qualifying q ON d.drv_id = q.drv_id 
WHERE q.race_id = 45 AND q.q3 = '0:01:33';
```

### Q877 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the time IS NOT NULL filter entirely -- a driver with a NULL finish time (e.g., DNF) could incorrectly be included and win the ORDER BY dob DESC LIMIT 1.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.fname, d.lname, d.dob
FROM drivers d
JOIN results r ON d.drv_id = r.drv_id
WHERE r.race_id = 872
ORDER BY d.dob DESC
LIMIT 1;
```

### Q879 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Compares fast_lap_spd via a plain (uncast) MAX() -- fastestLapSpeed is stored as TEXT, so this performs string comparison instead of gold's CAST(...AS REAL) numeric comparison, likely picking the wrong 'fastest' row.

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.nation 
FROM drivers d 
JOIN results r ON d.drv_id = r.drv_id 
WHERE r.fast_lap_spd = (SELECT MAX(fast_lap_spd) FROM results);
```

### Q881 (moderate, aggregate) -- **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds GROUP BY d.drv_id, producing one row per driver, when gold computes a single overall completion percentage across ALL results for that date (no GROUP BY at all); also uses race-count as denominator instead of driver-count.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT 
    d.fname || ' ' || d.lname AS driver_name,
    COUNT(r.res_id) * 100.0 / (SELECT COUNT(*) FROM races WHERE date = '1983-07-16') AS completion_rate
FROM 
    drivers d
JOIN 
    results r ON d.drv_id = r.drv_id
JOIN 
    races ra ON r.race_id = ra.race_id
WHERE 
    ra.date = '1983-07-16'
GROUP BY 
    d.drv_id;
```

### Q894 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT-list uses lt.time (a formatted time string) instead of gold's milliseconds (numeric) -- lapTimes has both as separate columns; the ORDER BY correctly still uses ms, but the wrong column is what's displayed.

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT lt.time, d.fname || ' ' || d.lname AS driver, r.name AS race
FROM lapTimes lt
JOIN drivers d ON lt.drv_id = d.drv_id
JOIN races r ON lt.race_id = r.race_id
ORDER BY lt.ms ASC
LIMIT 1;
```

### Q896 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses results (per-race finishing position) instead of gold's driverStandings (season-cumulative standings position after each race) -- a different real table/semantic concept despite both having a 'position' column.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.position = 1 THEN 0 ELSE 1 END) AS REAL) * 100 / COUNT(*) 
FROM races AS T1 
JOIN results AS T2 ON T1.race_id = T2.race_id 
JOIN drivers AS T3 ON T2.drv_id = T3.drv_id 
WHERE T3.fname = 'Lewis' AND T3.lname = 'Hamilton' AND T1.year >= 2010;
```

### Q897 (moderate, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's GROUP BY (forename,surname,nationality) + ORDER BY COUNT(wins) DESC LIMIT 1 entirely, replacing it with a single WHERE wins=(SELECT MAX(wins)...) filter -- a fundamentally different computation.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.fname, d.lname, d.nation, MAX(ds.points) AS max_points
FROM drivers d
JOIN driverStandings ds ON d.drv_id = ds.drv_id
WHERE ds.wins = (SELECT MAX(wins) FROM driverStandings);
```

### Q898 (simple, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Uses MySQL-style TIMESTAMPDIFF(YEAR, dob, CURDATE()) -- not valid SQLite syntax; SQLite reports 'no such column: YEAR' since YEAR is treated as a bare identifier, not a recognized function/keyword.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(TIMESTAMPDIFF(YEAR, dob, CURDATE())) AS age, fname, lname FROM drivers WHERE nation = 'Japanese'
```

### Q902 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses results (car race entries) instead of gold's driverStandings for the position filter; also filters rs.number<20 (car number) instead of position -- a completely different, unrelated column.

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT r.name 
FROM races r 
JOIN results rs ON r.race_id = rs.race_id 
JOIN drivers d ON rs.drv_id = d.drv_id 
WHERE d.fname = 'Alex' AND d.lname = 'Yoong' AND rs.number < 20;
```

### Q904 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Orders by results.fastestLapTime (a per-race precomputed value on results) instead of gold's lapTimes.milliseconds (individual lap records) -- different real table; also fastestLapTime is TEXT, so ORDER BY would be a string sort, not numeric.

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name, r.year 
FROM races r 
JOIN results rs ON r.race_id = rs.race_id 
JOIN drivers d ON rs.drv_id = d.drv_id 
WHERE d.fname = 'Michael' AND d.lname = 'Schumacher' 
ORDER BY rs.fast_lap_tm ASC 
LIMIT 1;
```

### Q906 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses results (per-race points) instead of gold's driverStandings (season standings snapshot) -- different real table/semantics; also orders by round instead of year, changing which race counts as 'first'.

**Gold SQL:**

```sql
SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name, res.points 
FROM races r 
JOIN results res ON r.race_id = res.race_id 
JOIN drivers d ON res.drv_id = d.drv_id 
WHERE d.fname = 'Lewis' AND d.lname = 'Hamilton' 
ORDER BY r.round ASC 
LIMIT 1;
```

### Q915 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** The innermost subquery orders by dob without ever joining drivers into that scope (only results/races/circuits are referenced there), causing 'no such column: dob' -- an extremely overcomplicated restructuring of what should be a trivial single-table drivers query.

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT country 
FROM drivers 
JOIN circuits ON drivers.drv_id = (SELECT drv_id FROM results WHERE race_id IN (SELECT race_id FROM races WHERE cir_id = circuits.cir_id) ORDER BY dob ASC LIMIT 1)
```

### Q930 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses ORDER BY position ASC LIMIT 1 instead of gold's WHERE rank=0 (an IN-list of ALL qualifying races) -- rank and position are different real columns on results, and the query shape changes from 'all matching races' to a single top-1 result.

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT r.name
FROM races r
JOIN results rs ON r.race_id = rs.race_id
JOIN drivers d ON rs.drv_id = d.drv_id
WHERE d.fname = 'Lewis' AND d.lname = 'Hamilton'
ORDER BY rs.position ASC
LIMIT 1;
```

### Q937 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** name='AustChineseralian Grand Prix' -- a garbled/corrupted value (looks like a merge of 'Australian' and 'Chinese') instead of gold's 'Chinese Grand Prix'; never matches.

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT r.time 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
WHERE ra.year = 2008 AND ra.name = 'AustChineseralian Grand Prix' AND r.position = 2;
```

### Q940 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the time IS NOT NULL filter -- counts all drivers entered in the race instead of just those who finished (had a non-null time).

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT drv_id) 
FROM results 
WHERE race_id IN (
    SELECT race_id 
    FROM races 
    WHERE year = 2008 AND name = 'Chinese Grand Prix'
);
```

### Q944 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses fast_lap_spd (fastest single lap speed) instead of gold's milliseconds (total race finish time) -- a completely different, unrelated real column; also doesn't restrict to finishers (time IS NOT NULL) when picking the 'last place' driver.

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    (first_place.fast_lap_spd - last_place.fast_lap_spd) / last_place.fast_lap_spd * 100 AS percentage_faster
FROM 
    results first_place
JOIN 
    results last_place ON first_place.race_id = last_place.race_id
JOIN 
    races ON first_place.race_id = races.race_id
WHERE 
    races.year = 1988 AND races.name = 'Australian Grand Prix'
    AND first_place.position = 1 AND last_place.position = (SELECT MAX(position) FROM results WHERE race_id = first_place.race_id);
```

### Q950 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses constructorResults instead of gold's constructorStandings -- different real table with different semantics (per-race points earned vs cumulative standings points), despite both having a 'points' column.

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT c.name 
FROM constructors c 
JOIN constructorResults cr ON c.ctor_id = cr.ctor_id 
WHERE cr.race_id = 291 AND cr.points = 0;
```

### Q954 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References r.year directly on results -- results has no year column; reaching year requires the races join, which is entirely omitted (only drivers is joined).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN r.position IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(r.race_id)) AS completion_percentage
FROM 
    results r
JOIN 
    drivers d ON r.drv_id = d.drv_id
WHERE 
    d.nation = 'Japanese' 
    AND r.year BETWEEN 2007 AND 2009;
```

### Q955 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Bare unqualified TIME (and YEAR) references are ambiguous once races and results are joined (both tables have a matching column name) -- 'ambiguous column name: TIME'; also computes AVG(TIME) instead of gold's AVG(milliseconds/1000.0), a wrong column entirely.

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT 
    YEAR, 
    AVG(TIME) AS avg_time_seconds
FROM 
    races
JOIN 
    results ON races.race_id = results.race_id
WHERE 
    YEAR < 1975 AND results.position = 1
GROUP BY 
    YEAR;
```

### Q959 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References T1.year directly on results -- no such column; races (which holds year) is never joined at all; also substitutes driverStandings.position=1 for gold's own time-format filter (LIKE '_:%:__.___'), a wholesale different, wrong logic.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.fast_lap
FROM results AS T1
JOIN driverStandings AS T2 ON T1.drv_id = T2.drv_id AND T1.race_id = T2.race_id
WHERE T1.year = 2009 AND T2.position = 1;
```

### Q962 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** COUNT(DISTINCT R.race_id, R.drv_id) references R.drv_id -- races (aliased R) has no drv_id column; the correct alias is RES (results, already joined) -- an alias mix-up, not a missing join; also uses RES.laps=50 (exact) instead of gold's laps>50.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN D.dob < '1985-01-01' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT R.race_id, R.drv_id) 
FROM races R 
JOIN results RES ON R.race_id = RES.race_id 
JOIN drivers D ON RES.drv_id = D.drv_id 
WHERE R.year BETWEEN 2000 AND 2005 AND RES.laps = 50;
```

### Q963 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** nation='France' (country name) instead of gold's 'French' (nationality/demonym) -- different domain value, never matches.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT d.drv_id) 
FROM drivers d 
JOIN laptimes lt ON d.drv_id = lt.drv_id 
WHERE d.nation = 'France' AND lt.ms < 120000;
```

### Q967 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Applies nation='Netherlands' as a pre-filter before ORDER BY dob DESC LIMIT 3, so it always returns 3 (whichever Dutch drivers are oldest) instead of gold's approach -- take the 3 overall oldest drivers first, then count how many are Dutch; also uses the country name 'Netherlands' instead of nationality/demonym 'Dutch'.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM drivers 
WHERE nation = 'Netherlands' 
ORDER BY dob DESC 
LIMIT 3;
```

### Q972 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters fast_lap=1 (fastestLap = lap NUMBER 1) instead of gold's fastestLapTime IS NOT NULL -- fastestLap and fastestLapTime are different real columns (lap number vs recorded time), a wrong-column substitution, not just a value swap.

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT drv_id, code 
FROM drivers 
WHERE dob LIKE '1971%' 
AND drv_id IN (
    SELECT drv_id 
    FROM results 
    WHERE fast_lap = 1
);
```

### Q977 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses COUNT(*) instead of gold's SUM(IIF(time IS NOT NULL,1,0)) -- drops the requirement that a time be recorded, counting all disqualified entries in the race-ID range regardless; the statusId resolution via subquery correctly matches 'Disqualified'=2 (verified).

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
WHERE race_id BETWEEN 50 AND 100 
AND status_id = (SELECT status_id FROM status WHERE status = 'Disqualified');
```

### Q978 (simple, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- two circuit rows share identical (location, lat, lng) values (verified), so predicted returns 3 rows instead of gold's 2 distinct rows.

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, lat, lng FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Uses MIN(dob) (oldest/earliest-born driver) instead of gold's ORDER BY dob DESC LIMIT 1 (most-recent-born/youngest driver) -- an inverted direction, selecting the opposite driver.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(r.year), r.name, r.date, r.time
FROM races r
JOIN qualifying q ON r.race_id = q.race_id
JOIN drivers d ON q.drv_id = d.drv_id
WHERE d.dob = (SELECT MIN(dob) FROM drivers)
```

### Q990 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses constructorStandings (season standings) instead of gold's results (individual race results) -- different real table; also filters cs.position=1 instead of gold's T1.time LIKE '_:%:__.___' pattern check, an unrelated condition.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT c.ctor_ref, c.url 
FROM constructors c 
JOIN constructorStandings cs ON c.ctor_id = cs.ctor_id 
JOIN races r ON cs.race_id = r.race_id 
WHERE r.name = 'Singapore Grand Prix' AND r.year = 2009 AND cs.position = 1;
```

### Q994 (challenging, aggregate) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Identical underlying result (verified: SUM=218.5, McLaren, British) -- only the SELECT-list column order differs (name, nationality, points vs gold's points, name, nationality); a strict evaluator likely does positional tuple comparison.

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    c.name AS constructor_name, 
    c.nation AS constructor_nation, 
    SUM(cr.points) AS total_points
FROM 
    constructors c
JOIN 
    constructorResults cr ON c.ctor_id = cr.ctor_id
JOIN 
    races r ON cr.race_id = r.race_id
WHERE 
    r.name = 'Monaco Grand Prix' 
    AND r.year BETWEEN 1980 AND 2010
GROUP BY 
    c.ctor_id
ORDER BY 
    total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an invented, unrelated round=3 filter not in gold at all; also substitutes q.position=1 for gold's actual q3 time-string parsing/ORDER BY ASC LIMIT 1 logic -- position=1 may not correspond to the fastest Q3 time in all cases.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.fname, d.lname 
FROM drivers d 
JOIN qualifying q ON d.drv_id = q.drv_id 
JOIN races r ON q.race_id = r.race_id 
JOIN circuits c ON r.cir_id = c.cir_id 
WHERE r.year = 2008 AND r.round = 3 AND c.name = 'Marina Bay Street Circuit' AND q.position = 1;
```

### Q1014 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses laptimes.lap (a lap NUMBER, e.g. 1,2,3...) instead of gold's results.fastestLapTime (a TIME value) -- MIN(lap) trivially returns the smallest lap number, a completely different, wrong table/column choice for 'fastest lap record'.

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(lap) AS min_lap
FROM circuits
JOIN races ON circuits.cir_id = races.cir_id
JOIN laptimes ON races.race_id = laptimes.race_id
WHERE circuits.country = 'Italy';
```

---

## student_club (25 failures)

### Q1317 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an invented m.maj_id IN (SELECT maj_id FROM major WHERE coll='Student_Club') filter that gold doesn't have at all.

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT m.mbr_id) 
FROM member m 
JOIN attendance a ON m.mbr_id = a.mbr_id 
JOIN event e ON a.evt_id = e.evt_id 
WHERE m.maj_id IN (SELECT maj_id FROM major WHERE coll = 'Student_Club') 
AND e.evt_nm = 'Women''s Soccer' 
AND m.shirt_sz = 'Medium';
```

### Q1322 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='meeting' (lowercase) vs gold's 'Meeting' (case-sensitive mismatch); logic is otherwise equivalent (IN-subquery vs derived-table pattern).

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM event 
WHERE evt_id IN (
    SELECT evt_id 
    FROM attendance 
    GROUP BY evt_id 
    HAVING COUNT(mbr_id) > 10
) 
AND type = 'meeting';
```

### Q1334 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an invented m.pos='Student_Club' filter not in gold; also state='IL' instead of the full name 'Illinois'.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT m.fname, m.lname 
FROM member m 
JOIN zip_code z ON m.zip = z.zip_cd 
WHERE z.state = 'IL' AND m.pos = 'Student_Club';
```

### Q1338 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes attendance (joined via expense.mbr_id=attendance.mbr_id then attendance.evt_id=event.evt_id) for budget as the connector between expense and event -- a same-size table swap serving the wrong linking role; also selects an extra exp_id column not in gold's SELECT list.

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT e.exp_id, e.aprvd 
FROM expense e 
JOIN attendance a ON e.mbr_id = a.mbr_id 
JOIN event ev ON a.evt_id = ev.evt_id 
WHERE ev.evt_nm = 'October Meeting' AND ev.evt_dt = '2019-10-08';
```

### Q1340 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** YEAR() is not a valid SQLite function (no such function: YEAR); also adds an invented type='Student_Club' filter in both subqueries.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT SUM(spent) FROM budget WHERE evt_id IN (SELECT evt_id FROM event WHERE YEAR(evt_dt) = 2019 AND type = 'Student_Club')) -
    (SELECT SUM(spent) FROM budget WHERE evt_id IN (SELECT evt_id FROM event WHERE YEAR(evt_dt) = 2020 AND type = 'Student_Club')) AS diff_spent;
```

### Q1344 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Queries event (using its own notes/type/event_date columns) instead of income (source/date_received) -- event happens to also have a notes column, but it's the wrong table entirely.

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE evt_dt = '2019-09-14' AND type = 'fundraising';
```

### Q1357 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** src='dues' (lowercase) vs gold's 'Dues' -- case mismatch.

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT rcvd_dt 
FROM income 
WHERE mbr_id = (SELECT mbr_id FROM member WHERE fname = 'Connor' AND lname = 'Hilton') 
AND src = 'dues';
```

### Q1359 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Introduces a scalar subquery gold doesn't have and replaces gold's ratio-of-two-conditional-sums with a COUNT(*) WHERE b1.spent > (single October-Meeting spent value); also drops the type='Meeting' filter.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM budget b1 
JOIN event e1 ON b1.evt_id = e1.evt_id 
WHERE b1.cat = 'Advertisement' AND e1.evt_nm = 'Yearly Kickoff' 
AND b1.spent > (
    SELECT b2.spent 
    FROM budget b2 
    JOIN event e2 ON b2.evt_id = e2.evt_id 
    WHERE b2.cat = 'Advertisement' AND e2.evt_nm = 'October Meeting'
);
```

### Q1376 (moderate, retrieval) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's HAVING SUM(spent)/SUM(amount) = (SELECT MAX(ratio)...) tie-preserving pattern into a plain ORDER BY (spent/amt) DESC LIMIT 1; no GROUP BY aggregation either.

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT e.evt_nm 
FROM event e 
JOIN budget b ON e.evt_id = b.evt_id 
WHERE e.status = 'closed' 
ORDER BY (b.spent / b.amt) DESC 
LIMIT 1;
```

### Q1380 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** cat='food' (lowercase) vs gold's 'Food'.

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE cat = 'food';
```

### Q1387 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Attempts to join member directly to budget via a nonexistent budget.mbr_id column; the real path is event->budget->expense->member (expense holds link_to_member); missing expense join causes the error; also drops the position='Treasurer' filter entirely.

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT m.fname, m.lname 
FROM member m 
JOIN budget b ON m.mbr_id = b.mbr_id 
JOIN event e ON b.evt_id = e.evt_id 
WHERE e.evt_nm = 'Yearly Kickoff';
```

### Q1389 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Joins expense directly to event via a nonexistent expense.evt_id column, omitting the budget bridge table (expense only has link_to_budget/link_to_member, not link_to_event).

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.evt_nm 
FROM event e 
JOIN expense ex ON e.evt_id = ex.evt_id 
ORDER BY ex.cost ASC, e.evt_nm ASC 
LIMIT 1;
```

### Q1390 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Same bug as Q1389: joins expense directly to event via a nonexistent expense.evt_id column, omitting the budget bridge table.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN e.evt_nm = 'Yearly Kickoff' THEN ex.cost ELSE 0 END) * 100.0 / SUM(ex.cost)) AS percentage
FROM 
    event e
JOIN 
    expense ex ON e.evt_id = ex.evt_id;
```

### Q1392 (simple, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a GROUP BY src + SUM(amt) aggregation that gold doesn't have (gold picks a single row via ORDER BY source DESC LIMIT 1 with no aggregation).

**Gold SQL:**

```sql
SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT src, SUM(amt) AS total_received
FROM income
WHERE strftime('%Y-%m', rcvd_dt) = '2019-09'
GROUP BY src
ORDER BY total_received DESC
LIMIT 1;
```

### Q1394 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an invented member.pos='Student_Club' filter that gold doesn't have (not a valid position value).

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member 
JOIN major ON member.maj_id = major.maj_id 
WHERE major.maj_nm = 'Physics Teaching' AND member.pos = 'Student_Club';
```

### Q1398 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** cat='advertisement' (lowercase) vs gold's 'Advertisement'.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT evt_nm 
FROM event 
WHERE evt_id = (
    SELECT evt_id 
    FROM budget 
    WHERE cat = 'advertisement' 
    ORDER BY spent DESC 
    LIMIT 1
);
```

### Q1401 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Tries to filter expense by evt_id directly (a column that doesn't exist on expense -- no such column: evt_id); the real path needs the budget bridge table (expense.link_to_budget -> budget.link_to_event); also wraps cost in SUM() where gold selects it directly.

**Gold SQL:**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) 
FROM expense 
WHERE exp_desc = 'Posters' 
AND evt_id IN (SELECT evt_id FROM event WHERE evt_nm = 'September Speaker');
```

### Q1403 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses e.status (event.status) instead of budget.event_status for the status filter -- different real columns; also drops remaining<0 and recomputes remaining differently via an added expense join (SUM(cost)-amount) instead of using budget.remaining directly.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.evt_nm
FROM event e
JOIN budget b ON e.evt_id = b.evt_id
JOIN expense ex ON b.bgt_id = ex.bgt_id
WHERE e.status = 'closed'
GROUP BY e.evt_id
ORDER BY SUM(ex.cost) - b.amt DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** e.cat used for category, but category belongs to the already-joined budget (b.cat), not expense -- an alias mix-up on an already-joined table; also aprvd=1 (integer) instead of gold's approved='true' (string) would likely mismatch too.

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
SELECT e.cat, SUM(e.cost) AS total_approved_cost
FROM expense e
JOIN budget b ON e.bgt_id = b.bgt_id
JOIN event ev ON b.evt_id = ev.evt_id
WHERE ev.evt_nm = 'October Meeting' AND e.aprvd = 1
GROUP BY e.cat;
```

### Q1422 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Selects b.cat (budget.category) via an unneeded join to budget, instead of gold's e.type (event.type) -- genuinely wrong column, not just aliasing.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.cat 
FROM budget b 
JOIN event e ON b.evt_id = e.evt_id 
WHERE e.loc = 'MU 215';
```

### Q1427 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='guest speaker' (lowercase) vs gold's 'Guest Speaker'; also drops DISTINCT.

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT b.cat 
FROM budget b 
JOIN event e ON b.evt_id = e.evt_id 
WHERE e.loc = 'MU 215' AND e.type = 'guest speaker' AND b.spent = 0;
```

### Q1432 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** CASE condition tests i.src='Student_Club' instead of gold's amount=50 (src vs amount are different real columns); also drops the position='Member' filter and uses SUM(amt) instead of COUNT(income_id) as denominator.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN i.src = 'Student_Club' THEN i.amt ELSE 0 END) AS REAL) * 100 / SUM(i.amt) 
FROM income i 
JOIN member m ON i.mbr_id = m.mbr_id 
WHERE m.shirt_sz = 'Medium';
```

### Q1435 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='game' and status='closed' (lowercase) vs gold's 'Game'/'Closed'; also drops DISTINCT and the date(SUBSTR(...)) wrapper (likely harmless if event_date is already a clean date string).

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT evt_nm 
FROM event 
WHERE type = 'game' 
AND status = 'closed' 
AND evt_dt BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1457 (challenging, aggregate) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT; otherwise structurally/semantically equivalent (the extra budget/member joins in gold's subquery don't filter anything, so AVG(cost) FROM expense is equivalent).

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT m.fname, m.lname, m.phone
FROM member m
JOIN expense e ON m.mbr_id = e.mbr_id
WHERE e.cost > (SELECT AVG(cost) FROM expense);
```

### Q1460 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Splits the single compound description 'Water, Veggie tray, supplies' into three separate lowercase IN-list values ('water','veggie tray','supplies') instead of matching the full string exactly.

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.fname, m.lname, e.cost 
FROM member m 
JOIN expense e ON m.mbr_id = e.mbr_id 
WHERE e.exp_desc IN ('water', 'veggie tray', 'supplies');
```

---

## superhero (26 failures)

### Q724 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** color='blue'/'blond' (lowercase) vs gold's Title Case 'Blue'/'Blond' (verified domain is capitalized) -- case-sensitive mismatch.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT hero_nm 
FROM superhero 
WHERE eye_clr_id = (SELECT id FROM colour WHERE color = 'blue') 
AND hair_clr_id = (SELECT id FROM colour WHERE color = 'blond');
```

### Q726 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the height_cm IS NOT NULL AND height_cm != 0 filter entirely -- heroes with 0 or NULL height would incorrectly appear in the ordered results.

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT s.hero_nm, s.ht_cm 
FROM superhero s 
JOIN publisher p ON s.pub_id = p.id 
WHERE p.pub_nm = 'Marvel Comics' 
ORDER BY s.ht_cm DESC;
```

### Q728 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Drops the RANK() OVER (ORDER BY COUNT(*) DESC) window function column entirely -- gold explicitly returns a PopularityRank alongside the count; predicted has no equivalent.

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.color, COUNT(*) as count 
FROM superhero s 
JOIN colour c ON s.eye_clr_id = c.id 
JOIN publisher p ON s.pub_id = p.id 
WHERE p.pub_nm = 'Marvel Comics' 
GROUP BY c.color 
ORDER BY count DESC;
```

### Q733 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** color='gold' (lowercase) vs gold's 'Gold' (verified domain is capitalized) -- case-sensitive mismatch.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.eye_clr_id = colour.id 
JOIN publisher ON superhero.pub_id = publisher.id 
WHERE colour.color = 'gold' AND publisher.pub_nm = 'Marvel Comics';
```

### Q736 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attr_nm='IQ' instead of gold's 'Intelligence' -- 'IQ' isn't a valid attribute_name value in this domain; also collapses gold's MIN-equality tie-preserving pattern into ORDER BY ASC LIMIT 1.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT hero_nm 
FROM superhero 
WHERE id = (SELECT hero_id FROM hero_attribute WHERE attr_id = (SELECT id FROM attribute WHERE attr_nm = 'IQ') ORDER BY attr_val ASC LIMIT 1);
```

### Q743 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** align='Self-Centric' -- not a valid value in the domain (verified: Good/Bad/Neutral/N/A); gold wants 'Bad'.

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN T1.align = 'Self-Centric' THEN 1 END) * 100.0 / COUNT(*)) AS percentage_self_centric,
    COUNT(CASE WHEN T1.align = 'Self-Centric' AND T2.pub_nm = 'Marvel Comics' THEN 1 END) AS marvel_self_centric_count
FROM 
    alignment AS T1
JOIN 
    superhero AS T3 ON T1.id = T3.align_id
JOIN 
    publisher AS T2 ON T3.pub_id = T2.id;
```

### Q744 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** pub_nm IN ('DC','Marvel') -- neither value exists (verified real values include 'Comics' suffix: 'DC Comics'/'Marvel Comics') -- matches zero rows; also restructures gold's single winner+difference computation into a per-publisher count list.

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
    p.pub_nm, 
    COUNT(s.id) AS num_heroes
FROM 
    publisher p
JOIN 
    superhero s ON p.id = s.pub_id
WHERE 
    p.pub_nm IN ('DC', 'Marvel')
GROUP BY 
    p.pub_nm
ORDER BY 
    num_heroes DESC;
```

### Q750 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the weight_kg > 0 filter -- heroes with weight_kg=0 (likely a placeholder for missing data) would incorrectly be included in the average, skewing it downward.

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(wt_kg) 
FROM superhero 
JOIN gender ON superhero.gender_id = gender.id 
WHERE gender.gender = 'Female';
```

### Q751 (moderate, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT that gold's query doesn't have -- gold intentionally returns one row per (male hero, power) pair, while predicted collapses to unique power names only.

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.pwr_nm 
FROM superhero h 
JOIN hero_power hp ON h.id = hp.hero_id 
JOIN superpower p ON hp.pwr_id = p.id 
JOIN gender g ON h.gender_id = g.id 
WHERE g.gender = 'Male';
```

### Q753 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Assumes 'No Colour' means eye_clr_id IS NULL, but 'No Colour' is an actual row in the colour table (id=1, verified) that heroes explicitly reference via a non-null FK -- should filter on colour.colour='No Colour' instead.

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT hero_nm 
FROM superhero 
WHERE ht_cm BETWEEN 170 AND 190 
AND eye_clr_id IS NULL;
```

### Q758 (moderate, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- multiple 185cm Human heroes could share the same hair colour, producing duplicate rows.

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT c.color 
FROM superhero s 
JOIN colour c ON s.hair_clr_id = c.id 
WHERE s.race_id = (SELECT id FROM race WHERE race = 'Human') AND s.ht_cm = 185;
```

### Q766 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's max_strength CTE (which finds ALL heroes tied at the maximum Strength value) into a plain ORDER BY attr_val DESC LIMIT 1, which would drop any heroes tied for the max and only return one.

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT s.full_nm 
FROM superhero s 
JOIN hero_attribute ha ON s.id = ha.hero_id 
JOIN attribute a ON ha.attr_id = a.id 
WHERE a.attr_nm = 'Strength' 
ORDER BY ha.attr_val DESC 
LIMIT 1;
```

### Q769 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Uses hero_power/superpower (whether a hero HAS the named power 'Durability') instead of gold's hero_attribute/attribute (a numeric Durability STAT value) -- a completely different real table/semantic concept; also replaces ORDER BY attribute_value DESC with a nonsensical GROUP BY/COUNT(*) ranking.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.hero_nm 
FROM superhero s 
JOIN publisher p ON s.pub_id = p.id 
JOIN hero_power hp ON s.id = hp.hero_id 
JOIN superpower sp ON hp.pwr_id = sp.id 
WHERE p.pub_nm = 'Dark Horse Comics' AND sp.pwr_nm = 'Durability' 
GROUP BY s.id 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q772 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Resolves eye/hair/skin colour IDs to their colour name strings via extra joins, instead of returning the raw eye_colour_id/hair_colour_id/skin_colour_id integer values gold explicitly selects.

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c1.color AS eye_color, 
    c2.color AS hair_color, 
    c3.color AS skin_color 
FROM 
    superhero s 
JOIN 
    gender g ON s.gender_id = g.id 
JOIN 
    colour c1 ON s.eye_clr_id = c1.id 
JOIN 
    colour c2 ON s.hair_clr_id = c2.id 
JOIN 
    colour c3 ON s.skin_clr_id = c3.id 
JOIN 
    publisher p ON s.pub_id = p.id 
WHERE 
    g.gender = 'Female' 
    AND p.pub_nm = 'Dark Horse Comics';
```

### Q775 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses eye_clr_id (eye colour) instead of gold's skin_colour_id (skin colour) -- a different real FK column on superhero, despite the shared reference to the colour table.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T1.eye_clr_id = (SELECT id FROM colour WHERE color = 'Blue') THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    superhero AS T1 
JOIN 
    gender AS T2 ON T1.gender_id = T2.id 
WHERE 
    T2.gender = 'Female';
```

### Q782 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** color='black' (lowercase) instead of gold's 'Black' -- case-sensitive mismatch causes zero results; the underlying logic (both eye_colour_id and hair_colour_id equal to Black's id) is otherwise equivalent to gold's same-alias join trick.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT hero_nm 
FROM superhero 
WHERE eye_clr_id = (SELECT id FROM colour WHERE color = 'black') 
AND hair_clr_id = (SELECT id FROM colour WHERE color = 'black');
```

### Q786 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's WHERE attribute_value=(SELECT MAX(...)) tie-preserving equality (COUNT(DISTINCT hero_id) counts ALL heroes tied for max Strength) into an ORDER BY DESC LIMIT 1 subquery, which returns only one hero_id even if multiple heroes tie for the max.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT ha.`hero_id`)
FROM `hero_attribute` AS ha
JOIN `attribute` AS a ON ha.`attribute_id` = a.`id`
WHERE a.`attribute_name` = 'Strength'
  AND ha.`attribute_value` = (
        SELECT MAX(ha2.`attribute_value`)
        FROM `hero_attribute` ha2
        JOIN `attribute` a2 ON ha2.`attribute_id` = a2.`id`
        WHERE a2.`attribute_name` = 'Strength'
      );
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
WHERE id IN (
    SELECT hero_id 
    FROM hero_attribute 
    WHERE attr_id = (
        SELECT id 
        FROM attribute 
        WHERE attr_nm = 'Strength'
    ) 
    ORDER BY attr_val DESC 
    LIMIT 1
);
```

### Q788 (challenging, aggregate) -- **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** Uses INNER JOIN publisher instead of gold's LEFT JOIN, dropping heroes with no publisher_id from the denominator; also moves the publisher_name='Marvel Comics' condition from inside a CASE into an outer WHERE that restricts the ENTIRE query -- computes '% of Marvel heroes that are Female' instead of gold's '% of Female heroes that are Marvel-published'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN g.gender = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero s 
JOIN gender g ON s.gender_id = g.id 
JOIN publisher p ON s.pub_id = p.id 
WHERE p.pub_nm = 'Marvel Comics';
```

### Q790 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters on hero_nm (superhero_name, e.g. stage name) instead of gold's full_name (civilian/real name) -- 'Emil Blonsky' and 'Charles Chandler' are full names (verified), not superhero names; likely returns NULL for both subqueries.

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT (SELECT wt_kg FROM superhero WHERE hero_nm = 'Emil Blonsky') - 
       (SELECT wt_kg FROM superhero WHERE hero_nm = 'Charles Chandler') AS weight_difference;
```

### Q791 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the height_cm > 0 filter entirely -- heroes with height_cm=0 (placeholder for missing data) would skew the average downward.

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(ht_cm) FROM superhero
```

### Q794 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References attr_val directly on superhero -- attribute_value lives on hero_attribute, which is never joined in the outer query (only referenced inside the MAX subquery); no such column error results.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT hero_nm FROM superhero WHERE attr_val = (SELECT MAX(attr_val) FROM hero_attribute WHERE attr_id = (SELECT id FROM attribute WHERE attr_nm = 'Speed'))
```

### Q797 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** color='blue'/'brown' (lowercase) vs gold's Title Case 'Blue'/'Brown' -- case-sensitive mismatch.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT s.hero_nm 
FROM superhero s 
JOIN colour c1 ON s.eye_clr_id = c1.id 
JOIN colour c2 ON s.hair_clr_id = c2.id 
WHERE c1.color = 'blue' AND c2.color = 'brown';
```

### Q798 (moderate, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Adds a DISTINCT that gold's query doesn't have -- all three named heroes share the same publisher (verified: publisher_id=4), so gold returns that publisher name three times while predicted collapses to once.

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.pub_nm 
FROM superhero h 
JOIN publisher p ON h.pub_id = p.id 
WHERE h.hero_nm IN ('Hawkman', 'Karate Kid', 'Speedy');
```

### Q800 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** color='blue' (lowercase) vs gold's 'Blue' -- case-sensitive mismatch.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.color = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero AS T1 
JOIN colour AS T2 ON T1.eye_clr_id = T2.id;
```

### Q819 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Assumes eye_clr_id IS NULL represents 'No Colour' instead of matching the actual colour.id=1 sentinel row for 'No Colour' (same misconception as Q753); also drops the 'weight_kg=0' half of gold's OR condition, checking only wt_kg IS NULL.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM superhero WHERE eye_clr_id = (SELECT id FROM colour WHERE color = 'Blue') AND wt_kg IS NULL) -
    (SELECT COUNT(*) FROM superhero WHERE eye_clr_id IS NULL AND wt_kg IS NULL) AS diff;
```

### Q829 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** pub_nm='DC' -- doesn't exist; the actual value is 'DC Comics' (with 'Comics' suffix), so that COUNT is always 0; also drops gold's CASE-based 'publisher_with_more_superheroes' winner label, returning only a raw difference number.

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
    (SELECT COUNT(*) FROM superhero WHERE pub_id = (SELECT id FROM publisher WHERE pub_nm = 'DC')) -
    (SELECT COUNT(*) FROM superhero WHERE pub_id = (SELECT id FROM publisher WHERE pub_nm = 'Marvel Comics')) AS difference;
```

---

## thrombosis_prediction (48 failures)

### Q1149 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Uses admission='Inpatient'/'Outpatient' and sex='Male' -- invented values; real domain is Admission='+'/'-' and SEX='M'/'F', so the WHERE never matches; also computes a % deviation formula instead of gold's simple in/out ratio.

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN SUM(CASE WHEN admission = 'Inpatient' THEN 1 ELSE 0 END) > SUM(CASE WHEN admission = 'Outpatient' THEN 1 ELSE 0 END) THEN 'Inpatient'
        ELSE 'Outpatient'
    END AS majority_type,
    ABS(SUM(CASE WHEN admission = 'Inpatient' THEN 1 ELSE 0 END) - SUM(CASE WHEN admission = 'Outpatient' THEN 1 ELSE 0 END)) * 100.0 / (SUM(CASE WHEN admission = 'Inpatient' THEN 1 ELSE 0 END) + SUM(CASE WHEN admission = 'Outpatient' THEN 1 ELSE 0 END)) AS deviation_percentage
FROM 
    Patient
WHERE 
    sex = 'Male';
```

### Q1150 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Moves the SEX='F' filter from the outer WHERE into the CASE condition (the value itself is correct), so the denominator COUNT(*) is now over ALL patients instead of just female patients.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'F' AND strftime('%Y', bday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient;
```

### Q1152 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission='Inpatient'/'Outpatient' instead of the stored codes '+'/'-'.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN admission = 'Inpatient' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN admission = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio
FROM 
    Patient
WHERE 
    diag = 'SLE';
```

### Q1153 (simple, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops the Diagnosis column from the SELECT list entirely (only returns Date); also adds a DISTINCT that gold doesn't have.

**Gold SQL:**

```sql
SELECT T1.Diagnosis, T2.Date FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 30609
```

**Predicted SQL:**

```sql
SELECT DISTINCT L.Date 
FROM Laboratory L 
JOIN Patient P ON L.ID = P.ID 
WHERE P.ID = '30609';
```

### Q1155 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** ldh>160 instead of gold's threshold >500 -- a wrong/invented value.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.bday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.ldh > 160;
```

### Q1156 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters E.thrombosis='positive' instead of gold's E.RVVT='+' -- a different real column (Thrombosis is distinct from RVVT); also 'positive' isn't even a valid Thrombosis domain value (0/1/2).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.bday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.bday)) AS age
FROM Patient P
JOIN Examination E ON P.ID = E.ID
WHERE E.thrombosis = 'positive';
```

### Q1157 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis='severe' (invented string) instead of gold's numeric degree value 2 -- Thrombosis is stored as an integer code, not descriptive text.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.diag 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.thrombosis = 'severe';
```

### Q1162 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission='门诊' (Chinese for 'outpatient', an invented value) instead of gold's coded '-'; column/date parts otherwise correct.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE sex = 'F' 
AND strftime('%Y', first_rec_dt) = '1997' 
AND admission = '门诊';
```

### Q1164 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis='most serious' (invented string) instead of gold's numeric value 1.

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
SELECT COUNT(*) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE strftime('%Y', e.exam_dt) = '1997' AND p.sex = 'F' AND e.thrombosis = 'most serious';
```

### Q1166 (simple, retrieval) -- **Nesting problem** (Wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's UNION branch (which supplies a NULL-symptom fallback row when the oldest patient with an exam has no recorded symptoms); also computes MAX(bday) over all patients instead of only those with an Examination row, and replaces the NOT NULL symptom filter with an arbitrary LIMIT 1.

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT E.symptoms, P.diag 
FROM Examination E 
JOIN Patient P ON E.ID = P.ID 
WHERE P.bday = (SELECT MAX(bday) FROM Patient) 
LIMIT 1;
```

### Q1168 (challenging, retrieval) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** Wraps P.bday in MAX() (mixed with non-aggregated columns, no GROUP BY) instead of gold's plain ORDER BY .. LIMIT 1 row selection; also selects the wrong columns (first_rec_dt instead of a computed age) and drops the Birthday IS NOT NULL filter plus the secondary date DESC tie-break.

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MAX(P.bday) AS birth_date, 
    P.first_rec_dt AS initial_admission_date, 
    L.Date AS last_laboratory_date
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    P.diag = 'SJS'
ORDER BY 
    P.bday ASC
LIMIT 1;
```

### Q1169 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Restructures gold's per-sex threshold conditional counts (UA<=8.0 for M, UA<=6.5 for F) into a single outer filter (ua>7.0) applied identically to both sexes, then just ratios the M/F counts among those rows -- a fundamentally different, non-equivalent computation.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN P.sex = 'M' THEN 1 ELSE 0 END) / SUM(CASE WHEN P.sex = 'F' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    L.ua > 7.0;  -- Assuming 7.0 mg/dL as the threshold for abnormal uric acid count
```

### Q1171 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Age-difference threshold '< 0' instead of gold's '< 18' -- wrong/invented numeric threshold.

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.exam_dt BETWEEN '1990-01-01' AND '1993-12-31' 
AND strftime('%Y', E.exam_dt) - strftime('%Y', P.bday) < 0;
```

### Q1175 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unneeded INNER JOIN to Examination that could filter out the top-HGB patient if they lack an exam record; also adds an extra sex column to the SELECT list.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.sex, strftime('%Y', 'now') - strftime('%Y', P.bday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.bday)) AS age, P.diag
FROM Patient P
JOIN Examination E ON P.ID = E.ID
JOIN Laboratory L ON P.ID = L.ID
ORDER BY L.hgb DESC
LIMIT 1;
```

### Q1179 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Queries Laboratory (igg/iga/igm -- Immunoglobulin tests) instead of Examination (acl_igm -- Anticardiolipin antibody test) -- a completely different real table/column despite the similar-sounding name; also selects 3 columns instead of gold's 1.

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT L.igg, L.iga, L.igm 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.diag = 'SLE' AND P.first_rec_dt = '1994-02-19' AND L.Date = '1993-11-12';
```

### Q1185 (challenging, aggregate) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** Uses (MAX(t_cho)-MIN(t_cho))/COUNT(DISTINCT Date) as an ad hoc decrease-rate instead of gold's month-scoped SUM(Nov T-CHO)-SUM(Dec T-CHO))/SUM(Nov T-CHO) -- a fundamentally different aggregate formula.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(t.t_cho) - MIN(t.t_cho)) / COUNT(DISTINCT t.Date) AS decrease_rate
FROM 
    Patient p
JOIN 
    Laboratory t ON p.ID = t.ID
WHERE 
    p.bday = '1959-02-18' 
    AND t.Date BETWEEN '1981-11-01' AND '1981-12-31';
```

### Q1187 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Applies the date-range filter to E.exam_dt (Examination Date) instead of gold's L.Date (Laboratory Date) -- a different real column/table entirely; also adds an unneeded Examination join.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
JOIN Laboratory L ON P.ID = L.ID 
WHERE E.exam_dt BETWEEN '1987-07-06' AND '1996-01-31' 
AND L.gpt > 30 
AND L.alb < 4;
```

### Q1189 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Inner subquery's AVG(acl_igm)*1.2 drops the Thrombosis=2 AND ANA Pattern='S' filters that the outer query has and that gold's subquery replicates -- computes the average over ALL Examination rows instead of the matching subset.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID)
FROM Patient P
JOIN Examination E ON P.ID = E.ID
WHERE E.thrombosis = 2
AND E.ana_pattern = 'S'
AND E.acl_igm > (SELECT AVG(acl_igm) * 1.2 FROM Examination);
```

### Q1192 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission='门诊' (invented Chinese value) instead of gold's '-'; also t_bil BETWEEN 5 AND 20 instead of gold's simple <2.0 -- wrong/invented threshold range.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE P.admission = '门诊'
AND L.Date BETWEEN '1991-10-01' AND '1991-10-31'
AND L.t_bil BETWEEN 5 AND 20;
```

### Q1198 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' instead of the stored single-letter code 'F'.

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE sex = 'female' AND diag = 'APS';
```

### Q1205 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Drops the sex-dependent threshold branching entirely (and the Patient join needed to reach SEX), instead applying one fixed range (2.4-7.2) regardless of sex.

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN ua BETWEEN 2.4 AND 7.2 THEN 'true' ELSE 'false' END AS is_normal FROM Laboratory WHERE ID = 57266
```

### Q1208 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M', and gpt>40 instead of gold's threshold >=60.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' AND L.gpt > 40;
```

### Q1209 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** gpt>40 instead of gold's threshold >60.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.diag 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.gpt > 40 
ORDER BY P.bday ASC;
```

### Q1220 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** un=20 instead of gold's value 29.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.bday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.un = 20;
```

### Q1225 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's single T-BIL>=2.0 threshold with a two-sided 'abnormal range' condition (t_bil<0.3 OR t_bil>1.2) -- a restructured, non-equivalent predicate; also uses COUNT(*) instead of GROUP_CONCAT(DISTINCT ID) as the aggregate.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.sex, COUNT(*) AS patient_count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.t_bil < 0.3 OR L.t_bil > 1.2
GROUP BY P.sex;
```

### Q1227 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Uses MySQL-style YEAR(CURRENT_DATE) -- not valid SQLite syntax (no such function: YEAR); also the threshold logic differs (t_cho > overall AVG(t_cho) instead of gold's fixed >=250 cutoff).

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(YEAR(CURRENT_DATE) - YEAR(bday)) AS avg_age
FROM Patient
WHERE sex = 'M' AND ID IN (
    SELECT ID
    FROM Laboratory
    WHERE t_cho > (SELECT AVG(t_cho) FROM Laboratory)
);
```

### Q1229 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** tg>150 instead of gold's threshold >=200.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID)
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.tg > 150 AND strftime('%Y', 'now') - strftime('%Y', P.bday) > 50;
```

### Q1231 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** cpk>100 instead of gold's threshold >=250.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'M' 
AND strftime('%Y', P.bday) BETWEEN '1936' AND '1956' 
AND L.cpk > 100;
```

### Q1232 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Restructures GLU>=180 into a two-sided 'abnormal range' OR condition (GLU<70 OR GLU>110) with a t_cho range (150-200) instead of gold's <250 cutoff; also, since AND binds tighter than OR, the query actually parses as GLU<70 OR (GLU>110 AND t_cho BETWEEN 150 AND 200) -- an unintended precedence bug.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, strftime('%Y', 'now') - strftime('%Y', P.bday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.bday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.GLU < 70 OR L.GLU > 110
AND L.t_cho BETWEEN 150 AND 200;
```

### Q1235 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's fixed clinical threshold RBC<3.5 with a dynamically computed rbc < AVG(rbc) -- a different, data-dependent comparison; also drops DISTINCT.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.bday) AS age, P.diag
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.rbc < (SELECT AVG(rbc) FROM Laboratory)
```

### Q1238 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hgb BETWEEN 13.5 AND 17.5 instead of gold's BETWEEN 10 AND 17.

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.diag = 'SLE' AND L.hgb BETWEEN 13.5 AND 17.5 
ORDER BY P.bday ASC 
LIMIT 1;
```

### Q1239 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses a two-sided range hct BETWEEN 45 AND 55 instead of gold's single-sided HCT>=52 threshold -- a restructured comparison, not just a value swap; the overall subquery-vs-join restructuring is otherwise roughly equivalent.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.bday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.bday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.hct > 45 AND L.hct < 55
GROUP BY P.ID
HAVING COUNT(L.ID) >= 2;
```

### Q1241 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** plt<150/plt>450 instead of gold's <100/>400 thresholds; also uses SUM(CASE...) counting rows instead of gold's two COUNT(DISTINCT ID) scalar subqueries, so a patient with multiple matching Laboratory rows would be over-counted.

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN plt < 150 THEN 1 ELSE 0 END) AS lower_than_normal,
    SUM(CASE WHEN plt > 450 THEN 1 ELSE 0 END) AS higher_than_normal
FROM 
    Laboratory;
```

### Q1242 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unneeded INNER JOIN to Examination (only 763/1238 patients have an exam record, verified) that could exclude qualifying patients who lack one; also plt BETWEEN 150 AND 450 instead of gold's 100-400.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
JOIN Examination E ON P.ID = E.ID
WHERE strftime('%Y', L.Date) = '1984'
AND strftime('%Y', 'now') - strftime('%Y', P.bday) < 50
AND L.plt BETWEEN 150 AND 450;
```

### Q1243 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** pt>13.5 instead of gold's PT>=14 -- wrong/looser threshold; also uses SUM(rows)/COUNT(*) instead of COUNT(DISTINCT patient-level CASE), so patients with multiple matching Laboratory rows would be over-counted.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN P.sex = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE strftime('%Y', 'now') - strftime('%Y', P.bday) > 55 AND L.pt > 13.5;
```

### Q1247 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops gold's FG<=150 OR FG>=450 two-sided condition, replacing it with a single fg<1.5 (different scale entirely); also sex='male' (wrong, real 'M') and wbc range 4.0-11.0 instead of gold's 3.5-9.0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' 
AND L.wbc BETWEEN 4.0 AND 11.0 
AND L.fg < 1.5;
```

### Q1251 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** igg>150 instead of gold's threshold >=2000.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.igg > 150;
```

### Q1252 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** igg='normal' (invented string) instead of gold's numeric range BETWEEN 900 AND 2000 -- IGG is a numeric lab value, not a categorical string.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
JOIN Examination E ON P.ID = E.ID 
WHERE L.igg = 'normal' AND E.symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** iga='normal' (invented string) instead of gold's numeric range BETWEEN 80 AND 500.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.iga = 'normal' AND P.admit_dt > '1990-01-01';
```

### Q1255 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's abnormal-range condition (IGM<=40 OR IGM>=400) with igm>0 -- effectively no filter, since virtually all values are positive; also counts raw joined rows instead of gold's DISTINCT (ID,Diagnosis) dedup first, so patients with multiple Laboratory rows are over-counted for their diagnosis.

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.diag, COUNT(*) as count 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.igm > 0 
GROUP BY P.diag 
ORDER BY count DESC 
LIMIT 1;
```

### Q1256 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Logic is inverted: predicted counts patients with NO crp>0 reading (NOT IN), while gold wants patients WITH CRP='+' (a categorical positive marker, not a numeric >0 comparison) AND Description IS NULL -- the Description IS NULL condition is dropped entirely too.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE ID NOT IN (SELECT ID FROM Laboratory WHERE crp > 0);
```

### Q1257 (challenging, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** References P.age as if it were a real column; no such column exists anywhere in the schema -- age must be computed via STRFTIME(...) - STRFTIME(...) as gold does; also cre>1.2 instead of gold's >=1.5.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.cre > 1.2 AND P.age < 70;
```

### Q1265 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** rnp='normal' and admission='yes' -- invented values; real domain is rnp IN ('negative','0') and admission='+'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.rnp = 'normal' AND P.admission = 'yes';
```

### Q1267 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References e.sm (SM lives on Laboratory, not Examination) -- the query never joins Laboratory at all; also thrombosis='no' is an invented value (Thrombosis is a numeric degree code, not yes/no text).

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
SELECT COUNT(*) 
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE e.sm = 'normal' AND e.thrombosis = 'no';
```

### Q1270 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** References p.symptoms directly on Patient -- Symptoms lives on Examination, which is never joined; also sc170='normal' and sex='female' are wrong/invented values.

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
SELECT COUNT(*) 
FROM Patient p 
JOIN Laboratory l ON p.ID = l.ID 
WHERE l.sc170 = 'normal' AND p.sex = 'female' AND p.symptoms IS NULL;
```

### Q1275 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** centromea='normal' and ssb='normal' and sex='male' -- invented values; real domain is 'negative'/'0' and 'M'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.centromea = 'normal' AND L.ssb = 'normal' AND P.sex = 'male';
```

### Q1281 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters on gpt (GPT, alanine aminotransferase) instead of gold's got (GOT, aspartate aminotransferase) -- a different real lab test; also threshold 40 instead of 60, and MIN(bday) (oldest patient) instead of ORDER BY Birthday DESC LIMIT 1 (youngest patient) -- an inverted result too.

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(bday) 
FROM Patient 
WHERE ID IN (
    SELECT ID 
    FROM Laboratory 
    WHERE gpt > 40
)
```

### Q1302 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Omits the Examination join entirely (needed for KCT='+' OR RVVT='+' OR LAC='+'), substituting an unrelated Laboratory column (pt>13.5, Prothrombin Time) instead; also cpk range 10-200 instead of gold's <250.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
JOIN Laboratory ON Patient.ID = Laboratory.ID 
WHERE Laboratory.cpk BETWEEN 10 AND 200 AND Laboratory.pt > 13.5;
```

---

## toxicology (38 failures)

### Q197 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*) FILTER(...)) nested aggregate misuse; also bnd_type='single' is an invented value (real domain is '-'/'='/'#', verified).

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*) FILTER (WHERE elem = 'O')) AS avg_oxygen_count
FROM molecule m
JOIN atom a ON m.mol_id = a.mol_id
JOIN bond b ON m.mol_id = b.mol_id
JOIN connected c ON a.atm_id = c.atm_id AND b.bnd_id = c.bnd_id
WHERE b.bnd_type = 'single'
GROUP BY m.mol_id;
```

### Q198 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) nested aggregate misuse; also lbl='carcinogenic' and bnd_type='single' are invented values (real domains are label='+'/'-' and bond_type='-'/'='/'#', verified).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) 
FROM bond 
JOIN molecule ON bond.mol_id = molecule.mol_id 
WHERE molecule.lbl = 'carcinogenic' AND bond.bnd_type = 'single' 
GROUP BY bond.mol_id;
```

### Q200 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='triple' and lbl LIKE '%carcinogenic%' are invented values -- real domains are bond_type='#' and label='+'; never matches.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.mol_id, m.lbl
FROM molecule m
JOIN bond b ON m.mol_id = b.mol_id
WHERE b.bnd_type = 'triple' AND m.lbl LIKE '%carcinogenic%';
```

### Q201 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='DOUBLE' (invented, real '=') and elem='C' (uppercase, real domain lowercase 'c', verified) -- never matches.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.elem = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atm_id = T2.atm_id 
JOIN bond AS T3 ON T2.bnd_id = T3.bnd_id 
WHERE T3.bnd_type = 'DOUBLE';
```

### Q206 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters m.lbl='TR004_8_9' -- label's domain is only '+'/'-'; the actual condition should be on connected.bond_id='TR004_8_9' (a bond identifier, not a molecule label) -- a wrong column substitution, not just a wrong value.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.elem 
FROM atom a 
JOIN molecule m ON a.mol_id = m.mol_id 
JOIN bond b ON a.mol_id = b.mol_id 
WHERE m.lbl = 'TR004_8_9';
```

### Q207 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='double' (invented, real '=') -- never matches.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.elem 
FROM atom a 
JOIN connected c ON a.atm_id = c.atm_id 
JOIN bond b ON c.bnd_id = b.bnd_id 
WHERE b.bnd_type = 'double';
```

### Q208 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** elem='H' (uppercase) instead of gold's lowercase 'h' -- atom.element values are stored lowercase (verified); never matches.

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT m.lbl 
FROM molecule m 
JOIN atom a ON m.mol_id = a.mol_id 
WHERE a.elem = 'H' 
GROUP BY m.lbl 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q212 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lbl='carcinogenic' is an invented value that never matches any row, so the NOT IN subquery is empty and the WHERE clause becomes a no-op (matches ALL molecules instead of gold's non-carcinogenic-only filter, label='-'); also collapses gold's tie-preserving HAVING COUNT(*)=(MIN cnt) pattern into ORDER BY ASC LIMIT 1.

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
SELECT elem 
FROM atom 
WHERE mol_id NOT IN (SELECT mol_id FROM molecule WHERE lbl = 'carcinogenic') 
GROUP BY elem 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### Q213 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters a1.elem='TR004_8' / a2.elem='TR004_20' -- these look like atom_id values, not element symbols (element's domain is short lowercase symbols like 'c','h','o', verified); should filter on atom_id directly instead.

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT b.bnd_type 
FROM bond b 
JOIN connected c ON b.bnd_id = c.bnd_id 
JOIN atom a1 ON c.atm_id = a1.atm_id 
JOIN atom a2 ON c.atm_id2 = a2.atm_id 
JOIN molecule m ON a1.mol_id = m.mol_id 
WHERE a1.elem = 'TR004_8' AND a2.elem = 'TR004_20';
```

### Q215 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** elem='I'/'S' (uppercase) instead of lowercase 'i'/'s'; bnd_type='single' instead of '-' -- all invented/wrong-case values, never matches; also both output columns use the identical COUNT(*) expression instead of separate per-element DISTINCT counts.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(*) AS iodine_count, 
    COUNT(*) AS sulfur_count 
FROM 
    atom 
JOIN 
    molecule ON atom.mol_id = molecule.mol_id 
JOIN 
    bond ON molecule.mol_id = bond.mol_id 
JOIN 
    connected ON atom.atm_id = connected.atm_id 
WHERE 
    (atom.elem = 'I' OR atom.elem = 'S') 
    AND bond.bnd_type = 'single';
```

### Q218 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lbl='carcinogenic' is an invented value -- real domain is label='+'/'-'.

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN elem != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom 
JOIN molecule ON atom.mol_id = molecule.mol_id 
WHERE molecule.lbl = 'carcinogenic';
```

### Q219 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Inverts gold's structure -- gold filters to triple-bonded molecules (bond_type='#') and computes what % are labeled '+' (carcinogenic); predicted instead filters to lbl='carcinogenic' (an invented value that never matches) and computes what % of THEIR bonds are triple -- numerator/denominator roles are swapped.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN b.bnd_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM bond b 
JOIN molecule m ON b.mol_id = m.mol_id 
WHERE m.lbl = 'carcinogenic';
```

### Q220 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters m.lbl='TR000' -- label's domain is only '+'/'-'; 'TR000' is a molecule_id value, so this should filter on molecule_id, not label -- a wrong column substitution.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT elem 
FROM atom 
JOIN molecule ON atom.mol_id = molecule.mol_id 
WHERE molecule.lbl = 'TR000' 
ORDER BY elem ASC 
LIMIT 3;
```

### Q226 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters m.lbl='TR008' instead of the correct molecule_id='TR008' -- label's domain is only '+'/'-'; also bnd_type='DOUBLE' is an invented value (real domain: '-'/'='/'#').

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN b.bnd_type = 'DOUBLE' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage_double_bonds
FROM bond b
JOIN molecule m ON b.mol_id = m.mol_id
WHERE m.lbl = 'TR008';
```

### Q227 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lbl='carcinogenic' is an invented value -- real domain is label='+'/'-'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN lbl = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage
FROM molecule;
```

### Q228 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters T2.lbl='TR206' instead of the correct molecule_id='TR206' -- a wrong column (label's domain is only '+'/'-'); also elem='H' uppercase instead of lowercase 'h'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.elem = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.mol_id = T2.mol_id WHERE T2.lbl = 'TR206';
```

### Q230 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters m.lbl='TR060' instead of the correct molecule_id='TR060' -- label's domain is only '+'/'-', not molecule ID strings.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.elem, m.lbl 
FROM atom a 
JOIN molecule m ON a.mol_id = m.mol_id 
WHERE m.lbl = 'TR060';
```

### Q231 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters m.lbl='TR010' instead of the correct molecule_id='TR010' -- wrong column, label's domain is only '+'/'-'.

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT bnd_type 
FROM bond 
JOIN molecule ON bond.mol_id = molecule.mol_id 
WHERE molecule.lbl = 'TR010' 
GROUP BY bnd_type 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q232 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECTs/orders by m.lbl instead of gold's molecule_id; also bnd_type='single' and lbl NOT LIKE '%carcinogenic%' are invented values (real domains: bond_type='-', label='-').

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT m.lbl 
FROM molecule m 
JOIN bond b ON m.mol_id = b.mol_id 
WHERE b.bnd_type = 'single' 
AND m.lbl NOT LIKE '%carcinogenic%' 
ORDER BY m.lbl ASC 
LIMIT 3;
```

### Q234 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters lbl='TR009' instead of the correct molecule_id='TR009' -- wrong column; also compares atm_id=12 (bare integer) instead of the actual compound-string atom_id format 'TR009_12' -- never matches.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM bond 
JOIN connected ON bond.bnd_id = connected.bnd_id 
JOIN molecule ON bond.mol_id = molecule.mol_id 
WHERE molecule.lbl = 'TR009' AND (connected.atm_id = 12 OR connected.atm_id2 = 12);
```

### Q236 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters m.lbl='TR001_6_9' instead of the correct bond_id='TR001_6_9' -- wrong column entirely (label's domain is only '+'/'-').

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT b.bnd_type, c.atm_id, c.atm_id2 
FROM bond b 
JOIN connected c ON b.bnd_id = c.bnd_id 
JOIN molecule m ON b.mol_id = m.mol_id 
WHERE m.lbl = 'TR001_6_9';
```

### Q239 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Compares atm_id=19 (bare integer) instead of gold's SUBSTR(atom_id,-2)='19' (string suffix match on the compound ID format 'TRxxx_19') -- a missing transformation, not a different column; never matches.

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM connected 
WHERE atm_id = 19;
```

### Q240 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.lbl='TR004' instead of the correct atom.molecule_id='TR004' -- wrong column, label's domain is only '+'/'-'.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT DISTINCT elem 
FROM atom 
JOIN molecule ON atom.mol_id = molecule.mol_id 
WHERE molecule.lbl = 'TR004';
```

### Q242 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECTs m.lbl instead of gold's molecule_id; also compares atm_id BETWEEN 21 AND 25 (bare integers) instead of gold's SUBSTR(atom_id,-2) BETWEEN '21' AND '25' (string suffix match), and drops the label='+' filter entirely.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.lbl 
FROM molecule m 
JOIN atom a ON m.mol_id = a.mol_id 
WHERE a.atm_id BETWEEN 21 AND 25;
```

### Q243 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** Attempts to join bond to connected via a nonexistent connected.mol_id column (connected has no molecule_id at all -- only atom_id, atom_id2, bond_id, verified); the correct join key is bond.bond_id=connected.bond_id.

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.bnd_id
FROM bond b
JOIN connected c ON b.mol_id = c.mol_id
JOIN atom a1 ON c.atm_id = a1.atm_id
JOIN atom a2 ON c.atm_id2 = a2.atm_id
WHERE (a1.elem = 'P' AND a2.elem = 'N') OR (a1.elem = 'N' AND a2.elem = 'P');
```

### Q244 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='DOUBLE' is an invented value (real domain: '-'/'='/'#', double bonds are '='); also collapses gold's tie-preserving HAVING cnt=(MAX cnt) pattern into ORDER BY DESC LIMIT 1.

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
SELECT m.lbl 
FROM molecule m 
JOIN bond b ON m.mol_id = b.mol_id 
WHERE b.bnd_type = 'DOUBLE' 
GROUP BY m.mol_id 
ORDER BY COUNT(b.bnd_id) DESC 
LIMIT 1;
```

### Q245 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** elem='I' (uppercase) instead of gold's lowercase 'i' -- atom.element is stored lowercase; also restructures the computation into AVG(per-atom bond count) via a derived table instead of gold's direct COUNT(bond_id)/COUNT(atom_id) ratio.

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) 
FROM (
    SELECT COUNT(*) AS bond_count 
    FROM atom 
    JOIN connected ON atom.atm_id = connected.atm_id 
    WHERE atom.elem = 'I' 
    GROUP BY atom.atm_id
)
```

### Q247 (challenging, retrieval) -- **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** Drops DISTINCT -- multiple isolated atoms could share the same element, producing duplicate rows.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT elem FROM atom WHERE atm_id NOT IN (SELECT atm_id FROM connected)
```

### Q248 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** Attempts to join connected directly to molecule via a nonexistent connected.mol_id column; molecule_id must be reached via atom.molecule_id or bond.molecule_id instead -- connected has no such column.

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT c.atm_id 
FROM connected c 
JOIN bond b ON c.bnd_id = b.bnd_id 
JOIN molecule m ON c.mol_id = m.mol_id 
WHERE b.bnd_type = 'triple' AND m.lbl = 'TR041';
```

### Q249 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters via molecule.lbl='TR144_8_19' instead of the correct connected.bond_id='TR144_8_19' -- wrong column entirely; label's domain is only '+'/'-', and this value's format ('TRxxx_a_b') is clearly a bond_id, not even a molecule_id.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT elem FROM atom WHERE mol_id = (SELECT mol_id FROM molecule WHERE lbl = 'TR144_8_19');
```

### Q253 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='triple' (invented, real '#') -- never matches.

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.elem 
FROM atom a 
JOIN connected c ON a.atm_id = c.atm_id 
JOIN bond b ON c.bnd_id = b.bnd_id 
WHERE b.bnd_type = 'triple';
```

### Q255 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Inverts gold's structure (same pattern as Q219) -- gold filters to single-bonded molecules (bond_type='-') and computes what % are labeled '+'; predicted filters to lbl='carcinogenic' (an invented value) and computes what % of THEIR bonds are 'single' (also invented) -- numerator/denominator roles swapped.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN b.bnd_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS proportion
FROM bond b
JOIN molecule m ON b.mol_id = m.mol_id
WHERE m.lbl = 'carcinogenic';
```

### Q260 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='triple' (invented, real '#') and elem='P' (wrong case, real is lowercase 'p') -- never matches; also the direct 3-way join (atom+bond+molecule) would inflate COUNT(*) by multiplying each atom by its molecule's bond count if any matches existed.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM atom 
JOIN molecule ON atom.mol_id = molecule.mol_id 
JOIN bond ON molecule.mol_id = bond.mol_id 
WHERE bond.bnd_type = 'triple' AND (atom.elem = 'P' OR atom.elem = 'Br');
```

### Q263 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bnd_type='single' is an invented value (real domain: '-'/'='/'#'; single bonds are '-'); also elem='Cl' is wrong case (real is lowercase 'cl', verified); also joins an unneeded 'connected' table that could inflate counts via row duplication.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN T1.elem = 'Cl' THEN 1 END) * 100.0 / COUNT(T1.atm_id)) AS chlorine_percentage
FROM 
    atom AS T1
JOIN 
    molecule AS T2 ON T1.mol_id = T2.mol_id
JOIN 
    bond AS T3 ON T2.mol_id = T3.mol_id
JOIN 
    connected AS T4 ON T1.atm_id = T4.atm_id
WHERE 
    T3.bnd_type = 'single';
```

### Q273 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lbl LIKE '%carcinogenic%' is an invented value (real domain: label='+'/'-') and elem='Cl' is wrong case (real is lowercase 'cl').

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.elem = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.mol_id = T2.mol_id 
WHERE T2.lbl LIKE '%carcinogenic%'
```

### Q281 (challenging, retrieval) -- **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Groups by mol_id (molecule) instead of gold's element -- a completely different entity/granularity; also drops the COUNT(*) aggregate from the SELECT list, uses an arbitrary LIMIT 3,1 offset instead of gold's full grouped result set, drops the SUBSTR(atom_id,-2)='_4' filter, and uses the invented value lbl='carcinogenic' instead of label='+'.

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT a.elem 
FROM atom a 
JOIN molecule m ON a.mol_id = m.mol_id 
WHERE m.lbl = 'carcinogenic' 
GROUP BY a.mol_id 
ORDER BY a.atm_id 
LIMIT 3, 1;
```

### Q282 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters T2.lbl='TR006' instead of the correct molecule_id='TR006' -- wrong column, label's domain is only '+'/'-'.

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.elem = 'H' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) AS ratio, T2.lbl FROM atom AS T1 JOIN molecule AS T2 ON T1.mol_id = T2.mol_id WHERE T2.lbl = 'TR006'
```

### Q327 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lbl NOT LIKE '%carcinogenic%' is vacuously true for every row (since no label value ever contains 'carcinogenic' -- the real domain is '+'/'-'), so the WHERE clause becomes a no-op instead of gold's label='-' (non-carcinogenic) filter.

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT m.lbl 
FROM molecule m 
JOIN atom a ON m.mol_id = a.mol_id 
WHERE m.lbl NOT LIKE '%carcinogenic%' 
GROUP BY m.mol_id 
HAVING COUNT(a.atm_id) > 5;
```

---

