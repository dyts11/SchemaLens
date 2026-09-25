"""
reflexion.py

Prompt builders for the Reflexion self-correction loop.

Two-step correction per round:
  1. Reflection: given the original task, the failed SQL, and feedback,
     ask the model to verbally diagnose what went wrong (no SQL yet).
  2. Correction: given the original task, the failed SQL, the feedback,
     and the reflection, ask the model to write corrected SQL.

Feedback for each outcome type:
  - "error"       : the SQLite error message from result.error_msg, with
                    a note on the most common causes of that error class
  - "wrong_answer": binary signal only (no gold leakage), augmented with
                    a checklist of the most common wrong-answer causes in
                    text-to-SQL — mirrors Reflexion's reasoning-task approach
                    where the evaluator provides pass/fail without revealing
                    the correct answer
"""

from typing import Optional

# Common wrong-answer causes listed explicitly because the model has no other
# signal — it only knows the query ran without error but returned wrong results.
_WRONG_ANSWER_CAUSES = """\
- A JOIN that introduces duplicate rows (use DISTINCT or COUNT(DISTINCT ...) if needed)
- A missing DISTINCT on key column in the SELECT clause column or during filtering or other processing
- A wrong JOIN condition or JOIN type (INNER vs LEFT) that includes or excludes the wrong rows
- A WHERE or HAVING predicate that filters on the wrong column, wrong value, or wrong operator
- A missing or incorrect GROUP BY that groups on the wrong key
- The wrong aggregation function (e.g. SUM instead of COUNT, COUNT(*) instead of COUNT(DISTINCT ...))
- Selecting the wrong column or expression in the result
- A subquery that returns the wrong set of values"""


def get_feedback(outcome: str, error_msg: Optional[str]) -> str:
    """
    Return a feedback string for the reflection and correction prompts.

    For execution errors the SQLite message is included directly; for wrong
    answers a structured list of common causes is provided since no further
    signal is available without leaking the gold answer.
    """
    if outcome == "error" and error_msg:
        return (
            f"Your SQL failed to execute with the following error:\n"
            f"  {error_msg}\n\n"
            f"Common causes of this error type: a column or table name that does "
            f"not match the schema exactly (check capitalisation and underscores), "
            f"a syntax mistake (missing comma, unmatched parenthesis, wrong keyword), "
            f"or referencing a column that is ambiguous across joined tables."
        )
    return (
        f"Your SQL executed without error but returned incorrect results.\n\n"
        f"Common causes in text-to-SQL:\n{_WRONG_ANSWER_CAUSES}"
    )


def build_reflection_prompt(
    original_prompt: str,
    predicted_sql: str,
    feedback: str,
) -> str:
    """
    Ask the model to diagnose why its SQL was wrong before attempting a fix.

    The original_prompt (from build_prompt()) already contains the full schema
    and question. This function appends the failed SQL, structured feedback, and
    a guided diagnostic checklist, then asks for a verbal reflection only.
    """
    return (
        f"{original_prompt}"
        f"{predicted_sql}\n\n"
        f"The above SQL is incorrect.\n\n"
        f"### Feedback:\n"
        f"{feedback}\n\n"
        f"### Diagnosis task:\n"
        f"Work through the following steps before writing any SQL:\n\n"
        f"1. Re-read the question carefully. What entities, conditions, and output "
        f"does it require? Is there an aggregation, a filter, a ranking, or a join "
        f"across multiple tables?\n\n"
        f"2. Trace through each clause of your SQL:\n"
        f"   - FROM / JOIN: do the joined tables and conditions produce the right rows "
        f"with no unintended duplicates?\n"
        f"   - WHERE / HAVING: do the filters exactly match the conditions in the question?\n"
        f"   - SELECT: are the correct columns or aggregations returned?\n"
        f"   - GROUP BY / ORDER BY / LIMIT: are these present and correct where needed?\n\n"
        f"3. State the specific mistake and how to fix it.\n\n"
        f"Do not write SQL yet — explain the diagnosis only.\n\n"
        f"### Reflection:"
    )


def build_correction_prompt(
    original_prompt: str,
    predicted_sql: str,
    feedback: str,
    reflection: str,
) -> str:
    """
    Ask the model to produce a corrected SQL query guided by its own reflection.

    The full original task (schema + question) is included again so the model
    can re-read the schema without relying on memory.
    """
    return (
        f"{original_prompt}"
        f"{predicted_sql}\n\n"
        f"The above SQL is incorrect.\n\n"
        f"### Feedback:\n"
        f"{feedback}\n\n"
        f"### Your reflection:\n"
        f"{reflection}\n\n"
        f"### Correction task:\n"
        f"Write the corrected SQL query following your reflection above. "
        f"Before finalising your answer, verify:\n"
        f"- Every table and column name exactly matches the schema shown above\n"
        f"- JOINs are on the correct keys and produce no unintended duplicate rows\n"
        f"- DISTINCT or COUNT(DISTINCT ...) is used wherever duplicates are possible\n"
        f"- WHERE / HAVING conditions precisely match the question requirements\n"
        f"- The SELECT clause returns exactly what the question asks for\n\n"
        f"Output the SQL query only — no explanation, no markdown, no code fences.\n\n"
        f"### Corrected SQL:"
    )
