# Qwen2.5-Coder-14B · L3·S1 -- hand-classified failures (n=387)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. At S1, every column is displayed as `col_a`, `col_b`, ... assigned by 0-indexed position WITHIN EACH TABLE (restarting at `col_a` for every table) -- the same alias string denotes a completely different real column depending on which table it is used with. Every `col_X` reference in the predicted SQL below was decoded against `dev_20240627/dev_tables.json` for the specific table it is declared against in that query's `FROM`/`JOIN` clause before being called a naming bug -- a `col_X` that resolves to the same real column gold uses is never flagged; only genuine substitutions of one real column/table for another, index-out-of-range aliases, or literal-value errors are. This is a much lower-accuracy condition than S2/S3 (the model has almost no naming signal to work with), so Schema linking and JOIN errors dominate far more heavily than at S3. Grouped by database, sorted by question id.

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

## california_schools (30 failures)

### Q5 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Right tables (schools, satscores via IN-subquery) but col_c on satscores decodes to sname (compared > 400) instead of AvgScrMath, and schools.col_b decodes to NCESDist (compared to 'Virtual') instead of Virtual='F'.

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
FROM schools 
WHERE col_a IN (
    SELECT col_a 
    FROM satscores 
    WHERE col_c > 400 
    GROUP BY col_a 
    HAVING AVG(col_c) > 400
) 
AND col_b = 'Virtual';
```

### Q11 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's Enrollment(K-12)/Enrollment(Ages 5-17) filter columns live only on frpm; predicted queries schools alone (col_b=NCESDist>500), missing the required frpm join entirely.

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT col_a FROM schools WHERE col_b > 500;
```

### Q12 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs frpm (FreeMealCount/Enrollment ratio) JOIN satscores (rtype/NumTstTakr/NumGE1500); predicted queries schools alone, MAX(col_ac)=SOCType (text) compared with col_a=CDSCode>0.3 -- neither needed table present.

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
SELECT MAX(col_ac) 
FROM schools 
WHERE col_a > 0.3;
```

### Q17 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** CharterNum lives on schools; predicted queries satscores alone, treating cds (col_a) as charter_number and sname (col_c) as an average score -- schools table missing entirely.

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
    col_a AS charter_number, 
    AVG(col_c) AS average_score, 
    RANK() OVER (ORDER BY AVG(col_c) DESC) AS rank
FROM 
    satscores
WHERE 
    col_c > 499
GROUP BY 
    col_a;
```

### Q23 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's Enrollment(K-12)-Enrollment(Ages 5-17) filter lives only on frpm; predicted queries schools alone, subtracting StatusType-County (col_d-col_e), and selects NCESDist/NCESSchool instead of School/Street.

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT col_b, col_c 
FROM schools 
WHERE col_d - col_e > 30;
```

### Q24 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a vestigial (harmless) schools bridge to correctly-keyed frpm+satscores joins, but SELECT returns schools.NCESDist (s.col_b) instead of frpm.'School Name', WHERE filters frpm.'County Code' (f.col_c) instead of the FreeMealCount/Enrollment ratio, and the NumGE1500 threshold is flipped to >=1500 instead of >0.

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.col_b 
FROM schools s 
JOIN frpm f ON s.col_a = f.col_a 
JOIN satscores ss ON s.col_a = ss.col_a 
WHERE f.col_c > 0.1 AND ss.col_k >= 1500;
```

### Q25 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a vestigial frpm join to a correctly-keyed schools+satscores pair, but SELECT returns schools.NCESDist/NCESSchool instead of sname/FundingType, WHERE filters schools.StatusType (col_d) instead of District LIKE 'Riverside%', GROUP BY groups by CDSCode instead of sname+FundingType, and HAVING averages satscores.cname (ss.col_e, text) instead of AvgScrMath.

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
SELECT s.col_b, s.col_c 
FROM schools s 
JOIN frpm f ON s.col_a = f.col_a 
JOIN satscores ss ON s.col_a = ss.col_a 
WHERE s.col_d = 'Riverside' 
GROUP BY s.col_a 
HAVING AVG(ss.col_e) > 400;
```

### Q26 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's FRPM Count (Ages 5-17) filter lives only on frpm; predicted queries schools alone, filtering CDSCode='Monterey' (col_a) and MailStreet>800 (col_m) -- frpm missing entirely.

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT col_b, col_c, col_d, col_e, col_f, col_g, col_h, col_i, col_j, col_k
FROM schools
WHERE col_a = 'Monterey' AND col_m > 800;
```

### Q27 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_b' -- both joined tables (schools, satscores) have a real column at position b, and the unqualified bare col_b/col_ac references don't disambiguate which table's column is meant; a genuine construction bug from the S1 positional-alias scheme, not a hallucinated identifier.

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT 
    col_b AS school_name, 
    AVG(col_k) AS average_writing_score, 
    col_ac AS communication_number
FROM 
    schools
JOIN 
    satscores ON schools.col_a = satscores.col_a
WHERE 
    col_d > 1991 OR col_e < 2000
GROUP BY 
    col_b, col_ac;
```

### Q28 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's Enrollment(K-12)/Enrollment(Ages 5-17) columns (both the outer filter and the correlated subquery's AVG) live only on frpm; predicted queries schools alone throughout, subtracting StatusType-County and filtering District='Locally Funded' instead of FundingType.

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT col_b, col_c 
FROM schools 
WHERE col_d - col_e > (SELECT AVG(col_d - col_e) FROM schools WHERE col_f = 'Locally Funded');
```

### Q31 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's FreeMealCount(K-12)/Enrollment(K-12) ratio (the entire SELECT output and ORDER BY key) lives only on frpm; predicted queries schools alone, selecting SOCType (col_ac) and ordering by MailStrAbr (col_n).

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT col_ac 
FROM schools 
ORDER BY col_n DESC 
LIMIT 9, 2;
```

### Q32 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's SOC filter lives only on schools; predicted queries frpm alone, filtering frpm.CDSCode=66 (col_a) instead of joining schools.SOC=66 -- schools missing entirely.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT col_c
FROM frpm
WHERE col_a = 66
ORDER BY col_b DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a vestigial frpm join to a correctly-keyed schools+satscores pair, but SELECT returns schools.NCESDist/NCESSchool instead of the Adm* name columns, WHERE filters satscores.cname (ss.col_e, text) >=1500 instead of NumGE1500, and adds a GROUP BY/COUNT gold doesn't have in place of a plain ORDER BY NumGE1500 DESC LIMIT 1.

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
SELECT s.col_b, s.col_c 
FROM schools s 
JOIN frpm f ON s.col_a = f.col_a 
JOIN satscores ss ON s.col_a = ss.col_a 
WHERE ss.col_e >= 1500 
GROUP BY s.col_a 
ORDER BY COUNT(ss.col_e) DESC 
LIMIT 1;
```

### Q37 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's NumGE1500/NumTstTakr ratio (used for both the WHERE filter and the MIN subquery) lives only on satscores; predicted queries schools alone, selecting NCESSchool/StatusType/County/District instead of Street/City/State/Zip and ordering by School name.

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
SELECT col_c, col_d, col_e, col_f 
FROM schools 
ORDER BY col_g ASC 
LIMIT 1;
```

### Q39 (simple, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_c' -- both joined tables (frpm, schools) have a real column at position c, and the unqualified AVG(col_c) doesn't disambiguate; also uses frpm instead of satscores (NumTstTakr) and misapplies the date filter to schools.NCESSchool (col_c) via BETWEEN.

**Gold SQL:**

```sql
SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) 
FROM frpm 
JOIN schools ON frpm.col_a = schools.col_a 
WHERE schools.col_b = 'Fresno' 
AND schools.col_c BETWEEN '1980-01-01' AND '1980-12-31';
```

### Q40 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold orders by satscores.AvgScrRead (also required non-null); predicted queries schools alone, filtering NCESDist='Fresno Unified' (col_b) and ordering by NCESSchool (col_c) instead of AvgScrRead -- satscores missing entirely.

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM schools 
WHERE col_b = 'Fresno Unified' 
ORDER BY col_c ASC 
LIMIT 1;
```

### Q41 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables match gold (schools, satscores) but every satscores column is misresolved: sname (col_c) used as 'county', rtype (col_b) used as 'school_id', dname (col_d, text) averaged as 'avg_reading_score' instead of AvgScrRead; schools.NCESSchool (col_c) is compared to the literal 'Virtual' instead of filtering schools.Virtual='F'.

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
SELECT s.col_b AS school_name
FROM schools s
JOIN (
    SELECT col_c AS county, col_b AS school_id, AVG(col_d) AS avg_reading_score
    FROM satscores
    GROUP BY col_c, col_b
) ss ON s.col_a = ss.school_id
WHERE s.col_c = 'Virtual'
AND ss.avg_reading_score IN (
    SELECT AVG(col_d)
    FROM satscores
    WHERE col_c = ss.county
    GROUP BY col_b
    ORDER BY AVG(col_d) DESC
    LIMIT 5
)
ORDER BY ss.avg_reading_score DESC;
```

### Q45 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables match gold (satscores, schools) but SELECT returns schools.NCESDist (col_b) instead of School, AVG(satscores.sname) (col_c, text) instead of AvgScrWrite, and WHERE compares schools.MailStreet (col_m) to a combined 'Ricci Ulrich' string instead of separate AdmFName1/AdmLName1 filters.

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.AdmFName1 = 'Ricci' AND T2.AdmLName1 = 'Ulrich'
```

**Predicted SQL:**

```sql
SELECT 
    s.col_b AS school_name, 
    AVG(ss.col_c) AS average_writing_score
FROM 
    schools s
JOIN 
    satscores ss ON s.col_a = ss.col_a
WHERE 
    s.col_m = 'Ricci Ulrich'
GROUP BY 
    s.col_b;
```

### Q46 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's DOC filter and School selection live on schools; predicted queries frpm alone, filtering County Code='Special' (col_c) and summing Academic Year (col_b) -- schools missing entirely.

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a, SUM(col_b) AS total_enrollees
FROM frpm
WHERE col_c = 'Special'
GROUP BY col_a
ORDER BY total_enrollees DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (schools) but AVG is taken over NCESSchool (col_c, text) instead of COUNT(School)/12, County='Alameda' filter lands on CDSCode (col_a), and the DOC=52 filter lands on NCESDist (col_b) compared to a district-type string instead of the numeric DOC code.

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) 
FROM schools 
WHERE col_a = 'Alameda' AND col_b = 'Elementary School District' AND strftime('%Y', col_d) = '1980';
```

### Q48 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (schools) but the DOC='54'/'52' distinction is replaced with NCESSchool (col_c) compared to district-type strings, the County='Orange' filter lands on NCESDist (col_b) compared to 'Orange County', and the shared StatusType='Merged' filter is dropped from both halves of the ratio.

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
    CAST(SUM(CASE WHEN col_c = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN col_c = 'Elementary School District' THEN 1 ELSE 0 END) AS ratio
FROM 
    schools
WHERE 
    col_b = 'Orange County';
```

### Q50 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold orders by satscores.AvgScrMath (also required non-null, rtype='S'); predicted queries schools alone, selecting NCESSchool/StatusType (col_c/col_d) instead of MailStreet/School and ordering by County (col_e) -- satscores missing entirely.

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
SELECT col_c, col_d 
FROM schools 
ORDER BY col_e DESC 
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's FreeMealCount(K-12)/Enrollment(K-12) ratio filter lives only on frpm; predicted queries schools alone, filtering StatusType='Los Angeles' (col_d), County='Non-Charter' (col_e), and District<0.18 (col_f) -- frpm missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM schools 
WHERE col_d = 'Los Angeles' 
AND col_e = 'Non-Charter' 
AND col_f < 0.18;
```

### Q72 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and join key are correct (frpm.CDSCode=schools.CDSCode) but COUNT(*) replaces SUM(Enrollment Ages 5-17), the BETWEEN 2014-2015 filter lands on Academic Year (frpm.col_b) compared to 5/17, EdOpsCode='SSS' lands on schools.NCESDist (col_b), and City='Fremont' lands on schools.NCESSchool (col_c).

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
JOIN schools ON frpm.col_a = schools.col_a 
WHERE frpm.col_b BETWEEN 5 AND 17 
AND schools.col_b = 'State Special School' 
AND schools.col_c = 'Fremont' 
AND frpm.col_c = '2014-2015';
```

### Q77 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and join key are correct (schools.CDSCode=frpm.CDSCode) but SELECT returns schools.NCESDist (col_b) and frpm.'School Code' (col_e) instead of School and the FRPM/Enrollment(Ages 5-17) ratio, and WHERE filters schools.Zip (col_k)='Los Angeles' and schools.MailStreet (col_m)='Kindergarten to 9th grade' instead of County/GSserved.

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT 
    s.col_b AS school_name, 
    f.col_e AS percent_eligible_frpm
FROM 
    schools s
JOIN 
    frpm f ON s.col_a = f.col_a
WHERE 
    s.col_k = 'Los Angeles' 
    AND s.col_m = 'Kindergarten to 9th grade';
```

### Q79 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (schools) but SELECT/GROUP BY use CDSCode (col_a) instead of County, the County IN (...) filter lands on NCESDist (col_b), and Virtual='F' lands on NCESSchool (col_c)='No'.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a, COUNT(*) AS school_count
FROM schools
WHERE col_b IN ('San Diego', 'Santa Barbara') AND col_c = 'No'
GROUP BY col_a
ORDER BY school_count DESC
LIMIT 1;
```

### Q82 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (schools) but SELECT computes Magnet-Latitude (col_ak-col_al) instead of GSoffered; ORDER BY does correctly land on Longitude (col_am) but is missing gold's ABS() wrapper.

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_ak - col_al AS grade_span 
FROM schools 
ORDER BY col_am DESC 
LIMIT 1;
```

### Q83 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's NSLP Provision Status filter lives only on frpm; predicted queries schools alone, filtering StatusType='Kindergarten to 8th grade' (col_d) instead of GSoffered and County (col_e) instead of the frpm NSLP field -- frpm missing entirely.

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT col_c, COUNT(*) 
FROM schools 
WHERE col_d = 'Kindergarten to 8th grade' AND col_e = 'Multiple Provision Types' 
GROUP BY col_c;
```

### Q85 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's FreeMealCount(K-12)/Enrollment(K-12) ratio and District Code (the entire SELECT output) live only on frpm; predicted queries schools alone, selecting CDSCode/NCESDist and filtering NCESSchool (col_c)='Alusine' instead of AdmFName1 -- frpm missing entirely.

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT col_a, col_b 
FROM schools 
WHERE col_c = 'Alusine';
```

### Q87 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold's frpm JOIN is vestigial (no frpm column is ever selected or filtered -- every predicate and both SELECT columns are schools fields), so predicted's schools-only table choice is structurally sufficient; the actual bug is every column being wrong: SOCType/EdOpsCode (col_ac/col_ad) instead of AdmEmail1/AdmEmail2, NCESDist/NCESSchool instead of County/City, StatusType instead of OpenDate, County instead of DOC, District instead of SOC.

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT col_ac, col_ad 
FROM schools 
WHERE col_b = 'San Bernardino' 
AND col_c = 'City of San Bernardino City Unified' 
AND col_d BETWEEN '2009-01-01' AND '2010-12-31' 
AND col_e = 'Intermediate/Middle School' 
AND col_f = 'Unified School';
```

---

## debit_card_specializing (30 failures)

### Q1471 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** col_e on transactions_1k decodes to CardID, not Currency; gold needs customers.Currency -- entire wrong table queried (both single-table, no join either side).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN col_e = 'EUR' THEN 1 ELSE 0 END) * 1.0 / 
    SUM(CASE WHEN col_e = 'CZK' THEN 1 ELSE 0 END) AS ratio
FROM 
    transactions_1k;
```

### Q1472 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Inserts an unneeded transactions_1k hop between customers and yearmonth (c.col_a=t.col_a joins CustomerID to TransactionID; t.col_e=y.col_a joins CardID to CustomerID) instead of gold's direct customers-yearmonth join; Segment filter lands on transactions_1k.Time (col_c) and consumption ordering on ProductID (col_g).

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.col_a 
FROM customers c 
JOIN transactions_1k t ON c.col_a = t.col_a 
JOIN yearmonth y ON t.col_e = y.col_a 
WHERE y.col_b = '2012' AND t.col_c = 'LAM' 
GROUP BY c.col_a 
ORDER BY SUM(t.col_g) ASC 
LIMIT 1;
```

### Q1473 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Collapses the required customers+yearmonth join into a single wrong table transactions_1k; TransactionID (col_a) compared to 'SME' and Time (col_c) LIKE a year pattern.

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(col_e) 
FROM transactions_1k 
WHERE col_a = 'SME' AND col_c LIKE '2013%';
```

### Q1476 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs customers JOIN yearmonth; predicted queries transactions_1k alone -- CardID (col_e) compared to 'CZK'/'EUR', ProductID (col_g) summed instead of Consumption.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN col_e = 'CZK' THEN col_g ELSE 0 END) - 
    SUM(CASE WHEN col_e = 'EUR' THEN col_g ELSE 0 END) AS difference
FROM 
    transactions_1k
WHERE 
    col_a LIKE '2012%';
```

### Q1479 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs customers JOIN yearmonth; predicted queries transactions_1k alone, grouping/selecting TransactionID (col_a) and ordering by Time (col_c) instead of Consumption.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM transactions_1k 
WHERE col_e = 'CZK' 
GROUP BY col_a 
ORDER BY SUM(col_c) DESC 
LIMIT 1;
```

### Q1480 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Swaps customers for transactions_1k in the yearmonth join (t.col_e=CardID joined to ym.col_a=CustomerID); Segment filter lands on transactions_1k.Date (col_b), consumption ordering on ProductID (col_g).

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT ym.col_b AS peak_month
FROM transactions_1k t
JOIN yearmonth ym ON t.col_e = ym.col_a
WHERE ym.col_c = '2013' AND t.col_b = 'SME'
GROUP BY ym.col_b
ORDER BY SUM(t.col_g) DESC
LIMIT 1;
```

### Q1481 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's CTEs join customers+yearmonth (grouped per customer); predicted runs correlated subqueries against transactions_1k alone -- TransactionID (col_a) compared to segment names, ProductID (col_g) compared to 'CZK', Time (col_c) run through strftime as if it were Date.

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(col_e) 
     FROM transactions_1k 
     WHERE col_a = 'SME' AND col_g = 'CZK' AND strftime('%Y', col_c) = '2013') -
    (SELECT AVG(col_e) 
     FROM transactions_1k 
     WHERE col_a = 'LAM' AND col_g = 'CZK' AND strftime('%Y', col_c) = '2013') AS diff_sme_lam,
    
    (SELECT AVG(col_e) 
     FROM transactions_1k 
     WHERE col_a = 'LAM' AND col_g = 'CZK' AND strftime('%Y', col_c) = '2013') -
    (SELECT AVG(col_e) 
     FROM transactions_1k 
     WHERE col_a = 'KAM' AND col_g = 'CZK' AND strftime('%Y', col_c) = '2013') AS diff_lam_kam,
    
    (SELECT AVG(col_e) 
     FROM transactions_1k 
     WHERE col_a = 'KAM' AND col_g = 'CZK' AND strftime('%Y', col_c) = '2013') -
    (SELECT AVG(col_e) 
     FROM transactions_1k 
     WHERE col_a = 'SME' AND col_g = 'CZK' AND strftime('%Y', col_c) = '2013') AS diff_kam_sme;
```

### Q1482 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs customers JOIN yearmonth filtered by Currency='EUR'; predicted queries transactions_1k alone, grouping by Date (col_b) as if it were Segment and computing the ratio over CardID (col_e).

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    col_b AS category,
    ((SUM(CASE WHEN col_a = '2013' THEN col_e ELSE 0 END) - SUM(CASE WHEN col_a = '2012' THEN col_e ELSE 0 END)) * 100.0 / SUM(CASE WHEN col_a = '2012' THEN col_e ELSE 0 END)) AS percentage_change
FROM 
    transactions_1k
WHERE 
    col_b IN ('SME', 'LAM', 'KAM')
GROUP BY 
    col_b;
```

### Q1483 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is yearmonth; predicted substitutes transactions_1k -- CardID (col_e) summed, Date (col_b) compared to a CustomerID literal, Time (col_c) compared to a date range.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(col_e) 
FROM transactions_1k 
WHERE col_b = 6 
AND col_c BETWEEN '2013-08' AND '2013-11';
```

### Q1484 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** col_c/col_d correctly resolve to gasstations.Country/Segment (right table, right columns), but literals are invented full names ('Czech Republic'/'Slovakia') and lowercase 'discount' instead of gold's real codes 'CZE'/'SVK'/'Discount'.

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM gasstations WHERE col_c = 'Czech Republic' AND col_d = 'discount') - 
    (SELECT COUNT(*) FROM gasstations WHERE col_c = 'Slovakia' AND col_d = 'discount') AS difference;
```

### Q1486 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is customers (Currency, Segment); predicted substitutes transactions_1k -- CardID (col_e) compared to 'CZK'/'EUR', and the Segment='SME' filter is dropped entirely.

**Gold SQL:**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN col_e = 'CZK' THEN 1 ELSE 0 END) - SUM(CASE WHEN col_e = 'EUR' THEN 1 ELSE 0 END) AS difference
FROM 
    transactions_1k;
```

### Q1490 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Swaps yearmonth for transactions_1k in the customers join (join key CustomerID=CustomerID happens to still be col_a=col_a by coincidence, but the joined table is wrong); Consumption threshold applied to transactions_1k.Date (col_b) instead of yearmonth.Consumption; also silently drops gold's LEFT JOIN for an INNER JOIN, but that's secondary to the wrong table.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.col_b > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM customers AS T1 
JOIN transactions_1k AS T2 ON T1.col_a = T2.col_a 
WHERE T1.col_b = 'LAM';
```

### Q1493 (simple, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Nests SUM(col_e) inside a CASE WHEN wrapped in an outer SUM -- SUM(CASE WHEN SUM(...) ...) is a nested-aggregate misuse; execution fails with 'misuse of aggregate function SUM()'.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SUM(col_e) > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT col_a) 
FROM transactions_1k 
JOIN yearmonth ON transactions_1k.col_g = yearmonth.col_a 
WHERE yearmonth.col_b = '2012' AND yearmonth.col_c = 'February' 
GROUP BY col_a;
```

### Q1498 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is yearmonth (SUM(Consumption) grouped by month); predicted substitutes transactions_1k -- MAX(CardID) (col_e) filtered on TransactionID (col_a) compared to '2012'.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(col_e) 
FROM transactions_1k 
WHERE col_a = '2012';
```

### Q1500 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unneeded yearmonth join (t.col_g=ProductID joined to y.col_a=CustomerID) and links products to transactions_1k via CardID (t.col_e) instead of ProductID (t.col_g); date filter incorrectly split onto yearmonth.Date/Consumption instead of transactions_1k.Date.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.col_b 
FROM products p 
JOIN transactions_1k t ON p.col_a = t.col_e 
JOIN yearmonth y ON t.col_g = y.col_a 
WHERE y.col_b = '2012' AND y.col_c = '8';
```

### Q1501 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unneeded yearmonth join (ProductID joined to CustomerID) and links gasstations to transactions_1k via Date (t.col_b) instead of GasStationID (t.col_f); date filter incorrectly split onto yearmonth.Date/Consumption.

**Gold SQL:**

```sql
SELECT DISTINCT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT gs.col_c 
FROM gasstations gs 
JOIN transactions_1k t ON gs.col_a = t.col_b 
JOIN yearmonth ym ON t.col_g = ym.col_a 
WHERE ym.col_b = '2012' AND ym.col_c = '8';
```

### Q1505 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs yearmonth JOIN customers; predicted queries transactions_1k alone, filtering CardID='euro' and HAVING SUM(Time) > 1000 instead of Consumption.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT col_a) 
FROM transactions_1k 
WHERE col_e = 'euro' 
GROUP BY col_a, col_b 
HAVING SUM(col_c) > 1000;
```

### Q1506 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 3 tables as gold (transactions_1k, gasstations, products) but both join keys are wrong: products joined via CardID (t.col_e) instead of ProductID (t.col_g), gasstations joined via Time (t.col_c) instead of GasStationID (t.col_f); WHERE also uses gasstations.Segment (col_d) with an invented value instead of Country='CZE'.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.col_b 
FROM transactions_1k t 
JOIN products p ON t.col_e = p.col_a 
JOIN gasstations g ON t.col_c = g.col_a 
WHERE g.col_d = 'Czech Republic';
```

### Q1507 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold but joined via Time (T.col_c) instead of GasStationID (T.col_f); WHERE filters gasstations.Segment (col_d)=11 instead of ChainID (col_b), and SELECT returns ProductID (col_g) instead of Time.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T2.ChainID = 11
```

**Predicted SQL:**

```sql
SELECT DISTINCT T.col_g 
FROM transactions_1k AS T 
JOIN gasstations AS G ON T.col_c = G.col_a 
WHERE G.col_d = 11;
```

### Q1509 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold but joined via Time (col_c) instead of GasStationID (col_f); WHERE filters gasstations.Segment (col_d) with an invented value instead of Country, and CardID (col_e) instead of Date for the date-range predicate.

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
JOIN gasstations ON transactions_1k.col_c = gasstations.col_a 
WHERE gasstations.col_d = 'Czech Republic' AND transactions_1k.col_e > '2012-01-01';
```

### Q1514 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs transactions_1k JOIN gasstations JOIN customers to reach Currency; predicted queries transactions_1k alone, returning ProductID (col_g) and filtering CardID (col_e) against a combined datetime string instead of separate Date/Time columns.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT col_g 
FROM transactions_1k 
WHERE col_e = '2012-08-24 16:25:00';
```

### Q1515 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Both tables match gold (transactions_1k, customers) but every column is misresolved: outer SELECT returns customers.Currency (col_c) instead of Segment (col_b); subquery filters transactions_1k.CustomerID (col_d) against a datetime literal and returns TransactionID (col_a) instead of filtering Date/Time and returning CustomerID.

**Gold SQL:**

```sql
SELECT T2.Segment FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.date = '2012-08-23' AND T1.time = '21:20:00'
```

**Predicted SQL:**

```sql
SELECT col_c 
FROM customers 
WHERE col_a = (SELECT col_a FROM transactions_1k WHERE col_d = '2012-08-23 21:20:00');
```

### Q1521 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs transactions_1k JOIN gasstations for the Country filter; predicted queries transactions_1k alone, filtering CardID (col_e) against a datetime range and ProductID (col_g) against 'CZE'.

**Gold SQL:**

```sql
SELECT COUNT(T1.TransactionID) FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-26' AND T1.Time BETWEEN '08:00:00' AND '09:00:00' AND T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM transactions_1k 
WHERE col_e BETWEEN '2012-08-26 08:00:00' AND '2012-08-26 09:00:00' 
AND col_g = 'CZE';
```

### Q1524 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Swaps gasstations for customers in the transactions_1k join (joined via TransactionID (t.col_a) instead of CustomerID); date/price filters land on CardID (col_e) and ProductID (col_g); SELECT returns customers.Segment (col_b) instead of gasstations.Country.

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT c.col_b 
FROM customers c 
JOIN transactions_1k t ON c.col_a = t.col_a 
WHERE t.col_e = '2012-08-24' AND t.col_g = 548.4;
```

### Q1525 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs transactions_1k JOIN customers for the Currency='EUR' filter; predicted queries transactions_1k alone, filtering CardID (col_e)='EUR' and Time (col_c) instead of Date.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_e = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM transactions_1k 
WHERE col_c = '2012-08-25';
```

### Q1526 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's subquery uses transactions_1k+gasstations (price/date) to find a CustomerID, then yearmonth for the consumption trend -- no customers table involved at all; predicted instead joins transactions_1k to customers via TransactionID=CustomerID (col_a=col_a) and never touches gasstations or yearmonth.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN strftime('%Y-%m-%d', transactions_1k.col_e) = '2012-08-25' THEN transactions_1k.col_c ELSE 0 END) - 
     SUM(CASE WHEN strftime('%Y', transactions_1k.col_e) = '2013' THEN transactions_1k.col_c ELSE 0 END)) / 
    SUM(CASE WHEN strftime('%Y', transactions_1k.col_e) = '2012' THEN transactions_1k.col_c ELSE 0 END) AS consumption_decrease_rate
FROM 
    transactions_1k
JOIN 
    customers ON transactions_1k.col_a = customers.col_a
WHERE 
    customers.col_b = 634.8;
```

### Q1528 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is gasstations (Country/Segment); predicted substitutes transactions_1k -- Date (col_b) compared to 'premium' and Time (col_c) compared to 'SVK'.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN col_b = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage_premium
FROM 
    transactions_1k
WHERE 
    col_c = 'SVK';
```

### Q1529 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (transactions_1k) but SUM aggregates CardID (col_e) instead of Amount*Price; WHERE filters Date (col_b) against the CustomerID literal and Time (col_c) against the month literal instead of CustomerID/Date; the August-2012 conditional sum is dropped entirely.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(col_e) AS total_spent
FROM transactions_1k
WHERE col_b = '38508' AND col_c = '2012-08';
```

### Q1531 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (customers, transactions_1k) but joined via Date (t.col_b) instead of CustomerID (t.col_d); aggregates CardID (col_e) instead of Price, and reports GasStationID (col_f) as 'currency'.

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT c.col_a AS customer_id, AVG(t.col_e) AS average_price_per_item, t.col_f AS currency
FROM customers c
JOIN transactions_1k t ON c.col_a = t.col_b
GROUP BY c.col_a, t.col_f
ORDER BY SUM(t.col_e * t.col_c) DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (transactions_1k, yearmonth) but joined via ProductID (t.col_g) instead of CustomerID (t.col_d); Price/Amount ratio filter lands on CardID (col_e), and the ProductID=5 filter lands on Date (col_b).

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT t.col_c, y.col_c
FROM transactions_1k t
JOIN yearmonth y ON t.col_g = y.col_a
WHERE t.col_e > 29.00 AND t.col_b = 5 AND y.col_b = '2012-08';
```

---

## european_football_2 (50 failures)

### Q1025 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** M.col_ae decodes to away_player_X9, not season (col_d); M.col_l decodes to home_player_X1, not home_team_goal (col_j), corrupting the SUM

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.col_b 
FROM League L 
JOIN Match M ON L.col_a = M.col_c 
WHERE M.col_ae = '2016' 
GROUP BY L.col_b 
ORDER BY SUM(M.col_k + M.col_l) DESC 
LIMIT 1;
```

### Q1028 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** T1.col_y decodes to away_player_X3, not season (col_d), so the season filter is nonsensical; team joins also use match_api_id/Team.id instead of home/away_team_api_id/team_api_id, the goal comparison direction is reversed, and the tied-for-max-win-count HAVING subquery is replaced by a plain ORDER BY/LIMIT

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T3.col_b AS away_team_name
FROM Match AS T1
JOIN Team AS T2 ON T1.col_g = T2.col_a
JOIN Team AS T3 ON T1.col_i = T3.col_a
JOIN League AS T4 ON T1.col_c = T4.col_a
WHERE T4.col_b = 'Scotland Premier League'
AND T1.col_y = 2010
AND T1.col_j > T1.col_k
GROUP BY T3.col_b
ORDER BY COUNT(*) DESC
LIMIT 1;
```

### Q1029 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a/col_b decode to id/team_fifa_api_id, not buildUpPlaySpeed (col_e); ORDER BY also uses col_c (team_api_id) instead of buildUpPlaySpeed

**Gold SQL:**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT col_a, col_b 
FROM Team_Attributes 
ORDER BY col_c DESC 
LIMIT 4;
```

### Q1030 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** M.col_ae decodes to away_player_X9 not season; M.col_bj decodes to home_player_7, not a goal-equality comparison — should be home_team_goal=away_team_goal (col_j=col_k)

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.col_b 
FROM League L 
JOIN Match M ON L.col_a = M.col_c 
WHERE M.col_ae = '2016' AND M.col_bj = 'Draw' 
GROUP BY L.col_b 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1031 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT col_a returns Player_Attributes.id, not an age computed from Player.birthday (no join present); col_ac decodes to long_shots not sprint_speed (col_u); col_b decodes to player_fifa_api_id not date (col_d)

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
SELECT col_a 
FROM Player_Attributes 
WHERE col_ac >= 97 AND col_b BETWEEN 2013 AND 2015;
```

### Q1032 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Collapses gold's tie-preserving HAVING COUNT(m.id) = (SELECT MAX(match_count)...) subquery into a plain ORDER BY COUNT DESC LIMIT 1, dropping ties; join/select columns are otherwise correct

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT L.col_b, COUNT(*) AS match_count
FROM League L
JOIN Match M ON L.col_a = M.col_c
GROUP BY L.col_a
ORDER BY match_count DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a decodes to id not team_fifa_api_id (col_b); col_c decodes to team_api_id not buildUpPlaySpeed (col_e); also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM Team_Attributes 
WHERE col_c BETWEEN 50 AND 59;
```

### Q1036 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** TA.col_j decodes to buildUpPlayPassingClass (categorical) not buildUpPlayPassing (col_i, numeric); TA.col_c used as a date is actually team_api_id; join uses Team.id=Team_Attributes.id instead of team_api_id; SELECT returns team_api_id (col_b) not team_long_name (col_d)

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T.col_b 
FROM Team AS T 
JOIN Team_Attributes AS TA ON T.col_a = TA.col_a 
WHERE TA.col_j > (SELECT AVG(col_j) FROM Team_Attributes WHERE strftime('%Y', col_c) = '2012') 
AND strftime('%Y', TA.col_c) = '2012';
```

### Q1037 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_x decodes to balance not preferred_foot (col_g); col_c (player_api_id) used as a birthday-range filter instead of joining Player.birthday (no join present)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_x = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player_Attributes 
WHERE col_c BETWEEN '1987-01-01' AND '1992-12-31';
```

### Q1039 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Player.col_b decodes to player_api_id, not player_name (col_c) — filter compares a numeric ID to a name string; col_x decodes to balance not long_shots (col_ac); join also uses Player.id=Player_Attributes.id instead of player_api_id

**Gold SQL:**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL:**

```sql
SELECT AVG(col_x) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_b = 'Ahmed Samir Farag';
```

### Q1040 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** P.col_c decodes to player_name (not height=col_f) used in a numeric filter; P.col_b decodes to player_api_id (not player_name=col_c) in SELECT; PA.col_ah decodes to penalties not heading_accuracy (col_l); join also uses id instead of player_api_id

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
SELECT P.col_b 
FROM Player P 
JOIN Player_Attributes PA ON P.col_a = PA.col_a 
WHERE P.col_c > 180 
GROUP BY P.col_a 
ORDER BY AVG(PA.col_ah) DESC 
LIMIT 10;
```

### Q1042 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** M.col_a (Match.id) used as a season/date-range filter instead of season (col_d); M.col_l decodes to home_player_X1, not home_team_goal (col_j), breaking the HAVING comparison

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2009/2010' GROUP BY t1.name HAVING (CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) - (CAST(SUM(t2.away_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) > 0
```

**Predicted SQL:**

```sql
SELECT L.col_b 
FROM League L 
JOIN Match M ON L.col_a = M.col_c 
WHERE M.col_a BETWEEN '2009-08-01' AND '2010-07-31' 
GROUP BY L.col_a 
HAVING AVG(M.col_k) > AVG(M.col_l);
```

### Q1044 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_c decodes to player_name not birthday (col_e); col_d decodes to player_fifa_api_id not a month field; SELECT * also replaces the specific player_name projection

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE SUBSTR(birthday, 1, 7) = '1970-10'
```

**Predicted SQL:**

```sql
SELECT * FROM Player WHERE col_c = '1970' AND col_d = 'October'
```

### Q1048 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a decodes to id not overall_rating (col_e); col_b (player_fifa_api_id) used as the name filter instead of joining Player.player_name (no join present); col_c (player_api_id) used as the year filter instead of date (col_d)

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Gabriel Tamas' AND strftime('%Y', t2.date) = '2011'
```

**Predicted SQL:**

```sql
SELECT col_a FROM Player_Attributes WHERE col_b = 'Gabriel Tamas' AND col_c = 2011
```

### Q1057 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** AVG(col_k) decodes to away_team_goal not home_team_goal (col_j); also routes country_id through an unneeded Team join and filters on Match.id (col_a) instead of season/date

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(t2.id) FROM Country AS t1 INNER JOIN Match AS t2 ON t1.id = t2.country_id WHERE t1.name = 'Poland' AND t2.season = '2010/2011'
```

**Predicted SQL:**

```sql
SELECT AVG(col_k) 
FROM Match 
JOIN Team ON Match.col_c = Team.col_a 
JOIN Country ON Team.col_d = Country.col_a 
WHERE Country.col_b = 'Poland' AND Match.col_a BETWEEN '2010-08-01' AND '2011-07-31';
```

### Q1068 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a (id) averaged instead of overall_rating (col_e); col_c (player_api_id) used as the height filter instead of joining Player.height (no join present); col_b (player_fifa_api_id) used as the year-range filter instead of date (col_d)

**Gold SQL:**

```sql
SELECT AVG(t2.overall_rating) AS avg_rating
FROM `Player` AS t1
JOIN `Player_Attributes` AS t2 ON t1.player_api_id = t2.player_api_id
WHERE t1.height > 170
  AND strftime('%Y', t2.`date`) BETWEEN '2010' AND '2015';
```

**Predicted SQL:**

```sql
SELECT AVG(col_a) 
FROM Player_Attributes 
WHERE col_b BETWEEN 2010 AND 2015 AND col_c > 170;
```

### Q1076 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ac decodes to long_shots not ball_control (col_s); join also matches Player_Attributes.id=Player.id instead of via player_api_id

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(col_ac) FROM Player_Attributes WHERE col_a = (SELECT col_a FROM Player WHERE col_c = 'Abdou Diallo')) -
    (SELECT AVG(col_ac) FROM Player_Attributes WHERE col_a = (SELECT col_a FROM Player WHERE col_c = 'Aaron Appindangoye')) AS difference;
```

### Q1078 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_b decodes to player_api_id not player_name (col_c) in SELECT; col_d decodes to player_fifa_api_id not birthday (col_e) in ORDER BY; also DESC vs gold's ASC

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM Player 
WHERE col_c = 'Aaron Lennon' OR col_c = 'Abdelaziz Barrada' 
ORDER BY col_d DESC 
LIMIT 1;
```

### Q1079 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_b decodes to player_api_id not player_name (col_c); col_c used in ORDER BY decodes to player_name not height (col_f)

**Gold SQL:**

```sql
SELECT player_name FROM Player ORDER BY height DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_b FROM Player ORDER BY col_c DESC LIMIT 1
```

### Q1080 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ac decodes to long_shots not preferred_foot (col_g); col_ad decodes to aggression not attacking_work_rate (col_h); also uses COUNT(*) instead of COUNT(DISTINCT player_api_id)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE col_ac = 'left' AND col_ad = 'left';
```

### Q1084 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a (id) compared to a birth-year string instead of joining Player.birthday (no join present); col_b decodes to player_fifa_api_id compared to 'GK' instead of defensive_work_rate='high' (col_i); col_c (player_api_id) adds a spurious 'Defender' filter with no gold counterpart

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE col_a < '1986' AND col_b = 'GK' AND col_c = 'Defender';
```

### Q1088 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ac decodes to long_shots not volleys (col_n); col_ad decodes to aggression not dribbling (col_o); also matches on internal id instead of player_api_id

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT col_b FROM Player WHERE col_a IN (SELECT col_a FROM Player_Attributes WHERE col_ac > 70 AND col_ad > 70)
```

### Q1091 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Match.col_d decodes to season not date (col_f), breaking the strftime('%Y-%m',...) month filter; also splits the single League.name string into a nonexistent country_id='Belgium'+name='Jupiler League' pair via an unneeded Country join

**Gold SQL:**

```sql
SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND SUBSTR(t2."date", 1, 7) = '2009-04'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Match 
JOIN League ON Match.col_c = League.col_a 
JOIN Country ON League.col_b = Country.col_a 
WHERE League.col_b = 'Belgium' AND League.col_c = 'Jupiler League' AND strftime('%Y-%m', Match.col_d) = '2009-04';
```

### Q1092 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** M.col_a (Match.id) used as a season/date-range filter instead of season (col_d); also collapses gold's tie-preserving HAVING=MAX(subquery) into ORDER BY/LIMIT

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT L.col_b 
FROM League L 
JOIN Match M ON L.col_a = M.col_c 
WHERE M.col_a BETWEEN '2008-08-01' AND '2009-07-31' 
GROUP BY L.col_b 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1094 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Player.col_b decodes to player_api_id, not player_name (col_c) — the name filter compares an ID to a string; col_x decodes to balance not overall_rating (col_e); join also matches Player_Attributes.id=Player.id instead of player_api_id; also drops the 'most recent record' ORDER BY date DESC LIMIT1 gold's CTEs apply

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT 
    ((SELECT col_x FROM Player_Attributes WHERE col_a = (SELECT col_a FROM Player WHERE col_b = 'Ariel Borysiuk')) - 
     (SELECT col_x FROM Player_Attributes WHERE col_a = (SELECT col_a FROM Player WHERE col_b = 'Paulin Puel'))) * 100.0 / 
    (SELECT col_x FROM Player_Attributes WHERE col_a = (SELECT col_a FROM Player WHERE col_b = 'Paulin Puel')) AS percentage_increase;
```

### Q1096 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Bare col_a is ambiguous between Player_Attributes and Player (both joined tables have a col_a), triggering SQLite's ambiguous-column error; underlying join key and name filter are also on the wrong columns

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Pietro Marino'
```

**Predicted SQL:**

```sql
SELECT AVG(col_a) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_b = 'Pietro Marino';
```

### Q1098 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Team.col_b decodes to team_api_id not team_long_name (col_d) — filter can't match 'Ajax'; col_x/col_y decode to defenceTeamWidthClass/defenceDefenderLineClass, not chanceCreationPassing (col_l)/chanceCreationPassingClass (col_m); join also uses internal id instead of team_api_id

**Gold SQL:**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(col_x), col_y 
FROM Team_Attributes 
JOIN Team ON Team_Attributes.col_a = Team.col_a 
WHERE Team.col_b = 'Ajax';
```

### Q1102 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** PA.col_j decodes to crossing not date (col_d); PA.col_k decodes to finishing not overall_rating (col_e); P.col_b decodes to player_api_id not player_name (col_c) in SELECT; P.col_c used in ORDER BY decodes to player_name not birthday (col_e), also DESC vs gold's ASC

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.col_b 
FROM Player P 
JOIN Player_Attributes PA ON P.col_a = PA.col_a 
WHERE PA.col_j = '2016-06-23' AND PA.col_k = 77 
ORDER BY P.col_c DESC 
LIMIT 1;
```

### Q1103 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a returns id not overall_rating (col_e); col_b (player_fifa_api_id) compared to a name string instead of joining Player.player_name (no join present); col_c (player_api_id) used as the date filter instead of date (col_d)

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT col_a FROM Player_Attributes WHERE col_b = 'Aaron Mooy' AND col_c = '2016/2/4'
```

### Q1105 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ac decodes to long_shots not attacking_work_rate (col_h); Player.col_b decodes to player_api_id not player_name (col_c); Player_Attributes.col_b decodes to player_fifa_api_id not date (col_d); join uses internal id instead of player_api_id

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT col_ac 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_b = 'Francesco Migliore' AND Player_Attributes.col_b = '2015/5/1';
```

### Q1107 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Bare col_a is ambiguous between Player_Attributes and Player (both joined tables have col_a), same pattern as Q1096; underlying join also uses internal id instead of player_fifa_api_id, and ORDER BY col_ac decodes to long_shots not crossing (col_j)

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_b = 'Kevin Constant' 
ORDER BY Player_Attributes.col_ac DESC 
LIMIT 1;
```

### Q1110 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a returns id not buildUpPlayPassingClass (col_j); col_b (team_fifa_api_id) compared to 'FC Lorient' instead of joining Team.team_long_name (no join present); col_c (team_api_id) used as the date filter instead of date (col_d)

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM Team_Attributes 
WHERE col_b = 'FC Lorient' AND col_c = '2010-02-22';
```

### Q1113 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_e decodes to buildUpPlaySpeed not defenceAggressionClass (col_v); Team.col_b decodes to team_api_id not team_long_name (col_d) — can't match 'Hannover 96'; Team_Attributes.col_c decodes to team_api_id not date (col_d); subquery join also uses internal id not team_api_id

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT col_e 
FROM Team_Attributes 
WHERE col_a = (SELECT col_a FROM Team WHERE col_b = 'Hannover 96') 
AND col_c = '2015-09-10';
```

### Q1114 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ae decodes to interceptions not overall_rating (col_e); Player_Attributes.col_b decodes to player_fifa_api_id not date (col_d) for the date-range filter; join uses internal id instead of player_fifa_api_id

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(col_ae) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_c = 'Marko Arnautovic' 
AND Player_Attributes.col_b BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** Predicted references the real column name 'overall_rating' directly instead of a col_X alias; under S1 no column is literally named 'overall_rating' anywhere in the queried schema, so it's a hallucinated identifier — genuine execution error ('no such column: L.overall_rating')

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
    ((L.overall_rating - J.overall_rating) * 100.0 / J.overall_rating) AS percentage_difference
FROM 
    Player_Attributes L
JOIN 
    Player_Attributes J ON L.col_a = J.col_a
JOIN 
    Player P_L ON L.col_a = P_L.col_a
JOIN 
    Player P_J ON J.col_a = P_J.col_a
WHERE 
    P_L.col_b = 'Landon Donovan' 
    AND P_J.col_b = 'Jordan Bowery' 
    AND L.col_c = '2013/7/12' 
    AND J.col_c = '2013/7/12';
```

### Q1116 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_b decodes to player_api_id not player_name (col_c); col_c used in ORDER BY decodes to player_name not height (col_f); also drops gold's DENSE_RANK() tie-handling in favor of a plain LIMIT 1

**Gold SQL:**

```sql
SELECT player_name FROM (SELECT player_name, height, DENSE_RANK() OVER (ORDER BY height DESC) as rank FROM Player) WHERE rank = 1
```

**Predicted SQL:**

```sql
SELECT col_b FROM Player ORDER BY col_c DESC LIMIT 1;
```

### Q1122 (simple, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** col_ac is used against Player, which only has 7 columns (up to col_g) — col_ac (position 28) is out of range and matches no real column, causing 'no such column: col_ac'; the model apparently intended a Player_Attributes column (overall_rating) but never joins Player_Attributes at all

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT col_b FROM Player ORDER BY col_ac DESC LIMIT 1;
```

### Q1124 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** P.col_b decodes to player_api_id not player_name (col_c); PA.col_ac decodes to long_shots not attacking_work_rate (col_h) — also restructures the categorical ='high' filter into a numeric >AVG() threshold; join uses internal id not player_api_id

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.col_b
FROM Player P
JOIN Player_Attributes PA ON P.col_a = PA.col_a
WHERE PA.col_ac > (SELECT AVG(col_ac) FROM Player_Attributes)
```

### Q1130 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** T2.col_j decodes to buildUpPlayPassingClass, not chanceCreationPassingClass (col_m); adds a spurious col_k='High' filter (buildUpPlayPositioningClass) not in gold; T1.col_b decodes to team_api_id not team_short_name (col_e); join uses internal id not team_api_id

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T1.col_b 
FROM Team AS T1 
JOIN Team_Attributes AS T2 
ON T1.col_a = T2.col_a 
WHERE T2.col_j = 'Safe' AND T2.col_k = 'High';
```

### Q1133 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_b decodes to player_api_id, compared to the string 'Aaron' instead of player_name (col_c) with LIKE; col_c decodes to player_name, compared numerically >1990 instead of birthday (col_e)

**Gold SQL:**

```sql
SELECT COUNT(id) FROM Player WHERE STRFTIME('%Y', birthday) > '1990' AND player_name LIKE 'Aaron%'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player WHERE col_b = 'Aaron' AND col_c > 1990;
```

### Q1134 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_f/col_k decode to potential/finishing, not jumping (col_z); also drops the id=6/id=23 conditional SUM entirely, returning one row per Player_Attributes record instead of a single aggregated difference

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL:**

```sql
SELECT col_f - col_k AS jumping_score_difference FROM Player_Attributes
```

### Q1135 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ac decodes to long_shots, not preferred_foot (col_g); col_ad decodes to aggression, not potential (col_f); SELECT col_a (id) is correct

**Gold SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT col_a FROM Player_Attributes WHERE col_ac = 'right' ORDER BY col_ad ASC LIMIT 4
```

### Q1136 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_ac decodes to long_shots, not crossing (col_j); col_ah decodes to penalties, not preferred_foot (col_g); also COUNT(*) instead of COUNT(DISTINCT player_api_id)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE col_ac = (SELECT MAX(col_ac) FROM Player_Attributes) 
AND col_ah = 'left';
```

### Q1139 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_b/col_c decode to country_id/league_id, not home_team_goal (col_j)/away_team_goal (col_k); col_d (season) compared to 'Belgian Jupiler League' instead of joining League.name (no join present); col_a (Match.id) used as the date filter instead of date (col_f)

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT col_b, col_c 
FROM Match 
WHERE col_a = '2008-09-24' AND col_d = 'Belgian Jupiler League';
```

### Q1141 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a returns id not buildUpPlaySpeedClass (col_f); col_b (team_fifa_api_id) compared to 'KSV Cercle Brugge' instead of joining Team.team_long_name (no join present); col_c (team_api_id) filtered against speed-class labels — a spurious extra condition not in gold

**Gold SQL:**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL:**

```sql
SELECT DISTINCT col_a FROM Team_Attributes WHERE col_b = 'KSV Cercle Brugge' AND col_c IN ('slow', 'balanced', 'fast')
```

### Q1144 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a/col_b decode to id/player_fifa_api_id, not finishing (col_k)/curve (col_p); the max-value subquery uses col_c (player_api_id) on Player_Attributes instead of weight on Player (no join present)

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT col_a, col_b 
FROM Player_Attributes 
WHERE col_c = (SELECT MAX(col_c) FROM Player_Attributes);
```

### Q1145 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** M.col_a (Match.id) used as a season/date-range filter instead of season (col_d); comparing an integer id to date-range strings won't select the right matches

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT L.col_b, COUNT(*) AS game_count
FROM Match M
JOIN League L ON M.col_c = L.col_a
WHERE M.col_a BETWEEN '2015-08-01' AND '2016-07-31'
GROUP BY L.col_b
ORDER BY game_count DESC
LIMIT 4;
```

### Q1146 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** T2.col_b decodes to team_api_id not team_long_name (col_d); join uses Match.match_api_id (col_g) = Team.id (col_a) instead of away_team_api_id (col_i) = team_api_id (col_b)

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.col_b 
FROM Match AS T1 
JOIN Team AS T2 ON T1.col_g = T2.col_a 
ORDER BY T1.col_k DESC 
LIMIT 1;
```

### Q1147 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_a returns Player_Attributes.id, not player_name (needs a Player join, none present); col_ac decodes to long_shots not overall_rating (col_e); also collapses gold's exact-equality-to-MAX (which returns all ties) into ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT col_a FROM Player_Attributes ORDER BY col_ac DESC LIMIT 1
```

### Q1148 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** col_m (short_passing) used as a height filter instead of joining Player.height (no join present); col_n decodes to volleys, not overall_rating (col_e); denominator also counts all rows instead of just height<180 rows

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_m < 180 AND col_n > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player_Attributes;
```

---

## financial (30 failures)

### Q89 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unneeded client hop (account.district_id=client.client_id, a wrong key) between account and district instead of gold's direct district-account join; A3 lands on district.A10 (col_j), and frequency carries a translated/invented value instead of the real code.

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(*)
FROM account
JOIN client ON account.col_b = client.col_a
JOIN district ON client.col_d = district.col_a
WHERE district.col_j = 'East Bohemia'
AND account.col_c = 'issuance after transaction';
```

### Q92 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's gender='F' filter lives only on client; predicted queries district alone, filtering A5 (col_e) instead of joining client.gender, and A11 lands on A6 (col_f).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T2.district_id)  FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' AND T2.A11 BETWEEN 6000 AND 10000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM district 
WHERE col_e = 'F' AND col_f BETWEEN 6000 AND 10000;
```

### Q93 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** client.col_e is referenced but client has only 4 columns (col_a-col_d), so the query fails with 'no such column: client.col_e'; also joined via birth_date=district_id (client.col_c=district.col_a) instead of district_id=district_id.

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM client 
JOIN district ON client.col_c = district.col_a 
WHERE client.col_d = 'M' 
AND district.col_j = 'North Bohemia' 
AND client.col_e > 8000;
```

### Q94 (challenging, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** account.col_e is referenced (GROUP BY col_b, AVG(col_e)) but account has only 4 columns (col_a-col_d), so the query fails with 'no such column: col_e'; gender also lands on account/client.frequency (col_c) instead of client.gender.

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT col_a FROM client WHERE col_c = 'F' ORDER BY col_d ASC LIMIT 1) AS oldest_female_account,
    (SELECT MAX(avg_salary) - MIN(avg_salary) FROM 
        (SELECT AVG(col_e) AS avg_salary FROM account GROUP BY col_b)) AS salary_gap;
```

### Q95 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's account-client bridge goes through disp; predicted joins account directly to client via district_id=client_id (a.col_b=c.col_a, wrong key), and district.A13 (col_m) replaces A11 in the ordering -- disp missing entirely.

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT a.col_a 
FROM account a 
JOIN client c ON a.col_b = c.col_a 
JOIN district d ON c.col_d = d.col_a 
GROUP BY a.col_a 
ORDER BY c.col_c ASC, AVG(d.col_m) DESC 
LIMIT 1;
```

### Q98 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (account, loan) but joined via account_id=loan_id (a.col_a=l.col_a) instead of account_id=account_id; the year filter lands on loan.duration (col_e), frequency lands on loan.date (col_c), and ORDER BY lands on status (col_g) instead of amount.

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.col_a, a.col_b, a.col_c, a.col_d
FROM account a
JOIN loan l ON a.col_a = l.col_a
WHERE l.col_e LIKE '1997%' AND l.col_c = 'W'
ORDER BY l.col_g ASC
LIMIT 1;
```

### Q99 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (account, loan) but joined via account_id=loan_id (a.col_a=l.col_a) instead of account_id=account_id; the account.date filter lands on frequency (col_c), and the amount-based MAX subquery uses status (col_g) instead of amount.

**Gold SQL:**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.col_a, a.col_b, a.col_c, a.col_d
FROM account a
JOIN loan l ON a.col_a = l.col_a
WHERE l.col_e > 12 AND a.col_c = '1993' AND l.col_g = (SELECT MAX(col_g) FROM loan WHERE col_e > 12 AND col_a IN (SELECT col_a FROM account WHERE col_c = '1993'))
```

### Q100 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs only district JOIN client; predicted adds two unneeded tables (account, disp) via wrong keys (account.account_id=disp.client_id, disp.account_id=client.client_id), and gender/birth_date/A2 all land on the wrong client/district columns.

**Gold SQL:**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL:**

```sql
SELECT COUNT(*)
FROM account
JOIN disp ON account.col_a = disp.col_b
JOIN client ON disp.col_c = client.col_a
JOIN district ON client.col_d = district.col_a
WHERE client.col_c = 'F' AND client.col_b < '1950-01-01' AND district.col_j = 'Sokolov';
```

### Q112 (simple, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** c.col_e (client) is referenced for the birth_date filter but client has only 4 columns (col_a-col_d), so the query fails with 'no such column: c.col_e'; the client-account-district chain is also joined via wrong keys throughout (client_id=district_id, frequency=district_id).

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
SELECT d.col_b 
FROM client c 
JOIN account a ON c.col_a = a.col_b 
JOIN district d ON a.col_c = d.col_a 
WHERE c.col_d = 'F' AND c.col_e = '1976-01-29';
```

### Q115 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** client and district are correctly joined (district_id=district_id) but A3='south Bohemia' lands on district.A10 (col_j), the GROUP BY/ORDER BY A4 lands on A11 (col_k), and gender='M' lands on client.birth_date (col_c).

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN client.col_c = 'M' THEN 1 ELSE 0 END) * 100.0 / COUNT(client.col_a)) AS male_percentage
FROM 
    client
JOIN 
    district ON client.col_d = district.col_a
WHERE 
    district.col_j = 'South Bohemia'
ORDER BY 
    district.col_k DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs loan JOIN account JOIN trans (trans holds the balance figures); predicted substitutes an unneeded client table and drops trans entirely, joining client.client_id to both loan.account_id and account.district_id (both wrong keys).

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT (MAX(T2.col_c) - MIN(T2.col_c)) / MIN(T2.col_c) AS increase_rate
FROM client AS T1
JOIN loan AS T3 ON T1.col_a = T3.col_b
JOIN account AS T2 ON T1.col_a = T2.col_b
WHERE T3.col_d = 'A' AND T3.col_c = '1993-07-05'
AND T2.col_d BETWEEN '1993-03-22' AND '1998-12-27';
```

### Q117 (moderate, aggregate) -- **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** loan.status (col_g) is the correct column (compared to the nonsensical numeric 0 instead of 'A'), but the amount-weighted SUM(amount)/SUM(amount) ratio gold computes is replaced with an unweighted COUNT(*)/COUNT(*) ratio -- amount is never referenced at all.

**Gold SQL:**

```sql
SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan
```

**Predicted SQL:**

```sql
SELECT (SUM(CASE WHEN col_g = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage_paid
FROM loan;
```

### Q118 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (loan) and status (col_g) is the right column (compared to 'A' instead of 'C'), but the amount<100000 filter lands on date (col_c) instead of amount (col_d).

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN col_g = 'A' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage_running
FROM 
    loan
WHERE 
    col_c < 100000;
```

### Q125 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs loan JOIN account JOIN district (3 tables); predicted inserts disp twice and client via a chain of wrong keys (loan_id=account_id, account_id=disp_id, client_id=disp_id, disp.account_id=district_id), and A12/A13 land on A15/A16 (col_o/col_p).

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.col_p - d.col_o AS unemployment_rate_increment
FROM loan l
JOIN account a ON l.col_a = a.col_a
JOIN disp d1 ON a.col_a = d1.col_a
JOIN client c ON d1.col_b = c.col_a
JOIN disp d2 ON c.col_a = d2.col_a
JOIN district d ON d2.col_c = d.col_a
WHERE l.col_g IS NULL AND l.col_e < 0;
```

### Q128 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** client and district are correctly joined (district_id=district_id) but gender='F' lands on client.birth_date (col_c), and SELECT returns district_id instead of A2 (col_b).

**Gold SQL:**

```sql
SELECT T2.A2 FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' GROUP BY T2.district_id, T2.A2 ORDER BY COUNT(T1.client_id) DESC LIMIT 9
```

**Predicted SQL:**

```sql
SELECT d.col_a, COUNT(c.col_a) AS female_client_count
FROM district d
JOIN client c ON d.col_a = c.col_d
WHERE c.col_c = 'F'
GROUP BY d.col_a
ORDER BY female_client_count DESC
LIMIT 9;
```

### Q129 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs only district JOIN account JOIN trans; predicted inserts two unneeded tables (client, disp) and joins disp-account and account-trans via wrong keys (disp_id=account_id, account_id=trans_id), with type/date/amount all landing on the wrong trans columns.

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT d.col_b 
FROM district d 
JOIN client c ON d.col_a = c.col_d 
JOIN disp dp ON c.col_a = dp.col_b 
JOIN account a ON dp.col_a = a.col_a 
JOIN trans t ON a.col_a = t.col_a 
WHERE t.col_c = 'W' AND t.col_g BETWEEN '1996-01-01' AND '1996-01-31' 
GROUP BY d.col_b 
ORDER BY SUM(t.col_j) DESC 
LIMIT 10;
```

### Q136 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's frequency='POPLATEK MESICNE' filter lives only on account; predicted queries loan alone, filtering duration (col_e) instead of amount and status (col_g)='M' instead of joining account.frequency -- account missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM loan 
WHERE col_c >= '1995-01-01' AND col_c <= '1997-12-31' 
AND col_e >= 250000 
AND col_g = 'M';
```

### Q137 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's status IN ('C','D') filter lives only on loan; predicted queries account alone (district_id=1 is correctly resolved, col_b), dropping the loan join and its status filter entirely.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM account 
WHERE col_b = '1';
```

### Q138 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** The client-district relationship is replaced with a nonsensical IN-subquery comparing client.client_id to district.district_id (nonsensical bridging, col_a to col_a) filtered on A10=1995 (col_j) instead of matching A15 (col_o); gender='M' also lands on client.birth_date (col_c).

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A15 = (SELECT T3.A15 FROM district AS T3 ORDER BY T3.A15 DESC LIMIT 1, 1)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM client 
WHERE col_c = 'M' 
AND col_a IN (
    SELECT col_a 
    FROM district 
    WHERE col_j = 1995 
    ORDER BY col_k DESC 
    LIMIT 1 OFFSET 1
);
```

### Q145 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (account, trans) but joined via account_id=trans_id (T1.col_a=T2.col_a) instead of account_id=account_id; the amount comparison lands on trans.account (col_j) instead of amount, and the operation='VYBER KARTOU' filter is dropped entirely.

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.col_a 
FROM account AS T1 
JOIN trans AS T2 ON T1.col_a = T2.col_a 
WHERE T2.col_j < (SELECT AVG(col_j) FROM trans WHERE strftime('%Y', col_c) = '1998') 
AND strftime('%Y', T2.col_c) = '1998';
```

### Q149 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs district JOIN account JOIN disp (disp holds the type column); predicted substitutes an unneeded client table and drops disp entirely, replacing the type<>'OWNER' filter with a nonsensical account.frequency NOT IN loan.account_id check.

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
SELECT DISTINCT a.col_c 
FROM account a 
JOIN client c ON a.col_b = c.col_a 
JOIN district d ON c.col_d = d.col_a 
WHERE a.col_c NOT IN (SELECT l.col_b FROM loan l) 
AND d.col_k BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (district) but A15 lands on A10 (col_j) in both the filter and the AVG target; the account-district bridge subquery also compares district_id to account.frequency (col_c) instead of account.district_id.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(col_j) 
FROM district 
WHERE col_j > 4000 AND col_a IN (
    SELECT col_c 
    FROM account 
    WHERE strftime('%Y', col_d) >= '1997'
)
```

### Q159 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs client JOIN disp JOIN account JOIN trans (4 tables); predicted queries trans alone bridged to disp via a nonsensical trans_id=disp_id IN-subquery, with client and account both missing and operation/client_id landing on the wrong trans/disp columns.

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT *
FROM trans
WHERE col_b = 'W' AND col_c = 'cash' AND col_a IN (
    SELECT col_a
    FROM disp
    WHERE col_c = 'OWNER' AND col_d = 3356
);
```

### Q168 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** client and district are correctly joined (district_id=district_id) but gender lands on client.birth_date (col_c) compared to the invalid code 'W', and the A11>10000 filter is moved into a HAVING on district.A10 (col_j) instead of a WHERE on A11.

**Gold SQL:**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN client.col_c = 'W' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(client.col_a) AS percentage_women
FROM 
    client
JOIN 
    district ON client.col_d = district.col_a
GROUP BY 
    district.col_a
HAVING 
    AVG(district.col_j) > 10000;
```

### Q169 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Uses YEAR(...), which is not a SQLite function (only strftime is supported), so the query fails with 'no such function: YEAR'.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN YEAR(col_e) = 1997 THEN col_c ELSE 0 END) - SUM(CASE WHEN YEAR(col_e) = 1996 THEN col_c ELSE 0 END)) / 
    SUM(CASE WHEN YEAR(col_e) = 1996 THEN col_c ELSE 0 END) AS growth_rate
FROM 
    loan
JOIN 
    account ON loan.col_a = account.col_a
JOIN 
    disp ON account.col_a = disp.col_a
JOIN 
    client ON disp.col_b = client.col_a
WHERE 
    client.col_d = 'M'
    AND YEAR(loan.col_e) IN (1996, 1997);
```

### Q173 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs account JOIN a per-(account,k_symbol) SUM(amount) aggregate over "order"; predicted queries trans alone -- both the order table and account are missing, with k_symbol/total_amount landing on trans.date/operation.

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS statement_requests, SUM(col_e) AS total_debit_amount
FROM trans
WHERE col_b = '3' AND col_c = 'AS' AND col_e = 3539;
```

### Q186 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_c' -- both joined tables (client, disp) have a real column at position c (birth_date vs account_id), and the unqualified bare col_c in the gender CASE doesn't disambiguate; account (needed for the frequency filter) is also missing entirely.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM client 
JOIN disp ON client.col_a = disp.col_b 
WHERE disp.col_c = 'OWNER';
```

### Q189 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs client JOIN district JOIN account JOIN disp (4 tables); predicted joins only account+client via district_id=client_id (a wrong key), dropping district and disp entirely and ordering by client.birth_date DESC (wrong direction) instead of ASC.

**Gold SQL:**

```sql
SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id  WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.col_a 
FROM account AS T1 
JOIN client AS T2 ON T1.col_b = T2.col_a 
WHERE T2.col_d = 'F' 
ORDER BY T2.col_c DESC, T1.col_d ASC 
LIMIT 1;
```

### Q192 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs account (for frequency) JOIN loan; predicted substitutes trans for account (same-size 2-table join) via a nonsensical loan_id=trans_id key, leaving status/amount misresolved to loan.date/loan.status.

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(loan.col_g) 
FROM loan 
JOIN trans ON loan.col_a = trans.col_a 
WHERE loan.col_c = 'A' AND loan.col_d = 'B';
```

### Q194 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 3 tables as gold (client, disp, card) but both join keys are wrong (client_id=disp_id, disp.client_id=card.disp_id); card.type lands on the wrong code 'HC' instead of 'gold', and disp.type='OWNER' is replaced with client.birth_date='A'.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.col_a, c.col_b 
FROM client c 
JOIN disp d ON c.col_a = d.col_a 
JOIN card ca ON d.col_b = ca.col_b 
WHERE ca.col_c = 'HC' AND c.col_c = 'A';
```

---

## formula_1 (66 failures)

### Q846 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs qualifying JOIN drivers (raceId=20, ORDER BY q1 DESC LIMIT 5); predicted queries results alone, filtering points='Eliminated' (col_j) and laps=1 (col_k) -- neither needed table present, no ordering/limit either.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM results 
WHERE col_b = 20 AND col_j = 'Eliminated' AND col_k = 1;
```

### Q847 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs qualifying JOIN drivers (2 tables); predicted joins drivers+results+races+qualifying (4 tables, 2 extra) via broken keys throughout (driverId=raceId, driverId=qualifyId), and orders by qualifying.number instead of q2.

**Gold SQL:**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_c 
FROM drivers d 
JOIN results r ON d.col_a = r.col_b 
JOIN races ra ON r.col_c = ra.col_a 
JOIN qualifying q ON r.col_c = q.col_a AND r.col_b = q.col_b 
WHERE ra.col_a = 19 AND q.col_d = 2 
ORDER BY q.col_e ASC 
LIMIT 1;
```

### Q850 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's country='Germany' filter lives only on circuits; predicted queries races alone, filtering round (col_c) and selecting year (col_b) instead of name -- circuits missing entirely.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT col_b FROM races WHERE col_c = 'Germany'
```

### Q854 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's races.name filter is needed to locate the circuit; predicted queries circuits alone, filtering circuitRef (col_b) against the race name and selecting name/location instead of lat/lng -- races missing entirely.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT col_c, col_d FROM circuits WHERE col_b = 'Australian Grand Prix'
```

### Q857 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Same pattern as the Abu Dhabi Grand Prix lookup: races missing entirely, predicted filters circuits.circuitRef (col_b) against the race name and selects name (col_c) instead of lat.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT col_c FROM circuits WHERE col_b = 'Abu Dhabi Grand Prix'
```

### Q859 (simple, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_g' -- both joined tables (qualifying, drivers) have a real column at position g (q1 vs nationality), and the unqualified bare col_g reference doesn't disambiguate.

**Gold SQL:**

```sql
SELECT T1.q1 FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 354 AND T2.forename = 'Bruno' AND T2.surname = 'Senna'
```

**Predicted SQL:**

```sql
SELECT col_g 
FROM qualifying 
JOIN drivers ON qualifying.col_b = drivers.col_a 
WHERE drivers.col_b = 'Bruno Senna' AND qualifying.col_a = 354;
```

### Q861 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's drivers.number (the SELECT target) requires joining drivers; predicted queries qualifying alone, returning qualifyId (col_a) and filtering driverId/constructorId (col_c/col_d) instead of q3 -- drivers missing entirely.

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM qualifying 
WHERE col_b = '903' AND col_c = 'Q3' AND col_d = '0:01:54';
```

### Q862 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** races and results are correctly joined (raceId=raceId) but the name/year filters land on round (col_c) and circuitId (col_d), and the time IS NULL check becomes rank!=1 (col_o); gold's drivers join is vestigial (used only for COUNT) so its absence isn't the actual cause.

**Gold SQL:**

```sql
SELECT COUNT(T3.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T1.year = 2007 AND T1.name = 'Bahrain Grand Prix' AND T2.time IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
JOIN races ON results.col_b = races.col_a 
WHERE races.col_c = 'Bahrain Grand Prix' AND races.col_d = 2007 AND results.col_o != 1;
```

### Q865 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (drivers, results) but joined via driverId=raceId (d.col_a=r.col_b) instead of driverId=driverId; SELECT and ORDER BY also land on driverRef/number/code instead of forename/surname/dob.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c 
FROM drivers d 
JOIN results r ON d.col_a = r.col_b 
WHERE r.col_c = 592 
ORDER BY d.col_d DESC 
LIMIT 1;
```

### Q866 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs lapTimes JOIN drivers (2 tables); predicted joins drivers+results+races+lapTimes (4 tables, 2 extra) via broken keys (driverId=raceId, driverId=lap), and selects driverRef/number/code instead of forename/surname/url.

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c, d.col_d
FROM drivers d
JOIN results r ON d.col_a = r.col_b
JOIN races ra ON r.col_c = ra.col_a
JOIN laptimes lt ON r.col_a = lt.col_b AND r.col_c = lt.col_c
WHERE ra.col_a = 161 AND lt.col_d = '0:01:27';
```

### Q868 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Same pattern as the Germany/Abu Dhabi circuit lookups: races missing entirely, predicted filters circuits.circuitRef (col_b) against the race name instead of joining races.name.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT col_c, col_d FROM circuits WHERE col_b = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs constructorResults (per-race points) JOIN constructors; predicted substitutes constructorStandings (a same-role per-race-per-constructor table) joined via constructorId=raceId (wrong key), and selects constructors.name (col_c) instead of url.

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.col_c 
FROM constructors c 
JOIN constructorStandings cs ON c.col_a = cs.col_b 
WHERE cs.col_d = (SELECT MAX(col_d) FROM constructorStandings WHERE col_e = 9);
```

### Q872 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (drivers, qualifying) but joined via driverId=raceId (d.col_a=q.col_b) instead of driverId=driverId; WHERE filters qualifyId=45 and q1 instead of raceId=45 and q3, and SELECT returns number instead of code.

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT d.col_c 
FROM drivers d 
JOIN qualifying q ON d.col_a = q.col_b 
WHERE q.col_a = 45 AND q.col_g = '0:01:33';
```

### Q875 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** seasons.url (col_b) is correctly selected, but the bridge back to races uses races.round (col_c) instead of races.year (col_b) to match seasons.year for raceId=901.

**Gold SQL:**

```sql
SELECT T2.url FROM races AS T1 INNER JOIN seasons AS T2 ON T2.year = T1.year WHERE T1.raceId = 901
```

**Predicted SQL:**

```sql
SELECT col_b FROM seasons WHERE col_a = (SELECT col_c FROM races WHERE col_a = 901)
```

### Q877 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** The IN-subquery bridges drivers to results by comparing driverId to raceId values (col_a to col_b) instead of driverId=driverId with a raceId=872 filter; milliseconds=1 (col_m) also replaces the time IS NOT NULL check, and SELECT/ORDER BY land on number/code instead of forename/surname/dob.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_c 
FROM drivers 
WHERE col_a IN (
    SELECT col_b 
    FROM results 
    WHERE col_a = 872 AND col_m = 1
) 
ORDER BY col_d ASC 
LIMIT 1;
```

### Q879 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs drivers JOIN results (2 tables) ordered by fastestLapSpeed; predicted joins drivers+results+lapTimes (extra table) via driverId=raceId (wrong key), and orders by lapTimes.position instead of results.fastestLapSpeed.

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_g 
FROM drivers d 
JOIN results r ON d.col_a = r.col_b 
JOIN lapTimes lt ON r.col_a = lt.col_a 
WHERE lt.col_d = (SELECT MIN(col_d) FROM lapTimes)
```

### Q880 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs drivers (for the forename/surname filter) JOIN results; predicted drops drivers entirely, faking the name filter as results.driverId='Paul di Resta' (col_c), and substitutes lapTimes.time for results.fastestLapSpeed via a broken resultId/raceId/driverId key mix-up.

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
    (100 * (fastest_lap_speed_853 - fastest_lap_speed_next) / fastest_lap_speed_next) AS percentage_faster
FROM 
    (SELECT 
        MIN(lapTimes.col_e) AS fastest_lap_speed_853
     FROM 
        results
     JOIN 
        lapTimes ON results.col_a = lapTimes.col_a AND results.col_b = lapTimes.col_b
     WHERE 
        results.col_c = 'Paul di Resta' AND results.col_d = 853) AS race_853
JOIN 
    (SELECT 
        MIN(lapTimes.col_e) AS fastest_lap_speed_next
     FROM 
        results
     JOIN 
        lapTimes ON results.col_a = lapTimes.col_a AND results.col_b = lapTimes.col_b
     WHERE 
        results.col_c = 'Paul di Resta' AND results.col_d > 853
     ORDER BY 
        results.col_d ASC
     LIMIT 1) AS next_race;
```

### Q881 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs races JOIN results (2 tables) filtered by date; predicted joins drivers+results+races (extra table, broken driverId=raceId key), filters races.circuitId (col_d) against the date string instead of races.date, and adds an unwarranted GROUP BY.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT 
    d.col_a AS driver_id, 
    d.col_b AS driver_name, 
    COUNT(r.col_a) AS total_races, 
    SUM(CASE WHEN r.col_j = 1 THEN 1 ELSE 0 END) AS completed_races, 
    CAST(SUM(CASE WHEN r.col_j = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(r.col_a) AS completion_rate
FROM 
    drivers d
JOIN 
    results r ON d.col_a = r.col_b
JOIN 
    races ra ON r.col_c = ra.col_a
WHERE 
    ra.col_d = '1983-07-16'
GROUP BY 
    d.col_a, d.col_b;
```

### Q884 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (races) but the earliest-date subquery filters round (col_c) instead of date, and SELECT returns year (col_b) instead of name.

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM races 
WHERE col_c = (SELECT MIN(col_c) FROM races)
```

### Q892 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (drivers, results) but joined via driverId=raceId (d.col_a=r.col_b) instead of driverId=driverId; SUM(points) (col_j) is the one correctly-resolved column, but SELECT still returns driverRef/number instead of forename/surname.

**Gold SQL:**

```sql
SELECT d.`forename`, d.`surname`, SUM(r.`points`) AS total_points
FROM `results` r
JOIN `drivers` d ON d.`driverId` = r.`driverId`
GROUP BY r.`driverId`
ORDER BY total_points DESC
LIMIT 1;
```

**Predicted SQL:**

```sql
SELECT d.col_b AS first_name, d.col_c AS last_name, SUM(r.col_j) AS total_points
FROM drivers d
JOIN results r ON d.col_a = r.col_b
GROUP BY d.col_a
ORDER BY total_points DESC
LIMIT 1;
```

### Q894 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** drivers is correctly joined to lapTimes (driverId=driverId), but lapTimes is then joined to races via lap=raceId (lt.col_c=r.col_a) instead of raceId=raceId; SELECT/ORDER BY also return lapTimes.position and races.round instead of milliseconds and name.

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT lt.col_d AS lap_time, d.col_b AS driver_name, r.col_c AS race_name
FROM lapTimes lt
JOIN drivers d ON lt.col_b = d.col_a
JOIN races r ON lt.col_c = r.col_a
ORDER BY lt.col_d ASC
LIMIT 1;
```

### Q895 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs races JOIN lapTimes JOIN drivers (3 tables); predicted adds an unneeded results table and every join key is wrong (lapTimes.raceId=results.resultId, results.raceId=drivers.driverId, results.driverId=races.raceId), leaving a structurally nonsensical join chain.

**Gold SQL:**

```sql
SELECT AVG(T2.milliseconds) FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.year = 2009 AND T1.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT AVG(lapTimes.col_e) 
FROM lapTimes 
JOIN results ON lapTimes.col_a = results.col_a 
JOIN drivers ON results.col_b = drivers.col_a 
JOIN races ON results.col_c = races.col_a 
WHERE drivers.col_b = 'Lewis Hamilton' AND races.col_d = 'Malaysian Grand Prix' AND races.col_c = 2009;
```

### Q896 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_b' -- both tables in scope (results, circuits) have a real column at position b (raceId vs circuitRef), and the unqualified bare col_b/col_c references don't disambiguate; the table choice itself (results+circuits instead of races+driverStandings+drivers) is also wrong, but the query never gets past the ambiguity error.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_b = 'Hamilton' AND col_c = 1 THEN 0 ELSE 1 END) AS REAL) * 100 / COUNT(*) 
FROM results 
JOIN circuits ON results.col_a = circuits.col_a 
WHERE circuits.col_d >= 2010;
```

### Q897 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs drivers JOIN driverStandings (wins/points, a season-standings table); predicted substitutes results (a same-role per-race table) joined via driverId=raceId (wrong key), filtering points=1 (col_j) instead of wins>=1 and taking MAX(laps) instead of MAX(points).

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c, MAX(r.col_k)
FROM drivers d
JOIN results r ON d.col_a = r.col_b
WHERE r.col_j = 1
GROUP BY d.col_a
ORDER BY COUNT(r.col_j) DESC
LIMIT 1;
```

### Q898 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (drivers) but nationality='Japanese' lands on code (col_d), ORDER BY lands on number (col_c) instead of dob, and SELECT returns number/driverRef instead of forename/surname plus the computed age.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_c, col_b 
FROM drivers 
WHERE col_d = 'Japan' 
ORDER BY col_c ASC 
LIMIT 1;
```

### Q901 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (circuits, races) but joined via races.round=circuits.circuitId (ra.col_c=c.col_a) instead of races.circuitId=circuits.circuitId; the date filter lands on races.circuitId (col_d), and SELECT returns races.year instead of races.name.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name, T1.name, T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Predicted SQL:**

```sql
SELECT races.col_b, circuits.col_c, circuits.col_d 
FROM races 
JOIN circuits ON races.col_c = circuits.col_a 
WHERE races.col_d LIKE '2005-09-%';
```

### Q902 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs races JOIN driverStandings (position) JOIN drivers; predicted substitutes results (same-role per-race table) for driverStandings -- position<20 lands on results.constructorId (col_d), and SELECT returns raceId instead of races.name.

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT races.col_a 
FROM races 
JOIN results ON races.col_a = results.col_b 
JOIN drivers ON results.col_c = drivers.col_a 
WHERE drivers.col_b = 'Alex Yoong' AND results.col_d < 20;
```

### Q904 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs races JOIN lapTimes (ordered by milliseconds) JOIN drivers; predicted substitutes results+qualifying for lapTimes (which is entirely absent) and orders by qualifying.constructorId instead of any time-like column.

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT races.col_b, races.col_c 
FROM races 
JOIN results ON races.col_a = results.col_b 
JOIN drivers ON results.col_c = drivers.col_a 
JOIN qualifying ON results.col_b = qualifying.col_b AND results.col_c = qualifying.col_c 
WHERE drivers.col_b = 'Michael Schumacher' 
ORDER BY qualifying.col_d ASC 
LIMIT 1;
```

### Q906 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs races JOIN driverStandings JOIN drivers (3 tables); predicted uses only drivers+results (driverStandings and races both missing), joined via driverId=raceId (wrong key), and orders by results.points instead of races.year.

**Gold SQL:**

```sql
SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.col_b, T2.col_e 
FROM drivers AS T1 
JOIN results AS T2 ON T1.col_a = T2.col_b 
WHERE T1.col_c = 'Lewis Hamilton' 
ORDER BY T2.col_j ASC 
LIMIT 1;
```

### Q909 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's country='Germany' comparison needs circuits; predicted queries races alone, filtering races.year (col_b) against the race name and races.round (col_c) against 'Germany' -- circuits missing entirely.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c = 'Germany' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM races 
WHERE col_b = 'European Grand Prix';
```

### Q910 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (circuits) but the name filter lands on circuitRef (col_b), and SELECT returns name/location (col_c/col_d) instead of lat/lng.

**Gold SQL:**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Silverstone Circuit'
```

**Predicted SQL:**

```sql
SELECT col_c, col_d FROM circuits WHERE col_b = 'Silverstone Circuit'
```

### Q912 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (circuits) but the SELECT/WHERE columns are swapped relative to gold: filters circuitRef (col_b) against the name string and selects name (col_c) instead of filtering by name and selecting circuitRef.

**Gold SQL:**

```sql
SELECT circuitRef FROM circuits WHERE name = 'Marina Bay Street Circuit'
```

**Predicted SQL:**

```sql
SELECT col_c FROM circuits WHERE col_b = 'Marina Bay Street Circuit'
```

### Q915 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (drivers) but SELECT returns number (col_c) instead of nationality, and ORDER BY uses code (col_d) instead of dob.

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_c 
FROM drivers 
ORDER BY col_d ASC 
LIMIT 1;
```

### Q928 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 3 tables as gold (drivers, results, races) but both join keys are wrong (driverId=raceId, driverId=raceId), and every filter/select column is consequently misresolved (races.circuitId/name instead of name/year, results.points instead of position).

**Gold SQL:**

```sql
SELECT d.forename, d.surname, d.driverRef FROM drivers AS d JOIN results AS r ON d.driverId = r.driverId JOIN races AS ra ON r.raceId = ra.raceId WHERE ra.name = 'Canadian Grand Prix' AND ra.year = 2007 AND r.position = 1
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c, d.col_a 
FROM drivers d 
JOIN results r ON d.col_a = r.col_b 
JOIN races ra ON r.col_c = ra.col_a 
WHERE ra.col_d = 'Canada' AND ra.col_e = 2007 AND r.col_j = 1;
```

### Q930 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and joins are all correct (races, results, drivers with correct keys) but the name filter uses driverRef instead of forename+surname, ORDER BY uses constructorId instead of filtering rank=0, and SELECT returns raceId instead of name.

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT DISTINCT r.col_a
FROM races r
JOIN results res ON r.col_a = res.col_b
JOIN drivers d ON res.col_c = d.col_a
WHERE d.col_b = 'Lewis Hamilton'
ORDER BY res.col_d ASC
LIMIT 1;
```

### Q931 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_e' -- both tables in scope (lapTimes, races) have a real column at position e (time vs name); also substitutes lapTimes for results via a driverId=raceId join key, but the query never gets past the ambiguity error.

**Gold SQL:**

```sql
SELECT T2.fastestLapSpeed FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.name = 'Spanish Grand Prix' AND T1.year = 2009 AND T2.fastestLapSpeed IS NOT NULL ORDER BY T2.fastestLapSpeed DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(col_e) 
FROM lapTimes 
JOIN races ON lapTimes.col_b = races.col_a 
WHERE races.col_c = 'Spanish Grand Prix' AND races.col_d = 2009;
```

### Q933 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_d' -- both joined tables (drivers, results) have a real column at position d (code vs constructorId), and the unqualified bare col_d reference doesn't disambiguate.

**Gold SQL:**

```sql
SELECT T2.positionOrder FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.name = 'Chinese Grand Prix' AND T1.year = 2008
```

**Predicted SQL:**

```sql
SELECT col_d 
FROM results 
JOIN races ON results.col_b = races.col_a 
JOIN drivers ON results.col_c = drivers.col_a 
WHERE drivers.col_b = 'Lewis Hamilton' AND races.col_c = 'Chinese Grand Prix' AND races.col_a = 2008 
ORDER BY results.col_a DESC 
LIMIT 1;
```

### Q937 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** results and races are correctly joined (raceId=raceId) but the race-name filter lands on round (col_c) with a garbled literal, the year filter lands on circuitId (col_d), the position=2 filter is replaced with an ORDER BY/LIMIT/OFFSET substitute, and SELECT returns laps (col_k) instead of time.

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT r.col_k 
FROM results r 
JOIN races ra ON r.col_b = ra.col_a 
WHERE ra.col_c = 'AustChineseralian Grand Prix' AND ra.col_d = 2008 
ORDER BY r.col_c ASC 
LIMIT 1 OFFSET 1;
```

### Q940 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** results and races are correctly bridged on raceId but the name/year filters land on round (col_c) and circuitId (col_d) instead of name/year, COUNT uses resultId instead of driverId, and the time-not-null/HAVING logic is dropped entirely.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT col_a) 
FROM results 
WHERE col_b = (SELECT col_a FROM races WHERE col_c = 'Chinese Grand Prix' AND col_d = 2008);
```

### Q944 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** results and races are correctly joined (raceId=raceId) but the year/name filters land on round (col_c) and circuitId (col_d), and the percent-faster formula uses results.points (col_j) instead of milliseconds.

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    ((MAX(results.col_j) - MIN(results.col_j)) / MIN(results.col_j)) * 100 AS percentage_faster
FROM 
    results
JOIN 
    races ON results.col_b = races.col_a
WHERE 
    races.col_c = '1988' AND races.col_d = 'Australian Grand Prix';
```

### Q945 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (circuits) but location='Adelaide' lands on name (col_c), and country='Australia' lands on location (col_d).

**Gold SQL:**

```sql
SELECT COUNT(circuitId) FROM circuits WHERE location = 'Adelaide' AND country = 'Australia'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM circuits WHERE col_c = 'Adelaide' AND col_d = 'Australia';
```

### Q948 (simple, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_e' -- both joined tables (constructors, constructorStandings) have a real column at position e (url vs position); the join key (constructorId=raceId) is also wrong, but the query never gets past the ambiguity error.

**Gold SQL:**

```sql
SELECT MAX(T1.points) FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T2.nationality = 'British'
```

**Predicted SQL:**

```sql
SELECT MAX(col_e) 
FROM constructors 
JOIN constructorStandings ON constructors.col_a = constructorStandings.col_b 
WHERE constructors.col_c = 'British';
```

### Q950 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables match gold (constructorStandings, constructors) but the bridging/filter logic compares constructorId to raceId values, filters constructorId=291 instead of raceId=291 and points>0 instead of points=0, and SELECT returns constructorRef instead of name.

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM constructors 
WHERE col_a NOT IN (SELECT col_b FROM constructorStandings WHERE col_c = 291 AND col_d > 0)
```

### Q951 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs constructorResults (per-race points) JOIN constructors; predicted substitutes constructorStandings (a same-role table), grouping by raceId instead of constructorId and inverting the points/count condition (NOT IN with points>0 vs gold's points=0 with COUNT=2).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM constructors 
WHERE col_c = 'Japan' 
AND col_a NOT IN (
    SELECT col_b 
    FROM constructorStandings 
    GROUP BY col_b 
    HAVING SUM(col_d) > 0 
    AND COUNT(DISTINCT col_a) >= 2
);
```

### Q954 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 3 tables as gold (results, drivers, races) but both join keys are wrong (raceId=driverId, driverId=raceId); nationality lands on drivers.dob (col_g), the year range lands on races.circuitId (col_d), and the time-not-null check becomes points=1 (col_j).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN results.col_j = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS completion_percentage
FROM 
    results
JOIN 
    drivers ON results.col_b = drivers.col_a
JOIN 
    races ON results.col_c = races.col_a
WHERE 
    drivers.col_g = 'Japan' 
    AND races.col_d BETWEEN 2007 AND 2009;
```

### Q955 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a harmless vestigial seasons table (seasons.year=races.year is a valid 1:1 bridge) but the core races-results join uses races.raceId=results.driverId (r.col_a=res.col_c) instead of raceId=raceId; position=1 lands on points=1 (col_j), and AVG lands on laps (col_k) instead of milliseconds.

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT 
    seasons.col_a AS year, 
    AVG(results.col_k) AS avg_time_seconds
FROM 
    seasons
JOIN 
    races ON seasons.col_a = races.col_b
JOIN 
    results ON races.col_a = results.col_c
WHERE 
    seasons.col_a < 1975 AND results.col_j = 1
GROUP BY 
    seasons.col_a;
```

### Q959 (simple, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_e' -- both tables in scope (driverStandings, results) have a real column at position e (position vs number); the table choice (drivers+driverStandings instead of results+races) is also wrong, but the query never gets past the ambiguity error.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT MIN(col_e) AS fastest_lap_number
FROM results
JOIN drivers ON results.col_b = drivers.col_a
JOIN driverStandings ON drivers.col_a = driverStandings.col_b
WHERE driverStandings.col_c = 1 AND driverStandings.col_d = 2009;
```

### Q960 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs results JOIN races (fastestLapSpeed, name, year); predicted queries qualifying alone, filtering raceId/driverId (col_b/col_c) and averaging qualifying.number (col_e) -- neither needed table present.

**Gold SQL:**

```sql
SELECT AVG(T1.fastestLapSpeed) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T2.name = 'Spanish Grand Prix'
```

**Predicted SQL:**

```sql
SELECT AVG(col_e) FROM qualifying WHERE col_b = 'Spanish Grand Prix' AND col_c = 2009
```

### Q962 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 3 tables as gold (drivers, results, races) but both join keys are wrong (driverId=raceId, driverId=raceId); dob<1985 lands on drivers.number (col_c), and laps>50 lands on results.points=50 (col_j).

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN D.col_c < '1985' AND R.col_j = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM drivers D 
JOIN results R ON D.col_a = R.col_b 
JOIN races Ra ON R.col_c = Ra.col_a 
WHERE Ra.col_d BETWEEN 2000 AND 2005;
```

### Q963 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and join key are correct (drivers.driverId=lapTimes.driverId) but nationality='French' lands on drivers.number (col_c), and the computed-time<120 check lands on lapTimes.position compared to a time string (col_d) instead of lapTimes.time.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT drivers.col_a)
FROM drivers
JOIN laptimes ON drivers.col_a = laptimes.col_b
WHERE drivers.col_c = 'France' AND laptimes.col_d < '02:00.00';
```

### Q964 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (drivers) but nationality='American' lands on number (col_c), and SELECT returns driverId (col_a) instead of code.

**Gold SQL:**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL:**

```sql
SELECT col_a FROM drivers WHERE col_c = 'American'
```

### Q967 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (drivers) but nationality='Dutch' lands on number (col_c) compared to 'Netherlands', and ORDER BY uses code (col_d) ascending instead of JULIANDAY(dob) descending; the outer top-3 filter/count structure is also dropped.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM drivers 
WHERE col_c = 'Netherlands' 
ORDER BY col_d ASC 
LIMIT 3;
```

### Q971 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (drivers) and SELECT correctly returns driverRef (col_b), but nationality='German' lands on number (col_c) compared to 'Germany', and ORDER BY uses code (col_d) instead of JULIANDAY(dob).

**Gold SQL:**

```sql
SELECT driverRef FROM drivers WHERE nationality = 'German' ORDER BY JULIANDAY(dob) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_b FROM drivers WHERE col_c = 'Germany' ORDER BY col_d ASC LIMIT 1
```

### Q972 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs results JOIN drivers (2 tables); predicted adds an unneeded lapTimes table and every join key is wrong (driverId=resultId, resultId=raceId, raceId=driverId), and checks lapTimes.position instead of results.fastestLapTime not null.

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.col_a, d.col_b
FROM drivers d
JOIN results r ON d.col_a = r.col_a
JOIN lapTimes lt ON r.col_a = lt.col_a AND r.col_b = lt.col_b
WHERE d.col_c = '1971' AND lt.col_d = (SELECT MIN(col_d) FROM lapTimes)
```

### Q977 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (results) but the raceId range lands on resultId (col_a), and statusId=2 lands on fastestLapTime='Disqualified' (col_p); the conditional time-not-null SUM is also replaced with a plain COUNT(*).

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
WHERE col_a BETWEEN 50 AND 100 AND col_p = 'Disqualified';
```

### Q978 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (circuits) and country='Austria' (col_e) is correctly resolved, but SELECT returns name/location (col_c/col_d) instead of location/lat/lng.

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT col_c, col_d FROM circuits WHERE col_e = 'Austria'
```

### Q981 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs qualifying JOIN drivers JOIN races (3 tables); predicted substitutes results+seasons for qualifying (which is entirely absent) via broken keys (driverId=raceId, driverId=raceId, races.name=seasons.year), and never surfaces races.date/time.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MIN(r.col_c) AS race_date, 
    r.col_d AS race_time, 
    d.col_b AS driver_name, 
    s.col_a AS year
FROM 
    drivers d
JOIN 
    results res ON d.col_a = res.col_b
JOIN 
    races r ON res.col_c = r.col_a
JOIN 
    seasons s ON r.col_e = s.col_a
WHERE 
    d.col_c = (SELECT MIN(col_c) FROM drivers)
ORDER BY 
    r.col_c ASC
LIMIT 1;
```

### Q988 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and join key are correct (drivers.driverId=pitStops.driverId) but the dob range lands on drivers.number (col_c) with the nationality='German' filter dropped entirely, AVG lands on pitStops.time (col_e) instead of duration, and SELECT returns driverRef instead of forename/surname.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.col_b AS driver_name
FROM drivers d
JOIN pitStops p ON d.col_a = p.col_b
WHERE d.col_c BETWEEN '1980' AND '1985'
GROUP BY d.col_a
ORDER BY AVG(p.col_e) ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** results and races are correctly joined (raceId=raceId) but the race-name filter lands on round (col_c) compared to 'Canada', the year filter lands on circuitId (col_d), and SELECT returns laps (col_k) instead of time.

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT col_k 
FROM results 
JOIN races ON results.col_b = races.col_a 
WHERE races.col_c = 'Canada' AND races.col_d = 2008 
ORDER BY results.col_e ASC 
LIMIT 1;
```

### Q990 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs results (per-race data) JOIN races JOIN constructors; predicted substitutes constructorStandings (a same-role table) for results, joined via constructorId=raceId and points=raceId (both wrong keys), and the race-name filter lands on races.round instead of name.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT c.col_b, c.col_c 
FROM constructors c 
JOIN constructorStandings cs ON c.col_a = cs.col_b 
JOIN races r ON cs.col_d = r.col_a 
WHERE r.col_c = 'Singapore Grand Prix' AND r.col_b = 2009 AND cs.col_e = (SELECT MAX(col_e) FROM constructorStandings WHERE col_d = r.col_a);
```

### Q994 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs constructorResults (per-race points) JOIN constructors JOIN races; predicted substitutes constructorStandings (a same-role table), joined via raceId=constructorId and constructorId=raceId (both wrong keys), and the Monaco/year filters land on races.circuitId/name instead of name/year.

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    c.col_b AS constructor_name, 
    c.col_c AS constructor_nationality, 
    SUM(cr.col_d) AS total_points
FROM 
    constructorStandings cr
JOIN 
    constructors c ON cr.col_b = c.col_a
JOIN 
    races r ON cr.col_c = r.col_a
WHERE 
    r.col_d = 'Monaco' AND 
    r.col_e BETWEEN 1980 AND 2010
GROUP BY 
    c.col_a
ORDER BY 
    total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs qualifying (q3 not null) JOIN drivers JOIN races, with a circuits subquery for the venue; predicted substitutes results for qualifying (which is entirely absent) via a driverId=raceId join key, though the races-circuits join itself is correct.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c 
FROM drivers d 
JOIN results r ON d.col_a = r.col_b 
JOIN races ra ON r.col_c = ra.col_a 
JOIN circuits c ON ra.col_d = c.col_a 
WHERE r.col_g = 1 AND ra.col_e = 3 AND c.col_b = 'Marina Bay Street Circuit' AND ra.col_f = 2008;
```

### Q1002 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs drivers JOIN driverStandings JOIN races (3 tables, for nationality and race name); predicted substitutes results for driverStandings (missing nationality path) joined via driverId=raceId (wrong key), and SELECT returns driverRef/number/circuitId instead of forename/surname/nationality/name.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c, r.col_d
FROM drivers d
JOIN results res ON d.col_a = res.col_b
JOIN races r ON res.col_c = r.col_a
WHERE d.col_g = (SELECT MIN(col_g) FROM drivers)
```

### Q1003 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's statusId=3 filter requires joining status; predicted queries results+races alone (status missing entirely), replacing it with a self-referential rank-based subquery that drops the statusId filter altogether.

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
JOIN races ON results.col_b = races.col_a 
WHERE races.col_c = 'Canadian Grand Prix' 
AND results.col_o = (SELECT results.col_o 
                     FROM results 
                     JOIN races ON results.col_b = races.col_a 
                     WHERE races.col_c = 'Canadian Grand Prix' 
                     GROUP BY results.col_o 
                     ORDER BY COUNT(results.col_o) DESC 
                     LIMIT 1);
```

### Q1011 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs drivers JOIN a per-driver MIN(milliseconds) aggregate over lapTimes (2 tables); predicted adds an unneeded results table and joins lapTimes via resultId=raceId (wrong key) instead of driverId=driverId, ordering by lapTimes.time instead of milliseconds.

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c
FROM drivers d
JOIN results r ON d.col_a = r.col_b
JOIN laptimes lt ON r.col_a = lt.col_a
ORDER BY lt.col_e ASC
LIMIT 20;
```

### Q1014 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_e' -- both tables in scope (circuits, results) have a real column at position e (country vs number); the circuits-races join key (circuitId=round) is also wrong, but the query never gets past the ambiguity error.

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(col_e) AS lap_record
FROM circuits
JOIN races ON circuits.col_a = races.col_c
JOIN results ON races.col_a = results.col_b
WHERE circuits.col_d = 'Italy';
```

---

## student_club (46 failures)

### Q1312 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** join uses member.last_name (col_c) instead of link_to_major (col_i) against major.major_id; WHERE also compares first_name alone to full name string 'Angela Sanders'

**Gold SQL:**

```sql
SELECT T2.major_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.first_name = 'Angela' AND T1.last_name = 'Sanders'
```

**Predicted SQL:**

```sql
SELECT major.col_b 
FROM member 
JOIN major ON member.col_c = major.col_a 
WHERE member.col_b = 'Angela Sanders';
```

### Q1317 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** member.col_g (phone) and col_h (zip) used instead of col_f (t_shirt_size) for the 'Medium' filter

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM event 
JOIN attendance ON event.col_a = attendance.col_a 
JOIN member ON attendance.col_b = member.col_a 
WHERE event.col_b = 'Women''s Soccer' AND member.col_g = 'T-shirt' AND member.col_h = 'Medium';
```

### Q1322 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** spurious WHERE on event.event_date (col_c) = 'Student_Club' zeroes out all rows; join key (attendance.col_b=link_to_member instead of col_a) and the type='Meeting' filter relocated into HAVING are secondary

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM event 
JOIN attendance ON event.col_a = attendance.col_b 
WHERE event.col_c = 'Student_Club' 
GROUP BY event.col_a 
HAVING COUNT(attendance.col_a) > 10 
AND event.col_d = 'meeting';
```

### Q1323 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters event.event_date (col_c) != 'fundraiser' instead of type (col_d); also entirely drops GROUP BY/HAVING, filtering by attendance.link_to_member (col_b) > 20 instead of COUNT(*) > 20

**Gold SQL:**

```sql
SELECT DISTINCT E.`event_name`
FROM `Event` AS E
JOIN `Attendance` AS A ON E.`event_id` = A.`link_to_event`
WHERE E.`type` <> 'Fundraiser'
GROUP BY E.`event_id`
HAVING COUNT(*) > 20;
```

**Predicted SQL:**

```sql
SELECT e.col_b 
FROM event e 
JOIN attendance a ON e.col_a = a.col_a 
WHERE a.col_b > 20 AND e.col_c != 'fundraiser';
```

### Q1331 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** position filter needs member (no join present); predicted compares income.date_received (col_b) to 'Vice President' on income alone

**Gold SQL:**

```sql
SELECT T2.amount FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Vice President'
```

**Predicted SQL:**

```sql
SELECT col_c FROM income WHERE col_b = 'Vice President'
```

### Q1334 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects member.phone/zip (col_g/col_h) instead of first_name/last_name; filters member.last_name (col_c) = 'IL' instead of joining zip_code.state='Illinois' (no join present)

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT col_g, col_h 
FROM member 
WHERE col_c = 'IL';
```

### Q1338 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** entirely omits event and budget needed to locate the row; compares expense.expense_date (col_c) to 'October Meeting' and expense.cost (col_d) to a date string, and outputs a hand-built CASE instead of selecting expense.approved (col_e)

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN expense.col_c = 'October Meeting' AND expense.col_d = '2019-10-08' THEN 'true'
        ELSE 'false'
    END AS is_approved
FROM 
    expense;
```

### Q1339 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes event/attendance for expense entirely; averages event.event_date (col_c) instead of expense.cost, using hardcoded 2023 dates instead of a SUBSTR month match

**Gold SQL:**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL:**

```sql
SELECT AVG(event.col_c) AS average_cost
FROM event
JOIN attendance ON event.col_a = attendance.col_a
JOIN member ON attendance.col_b = member.col_a
WHERE member.col_b = 'Elijah Allen' AND event.col_d BETWEEN '2023-09-01' AND '2023-10-31';
```

### Q1340 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** drops budget entirely (no join); sums event.event_date (col_c) instead of budget.spent; also bogus event_name='Student_Club' filter and strftime misapplied to type (col_d)

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT SUM(col_c) 
     FROM event 
     WHERE col_b = 'Student_Club' AND strftime('%Y', col_d) = '2019') -
    (SELECT SUM(col_c) 
     FROM event 
     WHERE col_b = 'Student_Club' AND strftime('%Y', col_d) = '2020') AS difference;
```

### Q1344 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes event for income entirely (same-size single-table swap); selects event.notes (col_e) instead of income.notes; also date format mismatch

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT col_e FROM event WHERE col_c = '2019/9/14' AND col_b = 'fundraising';
```

### Q1350 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** collapses budget+expense join into a single wrong table (event); selects event.notes (col_e) instead of budget.event_status, and misapplies expense_description/date filters to event.event_date/type

**Gold SQL:**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT col_e 
FROM event 
WHERE col_c = 'Post Cards, Posters' AND col_d = '2019/8/20';
```

### Q1351 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** join uses member.last_name (col_c) instead of link_to_major (col_i) against major.major_id; WHERE also compares first_name alone to full name string 'Brent Thomason'

**Gold SQL:**

```sql
SELECT T2.major_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.first_name = 'Brent' AND T1.last_name = 'Thomason'
```

**Predicted SQL:**

```sql
SELECT major.col_b 
FROM member 
JOIN major ON member.col_c = major.col_a 
WHERE member.col_b = 'Brent Thomason';
```

### Q1352 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** member.phone (col_g) used instead of t_shirt_size (col_f) for the 'Medium' filter; join key also uses last_name (col_c) instead of link_to_major (col_i)

**Gold SQL:**

```sql
SELECT COUNT(T1.member_id) FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.major_name = 'Business' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member 
JOIN major ON member.col_c = major.col_a 
WHERE major.col_b = 'Business' AND member.col_g = 'Medium';
```

### Q1356 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** no join to major (needed for department); selects member.last_name (col_c) instead; also filters first_name (col_b) = 'President' instead of position (col_e)

**Gold SQL:**

```sql
SELECT T2.department FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.position = 'President'
```

**Predicted SQL:**

```sql
SELECT col_c FROM member WHERE col_b = 'President';
```

### Q1357 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** no join to income (needed for date_received/source); selects member.last_name (col_c) instead; also uses email (col_d) for the 'Hilton' filter instead of last_name (col_c), and drops the source='Dues' filter

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT col_c FROM member WHERE col_b = 'Connor' AND col_d = 'Hilton';
```

### Q1359 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses budget.category (col_b) for the event-name filter via a meaningless self-join on budget_id, instead of joining event.event_name; also replaces the SUM ratio with a COUNT of self-joined rows

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM budget b1 
JOIN budget b2 ON b1.col_a = b2.col_a 
WHERE b1.col_b = 'Yearly Kickoff' AND b2.col_b = 'October Meeting' AND b1.col_c > b2.col_c;
```

### Q1361 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** sums expense.expense_date (col_c) instead of cost (col_d); literal case mismatch ('pizza' vs 'Pizza') would independently block matches

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(col_c) FROM expense WHERE col_b = 'pizza'
```

### Q1362 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** columns shifted by one position: selects col_b (type) instead of col_c (city); filters col_c (city)='Orange County' instead of col_d (county); filters col_d (county)='Virginia' instead of col_e (state)

**Gold SQL:**

```sql
SELECT COUNT(distinct city) FROM zip_code WHERE county = 'Orange County' AND state = 'Virginia'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT col_b) FROM zip_code WHERE col_c = 'Orange County' AND col_d = 'Virginia';
```

### Q1368 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** join uses member.last_name (col_c) instead of link_to_major (col_i) against major.major_id; WHERE phone filter (col_g) is correct

**Gold SQL:**

```sql
SELECT T2.major_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.phone = '809-555-3360'
```

**Predicted SQL:**

```sql
SELECT major.col_b 
FROM member 
JOIN major ON member.col_c = major.col_a 
WHERE member.col_g = '809-555-3360';
```

### Q1371 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters event.event_date (col_c) = 'Women's Soccer' instead of event_name (col_b); join also uses attendance.link_to_member (col_b) instead of link_to_event (col_a)

**Gold SQL:**

```sql
SELECT COUNT(T2.link_to_member) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'Women''s Soccer'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM attendance 
JOIN event ON attendance.col_b = event.col_a 
WHERE event.col_c = 'Women''s Soccer';
```

### Q1375 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** no join to major (needed for department); filters member.last_name (col_c) against the department string instead; also selects * instead of first_name/last_name

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.department = 'School of Applied Sciences, Technology and Education'
```

**Predicted SQL:**

```sql
SELECT * FROM member WHERE col_c = 'School of Applied Sciences, Technology and Education'
```

### Q1376 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters event.type (col_d) = 'closed' instead of status (col_g); joins budget/expense via event_id=budget_id/expense_id instead of proper FKs; also collapses the tie-preserving HAVING=MAX(ratio) into ORDER BY...LIMIT 1

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT e.col_a, (SUM(exp.col_c) / SUM(bud.col_c)) AS spend_to_budget_ratio
FROM event e
JOIN budget bud ON e.col_a = bud.col_a
JOIN expense exp ON e.col_a = exp.col_a
WHERE e.col_d = 'closed'
GROUP BY e.col_a
ORDER BY spend_to_budget_ratio DESC
LIMIT 1;
```

### Q1380 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes expense for budget entirely; sums expense.expense_date (col_c) instead of budget.spent, and filters expense_description (col_b) instead of category

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(col_c) FROM expense WHERE col_b = 'food'
```

### Q1381 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins member_id to attendance.link_to_event (col_a) instead of link_to_member (col_b); also drops last_name from SELECT

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT m.col_b 
FROM member m 
JOIN attendance a ON m.col_a = a.col_a 
GROUP BY m.col_a 
HAVING COUNT(a.col_b) > 7;
```

### Q1387 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits event, expense, and member entirely; selects budget.budget_id (col_a) and filters budget.category (col_b)='Yearly Kickoff' instead of joining to event.event_name and tracing to member.position='Treasurer'

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT col_a FROM budget WHERE col_b = 'Yearly Kickoff';
```

### Q1389 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits budget and expense entirely; orders by event.event_date (col_c) instead of expense.cost, and selects event_id (col_a) instead of event_name (col_b)

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM event 
ORDER BY col_c ASC, col_b ASC 
LIMIT 1;
```

### Q1390 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits budget and expense entirely; sums event.event_date (col_c) instead of expense.cost

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN col_b = 'Yearly Kickoff' THEN col_c ELSE 0 END) * 100.0 / SUM(col_c)) AS percentage
FROM 
    event;
```

### Q1392 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects/filters/orders using shifted columns throughout: date_received (col_b) selected instead of source (col_d); amount (col_c) filtered instead of date_received; SUM(source) computed as if numeric; also adds a GROUP BY gold doesn't have

**Gold SQL:**

```sql
SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM income 
WHERE col_c LIKE '2019-09%' 
GROUP BY col_b 
ORDER BY SUM(col_d) DESC 
LIMIT 1;
```

### Q1394 (simple, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** join uses member.last_name (col_c) instead of link_to_major (col_i); also adds a spurious member.first_name (col_b) = 'Student_Club' predicate that blocks all rows

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member 
JOIN major ON member.col_c = major.col_a 
WHERE member.col_b = 'Student_Club' AND major.col_b = 'Physics Teaching';
```

### Q1398 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits budget entirely; orders by event.event_date (col_c) instead of budget.spent, and drops the category='Advertisement' filter

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_b FROM event ORDER BY col_c DESC LIMIT 1;
```

### Q1399 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** attendance join columns swapped: link_to_member (col_b) used against event.event_id, and link_to_event (col_a) used against member.member_id

**Gold SQL:**

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean' AND T3.event_name = 'Women''s Soccer'
```

**Predicted SQL:**

```sql
SELECT CASE WHEN EXISTS 
(SELECT 1 FROM attendance 
JOIN event ON attendance.col_b = event.col_a 
JOIN member ON attendance.col_a = member.col_a 
WHERE member.col_b = 'Maya' AND member.col_c = 'Mclean' AND event.col_b = 'Women''s Soccer') 
THEN 'YES' ELSE 'NO' END;
```

### Q1401 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects expense.expense_date (col_c) instead of cost (col_d); also omits the event join and misapplies expense_description (col_b) and expense_id (col_a) to the wrong filter roles

**Gold SQL:**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL:**

```sql
SELECT col_c FROM expense WHERE col_b = 'September Speaker' AND col_a = 'Posters';
```

### Q1403 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters event.event_date (col_c) = 'closed' instead of budget.event_status; also joins event_id=budget_id (wrong key) and orders by (type - spent) instead of budget.remaining

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.col_b 
FROM event e 
JOIN budget b ON e.col_a = b.col_a 
WHERE e.col_c = 'closed' 
ORDER BY (e.col_d - b.col_c) DESC 
LIMIT 1;
```

### Q1404 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** omits event and budget entirely; groups/selects expense.expense_date (col_c) instead of budget.category, filters expense_id (col_a) instead of event.event_name, and drops the approved='true' filter

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
SELECT col_c, SUM(col_d) 
FROM expense 
WHERE col_a = 'October Meeting' 
GROUP BY col_c;
```

### Q1405 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects budget.spent/remaining (col_c/col_d) instead of category/amount (col_b/col_e); omits event join and the GROUP BY/SUM aggregation entirely

**Gold SQL:**

```sql
SELECT T2.category, SUM(T2.amount) FROM event AS T1 JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'April Speaker' GROUP BY T2.category ORDER BY SUM(T2.amount) ASC
```

**Predicted SQL:**

```sql
SELECT col_c, col_d 
FROM budget 
WHERE col_a = 'April Speaker' 
ORDER BY col_c ASC;
```

### Q1409 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** sums expense.expense_date (col_c) instead of cost (col_d); filters expense_id (col_a) against a date string instead of expense_date (col_c)

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(col_c) FROM expense WHERE col_a = '8/20/2019'
```

### Q1410 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes attendance+event for expense entirely, summing event.event_date (col_c) instead of expense.cost; also concatenates last_name+email (col_c/col_d) instead of first_name+last_name for the name

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'
```

**Predicted SQL:**

```sql
SELECT m.col_c || ' ' || m.col_d AS full_name, SUM(e.col_c) AS total_cost
FROM member m
JOIN attendance a ON m.col_a = a.col_b
JOIN event e ON a.col_a = e.col_a
WHERE m.col_a = 'rec4BLdZHS2Blfp4v'
GROUP BY m.col_a;
```

### Q1411 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects expense.expense_date (col_c) instead of expense_description (col_b); join also uses expense_id=member_id (wrong key, should be link_to_member) and WHERE merges first+last name into one first_name comparison

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT e.col_c 
FROM expense e 
JOIN member m ON e.col_a = m.col_a 
WHERE m.col_b = 'Sacha Harrison';
```

### Q1422 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects event.event_date (col_c) instead of type (col_d); filters type (col_d) = 'MU 215' instead of location (col_f)

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT col_c FROM event WHERE col_d = 'MU 215';
```

### Q1426 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects member.phone (col_g) instead of last_name (col_c); join key also uses first_name (col_b) instead of link_to_major (col_i), and drops the position='Member' filter

**Gold SQL:**

```sql
SELECT T2.last_name, T1.department, T1.college FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T2.position = 'Member' AND T1.major_name = 'Environmental Engineering'
```

**Predicted SQL:**

```sql
SELECT member.col_g, major.col_c, major.col_d 
FROM member 
JOIN major ON member.col_b = major.col_a 
WHERE major.col_b = 'Environmental Engineering';
```

### Q1427 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects budget.spent (col_c) instead of category (col_b); filters budget_id (col_a) against 'MU 215' instead of joining event.location, and compares category (col_b) to '0' instead of spent (col_c)=0; also drops the type='Guest Speaker' filter

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT col_c 
FROM budget 
WHERE col_a = 'MU 215' AND col_b = '0';
```

### Q1432 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** omits the income/amount=50 condition entirely, replacing it with member.last_name (col_c) = 'medium'; also replaces position='Member' with a spurious first_name (col_b) = 'Student_Club' predicate

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c = 'medium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM member 
WHERE col_b = 'Student_Club';
```

### Q1435 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** event_date (col_c) and type (col_d) are swapped: col_c compared to 'game', col_d used in the date range; also drops the status='Closed' filter and DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM event 
WHERE col_c = 'game' 
AND col_d BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1457 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** treats expense.expense_id (col_a) as the member-id grouping key instead of link_to_member (col_f); averages expense_date (col_c) instead of cost; and compares member.email (col_d) to that average instead of cost>avg(cost)

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT m.col_b, m.col_c
FROM member m
JOIN (
    SELECT e.col_a AS member_id, AVG(e.col_c) AS avg_expense
    FROM expense e
    GROUP BY e.col_a
) subq ON m.col_a = subq.member_id
WHERE m.col_d > subq.avg_expense;
```

### Q1460 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters expense.expense_date (col_c) IN ('water','veggie tray','supplies') instead of matching expense_description (col_b) exactly; join also uses expense_id=member_id (wrong key) instead of link_to_member

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.col_b, m.col_c, e.col_d
FROM member m
JOIN expense e ON m.col_a = e.col_a
WHERE e.col_c IN ('water', 'veggie tray', 'supplies');
```

### Q1464 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects member.last_name/email (col_c/col_d) instead of first_name/last_name, and income.notes (col_e) instead of amount (col_c); join also uses income_id=member_id (wrong key) instead of link_to_member; date format also differs

**Gold SQL:**

```sql
SELECT M.`first_name`, M.`last_name`, I.`amount`
FROM `Income` I
JOIN `Member` M ON M.`member_id` = I.`link_to_member`
WHERE I.`date_received` = '2019-09-09';
```

**Predicted SQL:**

```sql
SELECT member.col_c, member.col_d, income.col_e
FROM member
JOIN income ON member.col_a = income.col_a
WHERE income.col_b = '9/9/2019';
```

---

## superhero (45 failures)

### Q719 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.full_name (col_c) > 200 instead of height_cm (col_k); joins are otherwise correct

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.height_cm > 200
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN hero_power ON superhero.col_a = hero_power.col_a 
JOIN superpower ON hero_power.col_b = superpower.col_a 
WHERE superpower.col_b = 'Super Strength' AND superhero.col_c > 200;
```

### Q723 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.full_name (col_c) to colour.id instead of eye_colour_id (col_e); also case mismatch 'blue' vs 'Blue'

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.col_c = colour.col_a 
JOIN hero_power ON superhero.col_a = hero_power.col_a 
JOIN superpower ON hero_power.col_b = superpower.col_a 
WHERE colour.col_b = 'blue' AND superpower.col_b = 'Agility';
```

### Q724 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes attribute for colour (joining superhero.id directly to attribute.id, not a valid FK relationship) with fictional values 'blue eyes'/'blond hair' instead of joining colour for eye/hair_colour_id

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT superhero.col_b 
FROM superhero 
JOIN attribute ON superhero.col_a = attribute.col_a 
WHERE attribute.col_b = 'blue eyes' 
INTERSECT 
SELECT superhero.col_b 
FROM superhero 
JOIN attribute ON superhero.col_a = attribute.col_a 
WHERE attribute.col_b = 'blond hair';
```

### Q726 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by superhero.gender_id (col_d) instead of height_cm (col_k); join also uses full_name (col_c) instead of publisher_id (col_i), and drops the height_cm IS NOT NULL/!=0 filters

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT superhero.col_a, superhero.col_b 
FROM superhero 
JOIN publisher ON superhero.col_c = publisher.col_a 
WHERE publisher.col_b = 'Marvel Comics' 
ORDER BY superhero.col_d DESC;
```

### Q728 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.height_cm (col_k) to 'Marvel Comics' instead of joining publisher.publisher_name (no join present); colour join also uses alignment_id (col_j) instead of eye_colour_id (col_e); RANK() OVER window is also missing

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.col_b AS eye_color, COUNT(*) AS count 
FROM superhero s 
JOIN colour c ON s.col_j = c.col_a 
WHERE s.col_k = 'Marvel Comics' 
GROUP BY c.col_b 
ORDER BY count DESC;
```

### Q730 (challenging, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.height_cm (col_k) to publisher.id instead of publisher_id (col_i)

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_power AS T2 INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.id = T2.hero_id)AND EXISTS (SELECT 1 FROM publisher AS T4 WHERE T4.publisher_name = 'Marvel Comics' AND T1.publisher_id = T4.id)
```

**Predicted SQL:**

```sql
SELECT s.col_b 
FROM superhero s 
JOIN hero_power hp ON s.col_a = hp.col_a 
JOIN superpower sp ON hp.col_b = sp.col_a 
JOIN publisher p ON s.col_k = p.col_a 
WHERE p.col_b = 'Marvel Comics' AND sp.col_b = 'Super Strength';
```

### Q732 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits hero_attribute and attribute entirely (needed for the Speed attribute_value sort); publisher join also uses weight_kg (col_l) instead of publisher_id (col_i); orders by full_name (col_c) DESC as an arbitrary substitute

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id INNER JOIN attribute AS T4 ON T3.attribute_id = T4.id WHERE T4.attribute_name = 'Speed' ORDER BY T3.attribute_value LIMIT 1
```

**Predicted SQL:**

```sql
SELECT p.col_b 
FROM publisher p 
JOIN superhero s ON p.col_a = s.col_l 
ORDER BY s.col_c DESC 
LIMIT 1;
```

### Q733 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.full_name (col_c) to 'gold' instead of joining colour.colour via eye_colour_id (no join present); publisher join also uses alignment_id (col_j) instead of publisher_id (col_i)

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN publisher ON superhero.col_j = publisher.col_a 
WHERE publisher.col_b = 'Marvel Comics' AND superhero.col_c = 'gold';
```

### Q736 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits hero_attribute and attribute entirely; orders by superhero.full_name (col_c) alphabetically instead of the minimum Intelligence attribute_value

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT col_b FROM superhero ORDER BY col_c ASC LIMIT 1;
```

### Q737 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.publisher_id (col_i) to race.id instead of race_id (col_h)

**Gold SQL:**

```sql
SELECT T2.race FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id WHERE T1.superhero_name = 'Copycat'
```

**Predicted SQL:**

```sql
SELECT T2.col_b FROM superhero AS T1 JOIN race AS T2 ON T1.col_i = T2.col_a WHERE T1.col_b = 'Copycat'
```

### Q738 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects superhero.id (col_a) instead of superhero_name (col_b); also swaps hero_attribute's attribute_value (col_c) and attribute_id (col_b) roles and omits the attribute table needed to resolve 'Durability'

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_attribute AS T2 INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Durability' AND T2.attribute_value < 50 AND T1.id = T2.hero_id)
```

**Predicted SQL:**

```sql
SELECT superhero.col_a 
FROM superhero 
JOIN hero_attribute ON superhero.col_a = hero_attribute.col_a 
WHERE hero_attribute.col_c = 'Durability' AND hero_attribute.col_b < 50;
```

### Q739 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** power_name literal case mismatch: 'death touch' vs stored 'Death Touch'; joins are otherwise correct

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Death Touch'
```

**Predicted SQL:**

```sql
SELECT superhero.col_b 
FROM superhero 
JOIN hero_power ON superhero.col_a = hero_power.col_a 
JOIN superpower ON hero_power.col_b = superpower.col_a 
WHERE superpower.col_b = 'death touch';
```

### Q740 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits the attribute table entirely (can't filter attribute_name='Strength', so attribute_value=100 counts across all attributes); gender join also uses skin_colour_id (col_g) instead of gender_id (col_d)

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.attribute_name = 'Strength' AND T2.attribute_value = 100 AND T4.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN gender ON superhero.col_g = gender.col_a 
JOIN hero_attribute ON superhero.col_a = hero_attribute.col_a 
WHERE gender.col_b = 'Female' AND hero_attribute.col_c = 100;
```

### Q743 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.alignment_id (col_j) directly to 'Marvel Comics' instead of joining publisher.publisher_name (no join present); also mismatches the alignment join (id=id instead of alignment_id) and uses 'Selfish' instead of 'Bad'

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN alignment.col_b = 'Selfish' THEN 1 END) * 100.0 / COUNT(*)) AS percentage_selfish,
    COUNT(CASE WHEN alignment.col_b = 'Selfish' AND superhero.col_j = 'Marvel Comics' THEN 1 END) AS count_marvel_selfish
FROM 
    superhero
JOIN 
    alignment ON superhero.col_a = alignment.col_a;
```

### Q744 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins publisher.id to superhero.height_cm (col_k) instead of publisher_id (col_i); also restructures to a GROUP BY count instead of gold's marvel_cnt-dc_cnt difference, and uses 'DC' instead of 'DC Comics'

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
    p.col_b AS publisher, 
    COUNT(s.col_a) AS superhero_count
FROM 
    publisher p
JOIN 
    superhero s ON p.col_a = s.col_k
WHERE 
    p.col_b IN ('DC', 'Marvel Comics')
GROUP BY 
    p.col_b
ORDER BY 
    superhero_count DESC;
```

### Q747 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** checks superhero.superhero_name (col_b) IS NULL/empty instead of full_name (col_c)

**Gold SQL:**

```sql
SELECT COUNT(id) FROM superhero WHERE full_name IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM superhero WHERE col_b IS NULL OR col_b = ''
```

### Q750 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** averages superhero.full_name (col_c) instead of weight_kg (col_l); compares gender_id (col_d) directly to 'Female' instead of joining gender.gender (no join present); also drops the weight_kg>0 filter

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) FROM superhero WHERE col_d = 'Female'
```

### Q751 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.skin_colour_id (col_g) to gender.id instead of gender_id (col_d)

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL:**

```sql
SELECT sp.col_b 
FROM superhero sh 
JOIN hero_power hp ON sh.col_a = hp.col_a 
JOIN superpower sp ON hp.col_b = sp.col_a 
JOIN gender g ON sh.col_g = g.col_a 
WHERE g.col_b = 'Male';
```

### Q753 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses superhero.full_name (col_c) for the height BETWEEN 170-190 filter instead of height_cm (col_k); checks gender_id (col_d) IS NULL instead of joining colour.colour='No Colour' via eye_colour_id (no join present)

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM superhero 
WHERE col_c BETWEEN 170 AND 190 AND col_d IS NULL;
```

### Q758 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins colour via superhero.full_name (col_c) instead of hair_colour_id (col_f); compares gender_id (col_d)='human' instead of joining race (no join present); compares eye_colour_id (col_e)=185 instead of height_cm (col_k)

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT colour.col_b 
FROM superhero 
JOIN colour ON superhero.col_c = colour.col_a 
WHERE superhero.col_d = 'human' AND superhero.col_e = 185;
```

### Q760 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses superhero.full_name (col_c) for the height BETWEEN 150-180 filter instead of height_cm (col_k); publisher join also uses alignment_id (col_j) instead of publisher_id (col_i)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.height_cm BETWEEN 150 AND 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.col_b = 'Marvel Comics' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero AS T1 
JOIN publisher AS T2 ON T1.col_j = T2.col_a 
WHERE T1.col_c BETWEEN 150 AND 180;
```

### Q761 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.full_name (col_c) to the weight_kg average subquery instead of weight_kg (col_l) itself; gender join also uses skin_colour_id (col_g) instead of gender_id (col_d)

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id WHERE T2.gender = 'Male' AND T1.weight_kg * 100 > ( SELECT AVG(weight_kg) FROM superhero WHERE weight_kg > 0) * 79
```

**Predicted SQL:**

```sql
SELECT superhero.col_b 
FROM superhero 
JOIN gender ON superhero.col_g = gender.col_a 
WHERE gender.col_b = 'Male' 
AND superhero.col_c > (SELECT AVG(col_c) * 0.79 FROM superhero)
```

### Q765 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** power_name literal case mismatch: 'stealth' vs stored 'Stealth'; extra harmless join to superhero doesn't affect the row count

**Gold SQL:**

```sql
SELECT COUNT(T1.hero_id) FROM hero_power AS T1 INNER JOIN superpower AS T2 ON T1.power_id = T2.id WHERE T2.power_name = 'Stealth'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN hero_power ON superhero.col_a = hero_power.col_a 
JOIN superpower ON hero_power.col_b = superpower.col_a 
WHERE superpower.col_b = 'stealth';
```

### Q766 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares hero_attribute.attribute_id (col_b) directly to 'strength' instead of joining attribute.attribute_name (no join present), so MAX(attribute_value) is taken across all attributes, not just Strength

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT superhero.col_b, superhero.col_c 
FROM superhero 
JOIN hero_attribute ON superhero.col_a = hero_attribute.col_a 
WHERE hero_attribute.col_c = (SELECT MAX(col_c) FROM hero_attribute WHERE col_b = 'strength');
```

### Q769 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits hero_attribute and attribute entirely (needed for the Durability attribute_value ranking); publisher join also uses height_cm (col_k) instead of publisher_id (col_i); orders by full_name (col_c) DESC as an arbitrary substitute

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.col_b 
FROM superhero s 
JOIN publisher p ON s.col_k = p.col_a 
WHERE p.col_b = 'Dark Horse Comics' 
ORDER BY s.col_c DESC 
LIMIT 1;
```

### Q772 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** every FK join is shifted: skin_colour_id (col_g) used for both gender and 'eye colour', race_id (col_h) for 'hair colour', publisher_id (col_i) for 'skin colour', and height_cm (col_k) for publisher; also outputs resolved colour names instead of gold's raw eye/hair/skin_colour_id integers

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c.col_b AS eyes, 
    d.col_b AS hair, 
    e.col_b AS skin 
FROM 
    superhero s 
JOIN 
    gender g ON s.col_g = g.col_a 
JOIN 
    colour c ON s.col_h = c.col_a 
JOIN 
    colour d ON s.col_i = d.col_a 
JOIN 
    colour e ON s.col_j = e.col_a 
JOIN 
    publisher p ON s.col_k = p.col_a 
WHERE 
    g.col_b = 'Female' AND 
    p.col_b = 'Dark Horse Comics';
```

### Q773 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** WHERE compares full_name (col_c), gender_id (col_d), eye_colour_id (col_e) instead of eye/hair/skin_colour_id (col_e/f/g); publisher join also uses superhero.id (col_a) instead of publisher_id (col_i)

**Gold SQL:**

```sql
SELECT T1.superhero_name, T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.eye_colour_id = T1.hair_colour_id AND T1.eye_colour_id = T1.skin_colour_id
```

**Predicted SQL:**

```sql
SELECT s.col_b, p.col_b 
FROM superhero s 
JOIN publisher p ON s.col_a = p.col_a 
WHERE s.col_c = s.col_d AND s.col_d = s.col_e;
```

### Q775 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** colour join uses superhero.height_cm (col_k) instead of skin_colour_id (col_g); gender join uses alignment_id (col_j) instead of gender_id (col_d)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T1.col_b = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    colour AS T1 
JOIN 
    superhero AS T2 ON T1.col_a = T2.col_k 
JOIN 
    gender AS T3 ON T2.col_j = T3.col_a 
WHERE 
    T3.col_b = 'female';
```

### Q781 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects superhero.full_name (col_c) instead of height_cm (col_k); compares gender_id (col_d) to 'amber' instead of joining colour.colour via eye_colour_id (no join present)

**Gold SQL:**

```sql
SELECT T1.height_cm FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T2.colour = 'Amber'
```

**Predicted SQL:**

```sql
SELECT col_c FROM superhero WHERE col_d = 'amber'
```

### Q782 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** eye_colour join uses full_name (col_c) instead of eye_colour_id (col_e); hair_colour join uses gender_id (col_d) instead of hair_colour_id (col_f)

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT superhero.col_b 
FROM superhero 
JOIN colour AS eye_colour ON superhero.col_c = eye_colour.col_a 
JOIN colour AS hair_colour ON superhero.col_d = hair_colour.col_a 
WHERE eye_colour.col_b = 'black' AND hair_colour.col_b = 'black';
```

### Q785 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.full_name (col_c) to the alignment id subquery instead of alignment_id (col_j)

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id WHERE T2.alignment = 'Neutral'
```

**Predicted SQL:**

```sql
SELECT col_b FROM superhero WHERE col_c = (SELECT col_a FROM alignment WHERE col_b = 'Neutral')
```

### Q786 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes superhero entirely for hero_attribute+attribute; compares full_name (col_c) against MAX(full_name) instead of Strength's attribute_value against its max

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
WHERE col_c = (SELECT MAX(col_c) FROM superhero);
```

### Q788 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** gender join uses skin_colour_id (col_g) instead of gender_id (col_d); publisher join uses alignment_id (col_j) instead of publisher_id (col_i); WHERE-filtering the outer-joined publisher also negates the LEFT JOIN's purpose, and the % denominator isn't restricted to Female

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.col_b = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM gender AS T1 
JOIN superhero AS T2 ON T1.col_a = T2.col_g 
JOIN publisher AS T3 ON T2.col_j = T3.col_a 
WHERE T3.col_b = 'Marvel Comics';
```

### Q790 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** subtracts superhero.full_name (col_c) values instead of weight_kg (col_l); also filters by superhero_name (col_b) instead of full_name (col_c) for the LIKE match

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT (SELECT col_c FROM superhero WHERE col_b = 'Emil Blonsky') - 
       (SELECT col_c FROM superhero WHERE col_b = 'Charles Chandler') AS weight_difference;
```

### Q791 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** averages superhero.full_name (col_c) instead of height_cm (col_k); also drops the height_cm>0 filter

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) FROM superhero
```

### Q794 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits hero_attribute and attribute entirely; compares full_name (col_c) to MAX(full_name) instead of Speed's attribute_value to its max

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT col_b FROM superhero WHERE col_c = (SELECT MAX(col_c) FROM superhero)
```

### Q797 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes attribute for colour with fictional values 'blue eyes'/'brown hair', joining via full_name (col_c) rather than eye/hair_colour_id; also selects id (col_a) instead of superhero_name (col_b)

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT superhero.col_a 
FROM superhero 
JOIN attribute ON superhero.col_c = attribute.col_a 
WHERE attribute.col_b = 'blue eyes' 
INTERSECT 
SELECT superhero.col_a 
FROM superhero 
JOIN attribute ON superhero.col_c = attribute.col_a 
WHERE attribute.col_b = 'brown hair';
```

### Q798 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.weight_kg (col_l) to publisher.id instead of publisher_id (col_i)

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL:**

```sql
SELECT T2.col_b 
FROM superhero AS T1 
JOIN publisher AS T2 ON T1.col_l = T2.col_a 
WHERE T1.col_b IN ('Hawkman', 'Karate Kid', 'Speedy');
```

### Q800 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.full_name (col_c) to colour.id instead of eye_colour_id (col_e); also case mismatch 'blue' vs 'Blue'

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.col_b = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero AS T1 
JOIN colour AS T2 ON T1.col_c = T2.col_a;
```

### Q801 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters superhero.skin_colour_id (col_g) against gender.id subqueries instead of gender_id (col_d), for both the Male and Female counts

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.gender = 'Male' THEN T1.id ELSE NULL END) AS REAL) / COUNT(CASE WHEN T2.gender = 'Female' THEN T1.id ELSE NULL END) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM superhero WHERE col_g = (SELECT col_a FROM gender WHERE col_b = 'Male')) * 1.0 / 
    (SELECT COUNT(*) FROM superhero WHERE col_g = (SELECT col_a FROM gender WHERE col_b = 'Female')) AS ratio;
```

### Q806 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters superhero.superhero_name (col_b) against 'Karen Beecher-Duncan' (a full_name value) instead of full_name (col_c); colour join also uses alignment_id (col_j) instead of eye_colour_id (col_e)

**Gold SQL:**

```sql
SELECT T2.colour FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.full_name = 'Karen Beecher-Duncan'
```

**Predicted SQL:**

```sql
SELECT T2.col_b FROM superhero AS T1 JOIN colour AS T2 ON T1.col_j = T2.col_a WHERE T1.col_b = 'Karen Beecher-Duncan'
```

### Q819 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.full_name (col_c) to 'blue' instead of joining colour via eye_colour_id (no join present); also checks skin_colour_id (col_g) IS NULL instead of weight_kg (col_l)=0/NULL

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN col_c = 'blue' THEN 1 ELSE 0 END) - 
    SUM(CASE WHEN col_c IS NULL THEN 1 ELSE 0 END) AS difference
FROM 
    superhero
WHERE 
    col_g IS NULL;
```

### Q822 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** colour join uses full_name (col_c) instead of skin_colour_id (col_g); alignment join uses gender_id (col_d) instead of alignment_id (col_j); also uses 'villain' instead of 'Bad'

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.col_c = colour.col_a 
JOIN alignment ON superhero.col_d = alignment.col_a 
WHERE colour.col_b = 'green' AND alignment.col_b = 'villain';
```

### Q825 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins superhero.full_name (col_c) to gender.id instead of gender_id (col_d)

**Gold SQL:**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL:**

```sql
SELECT g.col_b 
FROM superhero s 
JOIN hero_power hp ON s.col_a = hp.col_a 
JOIN superpower sp ON hp.col_b = sp.col_a 
JOIN gender g ON s.col_c = g.col_a 
WHERE sp.col_b = 'Phoenix Force';
```

### Q829 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares superhero.alignment_id (col_j) directly to 'DC'/'Marvel Comics' instead of joining publisher.publisher_name via publisher_id (no join present); also omits the CASE for which publisher has more heroes and uses 'DC' instead of 'DC Comics'

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
SELECT (SELECT COUNT(*) FROM superhero WHERE col_j = 'DC') - 
       (SELECT COUNT(*) FROM superhero WHERE col_j = 'Marvel Comics') AS difference;
```

---

## thrombosis_prediction (50 failures)

### Q1149 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (Patient) and SEX (col_b) is correctly resolved, but the in/out-patient split uses Birthday (col_c) instead of Admission (col_f); also 'inpatient'/'outpatient' vs gold's '+'/'-' codes.

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN col_c = 'inpatient' THEN 1 ELSE 0 END) - SUM(CASE WHEN col_c = 'outpatient' THEN 1 ELSE 0 END)) AS difference,
    CAST(SUM(CASE WHEN col_c = 'inpatient' THEN 1 ELSE 0 END) AS REAL) * 100 / (SUM(CASE WHEN col_c = 'inpatient' THEN 1 ELSE 0 END) + SUM(CASE WHEN col_c = 'outpatient' THEN 1 ELSE 0 END)) - 50 AS deviation_percentage
FROM 
    Patient
WHERE 
    col_b = 'male';
```

### Q1150 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** SEX (col_b) and Birthday (col_c) are the correct columns, but SEX compares to 'Female' instead of 'F', and Birthday is compared directly to the string '1930' instead of gold's STRFTIME('%Y', Birthday) year-extraction.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient 
WHERE col_b = 'Female';
```

### Q1152 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is Patient (Diagnosis, Admission); predicted substitutes Examination -- Examination Date (col_b) compared to 'SLE' and aCL IgG (col_c) compared to admission strings.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN col_c = 'Inpatient' THEN 1 ELSE 0 END) / 
    SUM(CASE WHEN col_c = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio
FROM 
    Examination
WHERE 
    col_b = 'SLE';
```

### Q1153 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a vestigial Examination bridge to a correctly-keyed Patient+Laboratory join, but SELECT returns Laboratory.GOT/GPT (col_c/col_d) instead of Patient.Diagnosis and Laboratory.Date (col_b).

**Gold SQL:**

```sql
SELECT T1.Diagnosis, T2.Date FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 30609
```

**Predicted SQL:**

```sql
SELECT DISTINCT L.col_c, L.col_d
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
JOIN Laboratory L ON E.col_a = L.col_a
WHERE P.col_a = '30609';
```

### Q1155 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (LDH); predicted substitutes Examination for Laboratory -- filters aCL IgM (col_d) instead of LDH, which doesn't exist on Examination at all.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT P.col_a AS patient_id, P.col_b AS sex, P.col_c AS birthday
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_d > 100; -- Assuming col_d is the column for LDH and 100 is the normal range threshold
```

### Q1156 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables match gold (Patient, Examination) but SELECT returns SEX (P.col_b) instead of the computed age from Birthday, and the RVVT='+' filter lands on aCL IgG (E.col_c) instead of RVVT (col_j).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT P.col_a AS patient_id, P.col_b AS age 
FROM Patient P 
JOIN Examination E ON P.col_a = E.col_a 
WHERE E.col_c = 'positive';
```

### Q1157 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables match gold (Patient, Examination) but SELECT returns aCL IgG (E.col_c) instead of Patient.Diagnosis, and the Thrombosis=2 filter is replaced with aCL IgM (E.col_d) compared to a description string instead of Thrombosis=col_m=2.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT P.col_a AS patient_id, P.col_b AS sex, E.col_c AS disease
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_d = 'severe thrombosis';
```

### Q1162 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Description (col_d) correctly resolves for the year filter, but the SEX='F' filter lands on Birthday (col_c) instead of SEX (col_b), and the Admission='-' filter is dropped entirely.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_c = 'Female' AND col_d LIKE '1997%';
```

### Q1164 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables match gold (Patient, Examination) but every column is misresolved: Examination Date (col_b) filtered against 'thrombosis' instead of Thrombosis=col_m, aCL IgG (col_c) run through strftime instead of Examination Date, and Patient.First Date (col_e) compared to 'female' instead of SEX; an unwarranted ORDER BY/LIMIT 10 is also added.

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
FROM Patient 
WHERE col_a IN (
    SELECT col_a 
    FROM Examination 
    WHERE col_b = 'thrombosis' AND strftime('%Y', col_c) = '1997' 
    ORDER BY col_d DESC 
    LIMIT 10
) AND col_e = 'female';
```

### Q1166 (simple, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_e' -- both joined tables (Examination, Patient) have a real column at position e (ANA vs First Date), and the unqualified bare col_e reference doesn't disambiguate; a construction bug from the S1 positional-alias scheme, not a hallucinated identifier.

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT col_e 
FROM Examination 
JOIN Patient ON Examination.col_a = Patient.col_a 
WHERE Patient.col_c = (SELECT MIN(col_c) FROM Patient)
```

### Q1168 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Adds a vestigial Examination bridge to a correctly-keyed Patient+Laboratory join, but never uses Laboratory.Date for the SELECT/ORDER BY (uses Patient.Birthday instead), and the SJS diagnosis filter lands on Patient.First Date (col_e) instead of Diagnosis (col_g).

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MAX(P.col_c) AS last_laboratory_date, 
    P.col_d AS initial_age
FROM 
    Patient P
JOIN 
    Examination E ON P.col_a = E.col_a
JOIN 
    Laboratory L ON P.col_a = L.col_a
WHERE 
    P.col_e = 'SJS'
ORDER BY 
    P.col_c DESC
LIMIT 1;
```

### Q1169 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (UA); predicted substitutes Examination for Laboratory -- filters ANA (col_e)='Abnormal' instead of UA, and the SEX='M'/'F' split lands on Birthday (col_c) instead of SEX (col_b).

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN P.col_c = 'Male' THEN 1 ELSE 0 END) / 
    SUM(CASE WHEN P.col_c = 'Female' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    Patient P
JOIN 
    Examination E ON P.col_a = E.col_a
WHERE 
    E.col_e = 'Abnormal';
```

### Q1171 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's Examination Date (for the 1990-1993 range and the age-at-exam computation) lives only on Examination; predicted queries Patient alone, comparing SEX (col_b) to 1990/1993 with a self-contradictory AND -- Examination missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_b < 1990 AND col_b > 1993;
```

### Q1175 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Laboratory is correctly joined (needed for HGB) but ORDER BY uses Laboratory.Date (col_b) instead of HGB (col_s), and SELECT returns Examination.ANA (col_e) instead of Patient.Diagnosis and a computed age.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.col_c, E.col_e 
FROM Patient P 
JOIN Examination E ON P.col_a = E.col_a 
JOIN Laboratory L ON E.col_a = L.col_a 
ORDER BY L.col_b DESC 
LIMIT 1;
```

### Q1179 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Examination ('aCL IgM', Examination Date) plus a Patient subquery; predicted substitutes Laboratory for Examination via a nonsensical Date-to-ID join key, and returns Laboratory.ID (col_a) instead of 'aCL IgM' -- Laboratory doesn't have that column at all.

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT L.col_a 
FROM Laboratory L 
JOIN Patient P ON L.col_b = P.col_a 
WHERE P.col_c = 'SLE' AND P.col_d = '1994-02-19' 
AND L.col_c = 'anti-Cardiolipin antibody' AND L.col_d = '1993-11-12';
```

### Q1185 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory ('T-CHO'); predicted substitutes Examination for Laboratory -- computes the Nov/Dec ratio over Thrombosis (col_m) instead of 'T-CHO', which doesn't exist on Examination.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(CASE WHEN Examination.col_c = '1981-12' THEN Examination.col_m END) - 
     MIN(CASE WHEN Examination.col_c = '1981-11' THEN Examination.col_m END)) / 
    MIN(CASE WHEN Examination.col_c = '1981-11' THEN Examination.col_m END) AS decrease_rate
FROM 
    Examination
JOIN 
    Patient ON Examination.col_a = Patient.col_a
WHERE 
    Patient.col_d = '1959-02-18';
```

### Q1187 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Laboratory is joined (needed for GPT/ALB) but the Date range filter lands on the vestigial Examination.Examination Date instead of Laboratory.Date, and GPT>30 lands on Laboratory.TP (col_g) instead of GPT (col_d); ALB<4 (col_h) is the one correctly-resolved filter.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.col_a AS patient_id
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
JOIN Laboratory L ON P.col_a = L.col_a
WHERE E.col_b BETWEEN '1987-07-06' AND '1996-01-31'
AND L.col_g > 30
AND L.col_h < 4;
```

### Q1189 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** aCL IgM (col_d) is the correct column for the threshold comparison, but the Thrombosis=2 filter lands on Examination Date (col_b) and the ANA Pattern='S' filter lands on aCL IgG (col_c); the correlated AVG subquery also drops both filters and uses a flat +20 instead of gold's *1.2.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient p 
JOIN Examination e ON p.col_a = e.col_a 
WHERE e.col_b = 'thrombosis level 2' 
AND e.col_c = 'S' 
AND e.col_d > (SELECT AVG(col_d) + 20 FROM Examination WHERE col_d IS NOT NULL);
```

### Q1192 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Patient+Laboratory are both present (plus a vestigial Examination) but the Admission='-' filter is misapplied to Examination.Examination Date (which doesn't hold Admission at all -- that's Patient.col_f), and within Laboratory, GOT (col_c) and GPT (col_d) are used in place of Date and 'T-BIL'.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.col_a, p.col_b, p.col_c
FROM Patient p
JOIN Examination e ON p.col_a = e.col_a
JOIN Laboratory l ON p.col_a = l.col_a
WHERE e.col_b = 'outpatient clinic'
AND l.col_c BETWEEN '1991-10-01' AND '1991-10-31'
AND l.col_d BETWEEN 5 AND 20;
```

### Q1195 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Patient+Laboratory are both present (plus a vestigial Examination) but AVG is taken over Laboratory.IGG (col_ac) instead of ALB (col_h), PLT>400 lands on Laboratory.IGA (col_ad), SEX='F' lands on Patient.First Date (col_e), and Diagnosis='SLE' is misapplied to Examination.ANA (which doesn't hold Diagnosis -- that's Patient.col_g).

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(L.col_ac) 
FROM Laboratory L 
JOIN Patient P ON L.col_a = P.col_a 
JOIN Examination E ON P.col_a = E.col_a 
WHERE P.col_e = 'Female' AND L.col_ad > 400 AND E.col_e = 'SLE';
```

### Q1198 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table Patient already holds Diagnosis (col_g), but predicted looks it up via a wrong Examination subquery (filtering Examination Date='APS' instead); SEX='F' also lands on First Date (col_e) instead of SEX (col_b).

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_e = 'Female' 
AND col_a IN (
    SELECT col_a 
    FROM Examination 
    WHERE col_b = 'APS'
);
```

### Q1201 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Birthday (col_c) is correctly resolved for the year filter, but SEX='F' lands on First Date (col_e), and Diagnosis='RA' lands on Description (col_d) instead of Diagnosis (col_g).

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_e = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient 
WHERE strftime('%Y', col_c) = '1980' AND col_d = 'RA';
```

### Q1205 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's SEX+UA compound condition needs Patient JOIN Laboratory; predicted queries Laboratory alone, replacing the SEX-dependent UA thresholds with a single GOT (col_c) range check -- Patient missing entirely.

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN col_c BETWEEN 2.4 AND 7.0 THEN 'true'
        ELSE 'false'
    END AS is_normal
FROM 
    Laboratory
WHERE 
    col_a = 57266;
```

### Q1208 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Patient+Laboratory are both present (plus a vestigial Examination) but SEX='M' lands on Patient.Birthday (col_c), and GPT>=60 lands on Laboratory.Date/GOT (col_b/col_c) instead of GPT (col_d).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.col_a AS patient_id
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
JOIN Laboratory L ON E.col_a = L.col_a
WHERE P.col_c = 'male'
AND L.col_b = 'ALT glutamic pylvic transaminase (GPT)'
AND L.col_c > 40; -- Assuming 40 is the normal range threshold for ALT GPT
```

### Q1209 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (GPT); predicted substitutes Examination for Laboratory -- filters aCL IgG (col_c) instead of GPT, orders by Patient.Description (col_d) instead of Birthday, and selects SEX (col_b) instead of Diagnosis.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.col_b AS Diagnosis
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_c > 40
ORDER BY P.col_d ASC;
```

### Q1220 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (UN); predicted substitutes Examination for Laboratory -- filters aCL IgM/ANA (col_d/col_e) instead of UN, which doesn't exist on Examination.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT P.col_a AS ID, P.col_b AS Sex, P.col_c AS Birthday
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_d = 'Urea Nitrogen' AND E.col_e BETWEEN 7 AND 8;
```

### Q1225 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory ('T-BIL'); predicted substitutes Examination for Laboratory -- filters RVVT (col_j) instead of 'T-BIL', and mislabels SEX/Birthday (col_b/col_c) as 'patient_name'/'sex', grouping by both instead of just SEX.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.col_b AS patient_name, P.col_c AS sex, COUNT(*) AS count
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_j NOT BETWEEN 5 AND 20
GROUP BY P.col_b, P.col_c;
```

### Q1227 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's 'T-CHO' filter (the entire selection criterion) lives only on Laboratory; predicted queries Patient alone, filtering Description (col_d) instead and averaging raw Birthday (col_c) instead of a computed age -- Laboratory missing entirely.

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) 
FROM Patient 
WHERE col_b = 'male' AND col_d > 200;
```

### Q1229 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's TG (Triglyceride) filter lives only on Laboratory; predicted's primary filter subquery uses Examination instead (which has no TG field), and the age computation drops the age-formula for a raw Birthday>50 comparison.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_c > 50 
AND col_a IN (
    SELECT col_a 
    FROM Examination 
    WHERE col_b = 'Triglyceride' 
    AND col_c > (SELECT col_c FROM Laboratory WHERE col_b = 'Normal TG Range')
);
```

### Q1231 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (CPK); predicted substitutes Examination for Laboratory -- CPK is only referenced inside a broken nested value lookup, and the primary filter uses Examination.ANA (col_e); SEX='M' also lands on Description (col_d) instead of SEX (col_b).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient p 
JOIN Examination e ON p.col_a = e.col_a 
WHERE p.col_c BETWEEN '1936-01-01' AND '1956-12-31' 
AND p.col_d = 'male' 
AND e.col_e > (SELECT col_b FROM Laboratory WHERE col_c = 'creatinine phosphokinase' AND col_d = 'normal_max') 
AND e.col_e < (SELECT col_a FROM Laboratory WHERE col_c = 'creatinine phosphokinase' AND col_d = 'normal_min');
```

### Q1232 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and join key are correct (Patient, Laboratory) but GLU>=180 lands on Laboratory.Date/GOT (col_b/col_c) instead of GLU (col_p), and the correlated 'T-CHO'<250 check uses the same wrong columns instead of 'T-CHO' (col_m).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT P.col_a AS ID, P.col_b AS sex, P.col_c AS age
FROM Patient P
JOIN Laboratory L ON P.col_a = L.col_a
WHERE L.col_b = 'GLU' AND L.col_c NOT BETWEEN 70 AND 110
AND EXISTS (
    SELECT 1
    FROM Laboratory L2
    WHERE L2.col_a = P.col_a AND L2.col_b = 'T-CHO' AND L2.col_c BETWEEN 130 AND 200
);
```

### Q1235 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (RBC); predicted substitutes Examination for Laboratory -- filters aCL IgM (col_d) against its own average instead of RBC<3.5, and mislabels aCL IgG (col_c) as 'diagnosis' instead of using Patient.Diagnosis.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT P.col_a AS patient_id, P.col_b AS age, E.col_c AS diagnosis
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_d < (SELECT AVG(col_d) FROM Examination);
```

### Q1238 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (HGB); predicted substitutes Examination for Laboratory -- filters Examination Date/aCL IgG (col_b/col_c) instead of Diagnosis='SLE' and HGB range, and the ORDER BY direction is also flipped (DESC instead of ASC).

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.col_a AS patient_id, P.col_b AS sex
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_b = 'SLE' AND E.col_c = 'Normal'
ORDER BY P.col_c DESC
LIMIT 1;
```

### Q1239 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Patient+Laboratory are both present (plus a vestigial Examination) but the HCT>=52 filter lands on Laboratory.GOT (col_c) instead of HCT (col_t); the HAVING COUNT>=2 structure is otherwise preserved.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.col_a AS patient_id, P.col_b AS age
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
JOIN Laboratory L ON E.col_a = L.col_a
WHERE L.col_c > 45 AND L.col_c < 60
GROUP BY P.col_a, P.col_b
HAVING COUNT(L.col_a) >= 2;
```

### Q1241 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's PLT thresholds (<100 / >400) live only on Laboratory; predicted queries Examination instead, comparing aCL IgG < aCL IgM (col_c/col_d) to itself rather than PLT to fixed thresholds.

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(*) AS lower_than_normal,
    (SELECT COUNT(*) FROM Examination WHERE col_c < col_d) AS higher_than_normal
FROM Examination
WHERE col_c < col_d;
```

### Q1242 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Patient+Laboratory are both present (plus a vestigial Examination) but the 1984 date filter lands on Examination.aCL IgM (col_d) instead of Laboratory.Date, age<50 lands on Patient.First Date (col_e), and the PLT range lands on Laboratory.'U-PRO' (col_ab) instead of PLT (col_u).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.col_a, P.col_b, P.col_c
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
JOIN Laboratory L ON E.col_a = L.col_a
WHERE E.col_d = '1984'
AND P.col_e < 50
AND L.col_ab = 'Normal';
```

### Q1243 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (PT); predicted substitutes Examination for Laboratory -- filters aCL IgM (col_d) instead of PT>=14, and SEX='F' lands on Patient.First Date (col_e) instead of SEX (col_b); age>55 also drops the STRFTIME computation for a raw Birthday>55 comparison.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN P.col_e = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage_female_abnormal_pt
FROM 
    Patient P
JOIN 
    Examination E ON P.col_a = E.col_a
WHERE 
    P.col_c > 55 AND E.col_d = 'Abnormal';
```

### Q1247 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Tables and join key are correct (Patient, Laboratory) but SEX='M' lands on Birthday (col_c), FG thresholds land on Laboratory.UN (col_j), and WBC range lands on Laboratory.CRE (col_k).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(*)
FROM Patient p
JOIN Laboratory l ON p.col_a = l.col_a
WHERE p.col_c = 'male'
AND l.col_j = 'normal'
AND l.col_k = 'abnormal';
```

### Q1251 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's IGG>=2000 filter lives only on Laboratory; predicted queries Patient alone, comparing SEX (col_b) to its own average -- Laboratory missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_b > (SELECT AVG(col_b) FROM Patient);
```

### Q1252 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's IGG filter (Laboratory) and Symptoms filter (Examination) require a 3-table join; predicted queries Patient alone, comparing SEX/Birthday (col_b/col_c) to unrelated strings -- both required tables missing.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_b = 'normal' AND col_c = 'symptoms';
```

### Q1254 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's IGA BETWEEN 80 AND 500 filter lives only on Laboratory; predicted queries Patient alone, comparing Birthday (col_c) to 'normal' and Description (col_d) to a date -- Laboratory missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_c = 'normal' AND col_d > '1990-01-01';
```

### Q1255 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (IGM) grouped by Diagnosis; predicted queries Examination alone, filtering aCL IgG (col_c) and grouping by ANA (col_e) instead of Diagnosis -- neither needed table present.

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_e 
FROM Examination 
WHERE col_c = 'abnormal' 
GROUP BY col_e 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1256 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's CRP filter lives only on Laboratory; predicted substitutes Examination (which has no CRP field) via a NOT IN subquery, and the Description IS NULL filter is dropped entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_a NOT IN (SELECT col_a FROM Examination WHERE col_b = 'abnormal C-reactive protein');
```

### Q1257 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's CRE>=1.5 filter lives only on Laboratory; predicted queries Patient alone, comparing Birthday (col_c) to 'abnormal' and Description (col_d) to 70 instead of a computed age -- Laboratory missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_c = 'abnormal' AND col_d < 70;
```

### Q1265 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's RNP filter lives only on Laboratory; predicted queries Patient alone, comparing SEX (col_b) to 'normal' and Birthday (col_c) to 'admitted' instead of Admission (col_f) -- Laboratory missing entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_b = 'normal' AND col_c = 'admitted';
```

### Q1267 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's CTE needs Laboratory (SM) and Examination (Thrombosis) with no Patient table at all; predicted queries Patient alone, comparing SEX (col_b) to 'normal' and Birthday (col_c) to 'thrombosis' -- both required tables missing.

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
FROM Patient 
WHERE col_b = 'normal' AND col_c != 'thrombosis';
```

### Q1270 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (SC170) plus a correlated Examination check; predicted substitutes Examination for Laboratory as the primary join -- SC170 is never referenced, and SEX='F' lands on Patient.Birthday (col_c).

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
JOIN Examination e ON p.col_a = e.col_a 
WHERE e.col_b = 'normal' AND p.col_c = 'female' AND e.col_d IS NULL;
```

### Q1275 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Patient+Laboratory are both present (via subqueries) but SEX='M' lands on Patient.ID (col_a), and the CENTROMEA/SSB filters land on Laboratory.GOT/GPT/LDH (col_c/col_d/col_e) instead of CENTROMEA (col_ap) and SSB (col_ao).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_a = 'male' 
AND col_b IN (
    SELECT col_c 
    FROM Laboratory 
    WHERE col_d = 'anti-centromere' AND col_e = 'normal'
) 
AND col_c IN (
    SELECT col_c 
    FROM Laboratory 
    WHERE col_d = 'anti-SSB' AND col_e = 'normal'
);
```

### Q1281 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs Patient JOIN Laboratory (GOT); predicted substitutes Examination for Laboratory -- filters Examination Date/aCL IgG (col_b/col_c) instead of GOT>=60, and takes MIN(Birthday) instead of ORDER BY Birthday DESC LIMIT 1 (opposite end of the range).

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(P.col_c) 
FROM Patient P 
JOIN Examination E ON P.col_a = E.col_a 
WHERE E.col_b = 'glutamic oxaloacetic transaminase' AND E.col_c = 'abnormal';
```

### Q1302 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's CPK filter (Laboratory) and KCT/RVVT/LAC filter (Examination) require a 3-table join with Patient; predicted queries Examination alone, comparing aCL IgG/aCL IgM (col_c/col_d) to unrelated strings -- Patient and Laboratory both missing.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Examination 
WHERE col_c = 'normal' AND col_d = 'positive';
```

---

## toxicology (40 failures)

### Q195 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Table matches gold (bond) but both GROUP BY and SELECT use molecule_id (col_b) instead of bond_type (col_c).

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT bond_type, COUNT(bond_id) FROM bond GROUP BY bond_type ORDER BY COUNT(bond_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT col_b FROM bond GROUP BY col_b ORDER BY COUNT(*) DESC LIMIT 1;
```

### Q197 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** SELECT AVG(COUNT(*)) nests one aggregate directly inside another -- a misuse-of-aggregate-function construction error, independent of the col_a/col_b mapping.

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) 
FROM (
    SELECT col_a 
    FROM atom 
    WHERE col_b = 'O' 
    GROUP BY col_a
) AS oxygen_atoms;
```

### Q198 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's bond JOIN molecule (direct on molecule_id) is replaced with molecule JOIN connected JOIN bond via nonsensical bridging keys (molecule_id=atom_id, atom_id2=bond_id); molecule.label (col_b) and bond.bond_type (col_c) are the right columns, but the extra connected hop breaks the relationship entirely.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) 
FROM (
    SELECT COUNT(*) AS bond_count 
    FROM molecule 
    JOIN connected ON molecule.col_a = connected.col_a 
    JOIN bond ON connected.col_b = bond.col_a 
    WHERE molecule.col_b = 'carcinogenic' AND bond.col_c = 'single'
    GROUP BY molecule.col_a
)
```

### Q200 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (molecule, bond) but joined via molecule_id=bond_id (m.col_a=b.col_a) instead of molecule_id=molecule_id; bond_type/label also carry invented word values ('triple'/'carcinogenic') instead of the real codes ('#'/'+').

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT m.col_a, m.col_b 
FROM molecule m 
JOIN bond b ON m.col_a = b.col_a 
WHERE b.col_c = 'triple' AND m.col_b = 'carcinogenic';
```

### Q201 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (bond, atom) but joined via bond_id=atom_id (T1.col_a=T2.col_a) instead of molecule_id=molecule_id; bond_type also lands on molecule_id (col_b) with an invented value 'double'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.col_c = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM bond AS T1 
JOIN atom AS T2 ON T1.col_a = T2.col_a 
WHERE T1.col_b = 'double';
```

### Q206 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs atom JOIN connected (to resolve bond_id to element); predicted queries bond alone, filtering bond_type (col_c) against the bond_id literal -- neither needed table present.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT col_a, col_b, col_c 
FROM bond 
WHERE col_c = 'TR004_8_9';
```

### Q207 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs atom JOIN connected JOIN bond (3 tables) to reach element; predicted queries bond alone, returning bond_id (col_a) instead of atom.element.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT col_a FROM bond WHERE col_c = 'double'
```

### Q208 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's molecule.label (the GROUP BY/SELECT target) requires joining molecule; predicted queries atom alone, grouping/selecting molecule_id (col_b) instead -- molecule missing entirely.

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM atom 
WHERE col_c = 'hydrogen' 
GROUP BY col_b 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q212 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** The atom-molecule relationship is bridged via a NOT IN subquery comparing atom.atom_id to molecule.molecule_id (different ID spaces, col_a to col_a) instead of a proper molecule_id join; GROUP BY also lands on atom_id (col_a) instead of element (col_c).

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
SELECT col_a 
FROM atom 
WHERE col_a NOT IN (SELECT col_a FROM molecule WHERE col_b = 'carcinogenic') 
GROUP BY col_a 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### Q213 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs bond JOIN connected (to filter by atom pair); predicted queries bond alone, filtering bond_id/molecule_id (col_a/col_b) against the atom-id literals -- connected missing entirely.

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT col_c FROM bond WHERE col_a = 'TR004_8' AND col_b = 'TR004_20';
```

### Q215 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** The element='i'/'s' filters land on atom.molecule_id (col_b) instead of element (col_c); the bond subquery bridge (atom.atom_id IN bond.bond_id) is also wrong (should be molecule_id IN molecule_id) and the bond_type value is 'single' instead of '-'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(*) AS iodine_count, 
    (SELECT COUNT(*) FROM atom WHERE col_b = 'sulfur') AS sulfur_count 
FROM 
    atom 
WHERE 
    col_b = 'iodine' 
AND 
    col_a IN (SELECT col_a FROM bond WHERE col_c = 'single');
```

### Q218 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule.label (col_b) and atom.element (col_c) are the correct columns (just compared to invented word values 'carcinogenic'/'fluorine' instead of '+'/'f'), but the NOT IN subquery bridges molecule.molecule_id to atom.atom_id (col_a to col_a) instead of atom.molecule_id, comparing incompatible ID spaces.

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_b = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM molecule 
WHERE col_a NOT IN (SELECT col_a FROM atom WHERE col_c = 'fluorine');
```

### Q219 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's direct atom+molecule+bond join (all on molecule_id) is replaced with molecule JOIN connected JOIN bond via nonsensical bridging keys (molecule_id=atom_id, atom_id2=bond_id); atom is entirely absent, and bond_type carries an invented value 'triple' instead of '#'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond.col_c = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM molecule 
JOIN connected ON molecule.col_a = connected.col_a 
JOIN bond ON connected.col_b = bond.col_a;
```

### Q220 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is atom (element); predicted substitutes molecule -- filters/selects/orders on molecule.label (col_b) instead of atom.element throughout.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM molecule 
WHERE col_a = 'TR000' 
ORDER BY col_b ASC 
LIMIT 3;
```

### Q226 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is bond, filterable directly on molecule_id; predicted adds an unneeded molecule join via bond.bond_id=molecule.molecule_id (b.col_a=m.col_a, wrong key), and bond_type carries an invented value 'double' instead of '='.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage_double_bonds
FROM bond
JOIN molecule ON bond.col_a = molecule.col_a
WHERE molecule.col_b = 'TR008';
```

### Q227 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Table and column both match gold exactly (molecule.label, col_b) -- only the compared literal differs: the invented word 'carcinogenic' instead of the real code '+'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_b = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage
FROM molecule;
```

### Q228 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is atom, filterable directly on molecule_id; predicted adds two unneeded tables (connected, molecule) via a nonsensical bridging key (connected.bond_id=molecule.molecule_id), and element lands on atom.molecule_id (col_b) instead of element (col_c).

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN atom.col_b = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage
FROM 
    atom
JOIN 
    connected ON atom.col_a = connected.col_a
JOIN 
    molecule ON connected.col_c = molecule.col_a
WHERE 
    molecule.col_b = 'TR206';
```

### Q230 (challenging, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** SELECT col_b, col_c from molecule -- molecule has only 2 columns (col_a, col_b), so col_c is genuinely out of range and the query fails with 'no such column: col_c'; also the wrong table entirely (molecule instead of atom+molecule join).

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT col_b, col_c FROM molecule WHERE col_a = 'TR060'
```

### Q231 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_c' -- both bond and connected (both joined via a nonsensical bridging chain substituting for a direct bond.molecule_id filter) have a real column at position c (bond_type vs bond_id), and the unqualified bare col_c in the outer SELECT doesn't disambiguate.

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT col_c 
FROM bond 
JOIN connected ON bond.col_a = connected.col_a 
JOIN molecule ON connected.col_b = molecule.col_a 
WHERE molecule.col_b = 'TR010' 
GROUP BY bond.col_c 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q232 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's direct bond+molecule join (on molecule_id) is replaced with molecule JOIN connected JOIN bond via nonsensical bridging keys; bond_type/label carry invented/inverted values ('single' instead of '-', != 'carcinogenic' instead of ='-').

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.col_a 
FROM molecule m 
JOIN connected c ON m.col_a = c.col_a 
JOIN bond b ON c.col_b = b.col_a AND c.col_c = b.col_b 
WHERE b.col_c = 'single' AND m.col_b != 'carcinogenic' 
ORDER BY m.col_a ASC 
LIMIT 3;
```

### Q234 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is connected, filterable directly on atom_id/atom_id2; predicted adds two unneeded tables (molecule, bond) via a nonsensical bridging key (molecule.molecule_id=connected.atom_id), and filters bond.molecule_id/bond_type (col_b/col_c) against 12 instead of connected's own atom-id literal.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM molecule m 
JOIN connected c ON m.col_a = c.col_a 
JOIN bond b ON c.col_c = b.col_a 
WHERE m.col_b = 'TR009' AND (b.col_b = 12 OR b.col_c = 12);
```

### Q236 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs only bond JOIN connected (bond_id=bond_id); predicted adds an unneeded atom table and joins bond to connected via bond_id=atom_id (col_a=col_a) instead of bond_id=bond_id, then re-derives atom_id/atom_id2 through atom instead of using connected's own columns directly.

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT bond.col_c, atom.col_a, atom.col_b 
FROM bond 
JOIN connected ON bond.col_a = connected.col_a 
JOIN atom ON connected.col_b = atom.col_a 
WHERE bond.col_a = 'TR001_6_9';
```

### Q239 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Table and column both match gold exactly (connected.atom_id, col_a), but the SUBSTR(atom_id, -2)='19' suffix-match is replaced with a direct numeric equality atom_id=19 -- a transformation change, not just a literal change.

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM connected 
WHERE col_a = 19;
```

### Q240 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table is atom (element); predicted substitutes molecule, filtering molecule.label (col_b) against the molecule-id literal and selecting all of molecule's columns instead of atom.element.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT * FROM molecule WHERE col_b = 'TR004';
```

### Q242 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs atom (for the SUBSTR(atom_id,-2) range) JOIN molecule; predicted substitutes connected for atom via a nonsensical bridging key (molecule.molecule_id=connected.atom_id), so the range filter lands on connected.atom_id2 instead of atom.atom_id.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.col_b 
FROM molecule m 
JOIN connected c ON m.col_a = c.col_a 
WHERE c.col_b BETWEEN 21 AND 25 AND m.col_b = 'carcinogenic';
```

### Q243 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs atom JOIN connected (to relate two atoms via a shared bond); predicted substitutes bond joined twice to atom via nonsensical keys (bond.bond_id=atom.atom_id, bond.molecule_id=atom.atom_id) -- connected is entirely absent, and element filters land on atom.molecule_id (col_b).

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT bond.col_a, bond.col_b, bond.col_c 
FROM bond 
JOIN atom AS atom1 ON bond.col_a = atom1.col_a 
JOIN atom AS atom2 ON bond.col_b = atom2.col_a 
WHERE atom1.col_b = 'phosphorus' AND atom2.col_b = 'nitrogen';
```

### Q244 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (molecule, bond) but joined via molecule_id=bond_id (m.col_a=b.col_a) instead of molecule_id=molecule_id; bond_type/label (col_c/col_b) are otherwise the correct columns, just with an invented value 'double' instead of '='.

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
SELECT m.col_b 
FROM molecule m 
JOIN bond b ON m.col_a = b.col_a 
WHERE b.col_c = 'double' 
GROUP BY m.col_a 
ORDER BY COUNT(b.col_c) DESC 
LIMIT 1;
```

### Q245 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** Fails with 'ambiguous column name: col_c' -- both bond and atom (joined via a nonsensical bond_id=atom_id key substituting for the missing connected table) have a real column at position c (bond_type vs element), and the unqualified bare col_c in AVG() doesn't disambiguate.

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) 
FROM bond 
JOIN atom ON bond.col_a = atom.col_a 
WHERE atom.col_b = 'iodine';
```

### Q247 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's anti-join subquery needs connected.atom_id; predicted substitutes bond.bond_id (col_a) -- connected is entirely absent, and the outer SELECT also returns atom_id (col_a) instead of element.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT col_a FROM atom WHERE col_a NOT IN (SELECT col_a FROM bond)
```

### Q248 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs atom JOIN connected JOIN bond (3 tables); predicted adds an unneeded molecule table via a nonsensical bridging key (connected.atom_id2=molecule.molecule_id) and a wrong atom-bond key (atom_id=bond_id), while bond_type carries an invented value 'triple' instead of '#'.

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT atom.col_a 
FROM atom 
JOIN bond ON atom.col_a = bond.col_a 
JOIN connected ON atom.col_a = connected.col_a 
JOIN molecule ON connected.col_b = molecule.col_a 
WHERE molecule.col_b = 'TR041' AND bond.col_c = 'triple';
```

### Q249 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs connected JOIN atom (to resolve bond_id to element); predicted queries atom alone, filtering molecule_id (col_b) against the bond-id literal and returning atom_id (col_a) instead of element.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT col_a FROM atom WHERE col_b = 'TR144_8_19';
```

### Q253 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs bond JOIN connected JOIN atom (3 tables) to reach element; predicted queries bond alone, returning bond_id/molecule_id/bond_type instead of atom.element, with bond_type also carrying an invented value 'triple' instead of '#'.

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT col_a, col_b, col_c FROM bond WHERE col_c = 'triple'
```

### Q255 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's molecule.label (needed for the ratio) requires joining molecule; predicted queries bond alone, filtering molecule_id (col_b) against 'single' and treating bond_type (col_c) as if it held the label value -- molecule missing entirely.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond WHERE col_b = 'single'
```

### Q260 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table atom (with bond/atom subqueries) is replaced with atom JOIN bond JOIN molecule via a nonsensical bond_type=molecule_id key (bond.col_c=molecule.col_a); atom.element also lands on molecule_id (col_b).

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM atom 
JOIN bond ON atom.col_a = bond.col_a 
JOIN molecule ON bond.col_c = molecule.col_a 
WHERE bond.col_b = 'triple' AND (atom.col_b = 'phosphorus' OR atom.col_b = 'bromine');
```

### Q263 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's single table atom (with a molecule+bond subquery) is replaced entirely with bond alone -- atom (needed for element='cl') is completely absent, replaced by bond.bond_id (col_a) compared to the element string.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bond WHERE col_c = 'single')) AS chlorine_percentage
FROM bond
WHERE col_c = 'single' AND col_a = 'chlorine';
```

### Q268 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold needs connected JOIN atom (to resolve bond_id to element); predicted queries bond alone, filtering molecule_id (col_b) against the bond-id literal and returning bond_id (col_a) instead of element.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT col_a FROM bond WHERE col_b = 'TR001_10_11'
```

### Q273 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (atom, molecule) but joined via molecule_id=atom_id (molecule.col_a=atom.col_a) instead of molecule_id=molecule_id; element also lands on atom.molecule_id (col_b), and the label='+' filter is dropped entirely.

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM molecule)) AS percentage
FROM molecule
JOIN atom ON molecule.col_a = atom.col_a
WHERE atom.col_b = 'chlorine';
```

### Q281 (challenging, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (atom, molecule) but joined via atom_id=molecule_id (atom.col_a=molecule.col_a) instead of molecule_id=molecule_id; GROUP BY also uses molecule_id instead of element, with an unwarranted ORDER BY/LIMIT/OFFSET replacing gold's plain per-element grouping.

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT atom.col_c 
FROM atom 
JOIN molecule ON atom.col_a = molecule.col_a 
WHERE molecule.col_b = 'carcinogenic' 
GROUP BY molecule.col_a 
ORDER BY COUNT(*) 
LIMIT 1 OFFSET 3;
```

### Q282 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Gold's direct atom+molecule join (on molecule_id) is replaced with atom JOIN connected JOIN molecule via a nonsensical bridging key (connected.bond_id=molecule.molecule_id); element also lands on atom.molecule_id (col_b), and gold's per-group label is replaced with a hardcoded 'Hydrogen' literal.

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(*) * 1.0 / (SELECT COUNT(*) FROM molecule WHERE col_a = 'TR006')) AS ratio, 
    'Hydrogen' AS label 
FROM 
    atom 
JOIN 
    connected ON atom.col_a = connected.col_a 
JOIN 
    molecule ON connected.col_c = molecule.col_a 
WHERE 
    atom.col_b = 'H' AND molecule.col_a = 'TR006';
```

### Q327 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Same 2 tables as gold (molecule, atom) but joined via molecule_id=atom_id (m.col_a=a.col_a) instead of molecule_id=molecule_id; molecule.label (col_b) carries an invented value 'non-carcinogenic' instead of '-'.

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT m.col_a 
FROM molecule m 
JOIN atom a ON m.col_a = a.col_a 
WHERE m.col_b = 'non-carcinogenic' 
GROUP BY m.col_a 
HAVING COUNT(a.col_a) > 5;
```

---

