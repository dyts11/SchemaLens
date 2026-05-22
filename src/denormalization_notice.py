"""
Text block appended to L1/L2 prompts (denormalised 1NF / 2NF materialised schemas).
"""

DENORMALIZATION_NOTICE = """\
## Schema Denormalization Notice

The database schema provided is in a denormalized form. Tables have been \
constructed by joining multiple normalized entities together, which means \
a single logical record (e.g. one race result, one driver) may appear \
across multiple rows due to join redundancy. You must account for this \
when writing SQL to avoid returning inflated or incorrect results.

The rules below tell you exactly how to handle this for each query type.

---

## 1. Retrieval Queries (SELECT without aggregation)

Retrieval queries return rows of values — names, IDs, descriptions, dates.

RULE: Always use SELECT DISTINCT when retrieving any column or combination \
of columns, unless the question explicitly asks for all occurrences \
including repetitions.

Examples:
  Question: "List the names of all drivers who competed in race 5."
  Wrong:   SELECT driver_name FROM results_flat WHERE race_id = 5
  Correct: SELECT DISTINCT driver_name FROM results_flat WHERE race_id = 5

  Question: "What circuits have hosted a race?"
  Wrong:   SELECT circuit_name FROM results_flat
  Correct: SELECT DISTINCT circuit_name FROM results_flat

When to NOT use DISTINCT on retrieval:
  - The question asks for all rows explicitly, e.g. "list every lap time \
    recorded" — in this case repetition may be expected.
  - The question includes an ORDER BY with LIMIT and you are retrieving \
    a specific ranked row — DISTINCT may change ranking behaviour.

---

## 2. COUNT Queries

COUNT queries count how many things exist. This is the most error-prone \
query type on denormalized schemas. You must identify what entity is \
being counted and apply DISTINCT to that entity's primary identifier.

RULE: Always use COUNT(DISTINCT <entity_id>) rather than COUNT(*) \
or COUNT(<column>), where <entity_id> is the primary key of the \
logical entity the question is asking about.

Examples:
  Question: "How many drivers competed in race 5?"
  Wrong:   SELECT COUNT(*) FROM results_flat WHERE race_id = 5
  Wrong:   SELECT COUNT(driver_id) FROM results_flat WHERE race_id = 5
  Correct: SELECT COUNT(DISTINCT driver_id) FROM results_flat WHERE race_id = 5

  Question: "How many races has Hamilton participated in?"
  Wrong:   SELECT COUNT(*) FROM results_flat WHERE driver_name = 'Hamilton'
  Correct: SELECT COUNT(DISTINCT race_id) FROM results_flat \
           WHERE driver_name = 'Hamilton'

  Question: "How many results were recorded with more than 5 points?"
  Correct: SELECT COUNT(DISTINCT result_id) FROM results_flat \
           WHERE points > 5

Identifying which entity_id to use:
  - If counting people/drivers/teams → DISTINCT on driver_id or team_id
  - If counting events/races/games  → DISTINCT on race_id or event_id
  - If counting records/results     → DISTINCT on result_id
  - If counting laps                → lap rows are the atomic unit; \
    COUNT(*) may be appropriate if laps themselves are what is counted

---

## 3. SUM and AVG Queries

SUM and AVG are the most dangerous query types on denormalized schemas. \
A simple SUM(points) will add up points once per row, but each logical \
result may appear many times (once per lap), inflating the total massively. \
DISTINCT cannot be applied directly inside SUM or AVG.

RULE: Always deduplicate using a subquery before applying SUM or AVG. \
The subquery should SELECT DISTINCT on the primary key of the entity \
whose attribute you are aggregating, along with the attribute column.

Template:
  SELECT SUM(col) / AVG(col)
  FROM (
    SELECT DISTINCT <entity_id>, <col>
    FROM <table>
    WHERE <condition>
  )

Examples:
  Question: "What is the total points scored by Hamilton?"
  Wrong:   SELECT SUM(points) FROM results_flat \
           WHERE driver_name = 'Hamilton'
           -- Inflated: sums points once per lap row

  Correct: SELECT SUM(points) \
           FROM (
             SELECT DISTINCT result_id, points \
             FROM results_flat \
             WHERE driver_name = 'Hamilton'
           )

  Question: "What is the average points per race in the 2020 season?"
  Correct: SELECT AVG(points)
           FROM (
             SELECT DISTINCT result_id, points
             FROM results_flat
             WHERE race_year = 2020
           )

---

## 4. GROUP BY Queries

GROUP BY queries aggregate within groups — e.g. total points per driver, \
number of races per year. On denormalized schemas, GROUP BY alone does \
not deduplicate — it groups all rows including duplicates.

RULE: When using GROUP BY, either:
  (a) Apply COUNT(DISTINCT <entity_id>) inside the aggregation, or
  (b) Deduplicate with a subquery before grouping

Examples:
  Question: "How many races did each driver compete in?"
  Wrong:   SELECT driver_name, COUNT(*) FROM results_flat GROUP BY driver_name
  Correct: SELECT driver_name, COUNT(DISTINCT race_id) \
           FROM results_flat GROUP BY driver_name

  Question: "What is the total points per driver in the 2020 season?"
  Wrong:   SELECT driver_name, SUM(points) FROM results_flat \
           WHERE race_year = 2020 GROUP BY driver_name
  Correct: SELECT driver_name, SUM(points) \
           FROM (
             SELECT DISTINCT result_id, driver_name, points \
             FROM results_flat WHERE race_year = 2020
           ) GROUP BY driver_name

---

## 5. MIN and MAX Queries

MIN and MAX are safe on denormalized schemas because taking the minimum \
or maximum of a repeated value returns the same result regardless of \
how many times the value appears.

RULE: No special handling needed for MIN and MAX. Use them normally.

Example:
  Question: "What is the fastest lap time recorded by Hamilton?"
  Correct: SELECT MIN(laptime) FROM laptimes_flat \
           WHERE driver_name = 'Hamilton'
  -- Safe: MIN of repeated values is unaffected by duplicates

---

## 6. EXISTS and IN Subqueries

EXISTS and IN check for the presence of a value, not its count. \
Duplicates do not affect correctness here.

RULE: No special handling needed for EXISTS or IN subqueries.

---

## Summary Reference

| Query type      | Rule                                              |
|-----------------|---------------------------------------------------|
| SELECT          | Always DISTINCT unless repetition is intended     |
| COUNT           | Always COUNT(DISTINCT entity_id)                  |
| SUM / AVG       | Deduplicate in subquery first, then aggregate     |
| GROUP BY        | Use COUNT(DISTINCT ...) or subquery deduplication |
| MIN / MAX       | Safe — no special handling needed                 |
| EXISTS / IN     | Safe — no special handling needed                 |
"""
