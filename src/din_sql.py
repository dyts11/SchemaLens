"""
din_sql.py

DIN-SQL style three-stage prompt pipeline for text-to-SQL.

Stages:
  1. Schema Linking  — identify which tables and columns the question needs.
  2. Classification  — label the query as EASY, NON-NESTED, or NESTED.
  3. SQL Generation  — produce SQL using the linked schema and complexity class.

Few-shot examples for each stage are derived automatically from existing
(question, gold_sql) pairs using annotate_example(), which parses the SQL to
extract referenced tables/columns and infers the complexity class — no manual
annotation required.

Stage outputs are parsed with light regex so the pipeline stays robust to
minor formatting deviations from the model.
"""

import re
from typing import Dict, List, Optional

from src.denormalization_notice import DENORMALIZATION_NOTICE

# ---------------------------------------------------------------------------
# SQL annotation — derives stage labels from gold SQL
# ---------------------------------------------------------------------------

def _extract_tables(sql: str) -> List[str]:
    """Tables referenced in FROM and JOIN clauses, deduplicated in order."""
    tokens = re.findall(r'\b(?:FROM|JOIN)\s+`?(\w+)`?', sql, re.IGNORECASE)
    seen: set = set()
    result: List[str] = []
    for t in tokens:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            result.append(t)
    return result


def _extract_columns(sql: str) -> List[str]:
    """
    Column identifiers extracted from the SQL, deduplicated in order.

    Captures backtick-quoted names (common in BIRD/SQLite) and dotted
    table.column references; skips SQL keywords and numeric literals.
    """
    backtick = re.findall(r'`([^`]+)`', sql)
    dotted   = re.findall(r'\b([A-Za-z_]\w*\.[A-Za-z_]\w*)\b', sql)
    seen: set = set()
    result: List[str] = []
    for col in backtick + dotted:
        key = col.lower()
        if key not in seen:
            seen.add(key)
            result.append(col)
    return result


def classify_sql_complexity(sql: str) -> str:
    """
    Classify SQL into a DIN-SQL complexity tier based on subquery depth.

    EASY       — single SELECT, no subqueries.
    NON-NESTED — subquery present, but at most one level of nesting.
    NESTED     — two or more levels of nested subqueries.
    """
    n_select = len(re.findall(r'\bSELECT\b', sql, re.IGNORECASE))
    if n_select <= 1:
        return "EASY"
    if n_select == 2:
        return "NON-NESTED"
    return "NESTED"


def annotate_example(question: str, sql: str) -> Dict:
    """
    Derive all DIN-SQL stage labels from a (question, gold_sql) pair.

    Returns a dict used as a typed few-shot example across all three stages.
    """
    return {
        "question":   question,
        "sql":        sql,
        "tables":     _extract_tables(sql),
        "columns":    _extract_columns(sql),
        "complexity": classify_sql_complexity(sql),
    }


def format_schema_links(tables: List[str], columns: List[str]) -> str:
    t_str = "[" + ", ".join(tables) + "]" if tables else "[]"
    c_str = "[" + ", ".join(columns) + "]" if columns else "[]"
    return f"tables: {t_str}\ncolumns: {c_str}"


# ---------------------------------------------------------------------------
# Stage 1 — Schema Linking
# ---------------------------------------------------------------------------

_SCHEMA_LINKING_TEMPLATE = """\
You are an expert SQL analyst. Given the database schema and a natural-language \
question, identify which tables and columns from the schema are needed to answer it.

Output exactly two lines:
tables: [table1, table2, ...]
columns: [col1, col2, ...]

Use only names that appear in the schema. If a column is referenced with a table \
prefix (e.g. T1.col), include just the column name.

### Schema:
{schema}

{examples_block}\
### Question:
{question}
tables:\
"""


def _format_schema_linking_examples(examples: List[Dict]) -> str:
    if not examples:
        return ""
    parts = []
    for ex in examples:
        links = format_schema_links(ex["tables"], ex["columns"])
        parts.append(f"Question: {ex['question']}\n{links}")
    return "### Examples:\n" + "\n\n".join(parts) + "\n\n"


def build_schema_linking_prompt(
    schema: str,
    question: str,
    examples: List[Dict],
) -> str:
    """Stage 1: ask the model which tables and columns are needed."""
    return _SCHEMA_LINKING_TEMPLATE.format(
        schema=schema,
        examples_block=_format_schema_linking_examples(examples),
        question=question,
    )


# ---------------------------------------------------------------------------
# Stage 2 — Classification
# ---------------------------------------------------------------------------

_CLASSIFICATION_TEMPLATE = """\
Classify the SQL query needed to answer the question as one of:
  EASY        — single table or simple join, no subqueries needed.
  NON-NESTED  — requires a subquery, but not nested within another subquery.
  NESTED      — requires subqueries nested inside other subqueries.

Output the class label only (EASY, NON-NESTED, or NESTED).

{examples_block}\
### Question:
{question}
Relevant schema links:
{schema_links}
Class:\
"""


def _format_classification_examples(examples: List[Dict]) -> str:
    if not examples:
        return ""
    parts = []
    for ex in examples:
        links = format_schema_links(ex["tables"], ex["columns"])
        parts.append(
            f"Question: {ex['question']}\n"
            f"Relevant schema links:\n{links}\n"
            f"Class: {ex['complexity']}"
        )
    return "### Examples:\n" + "\n\n".join(parts) + "\n\n"


def build_classification_prompt(
    question: str,
    schema_links: str,
    examples: List[Dict],
) -> str:
    """Stage 2: classify query complexity given the linked schema."""
    return _CLASSIFICATION_TEMPLATE.format(
        examples_block=_format_classification_examples(examples),
        question=question,
        schema_links=schema_links,
    )


# ---------------------------------------------------------------------------
# Stage 3 — SQL Generation
# ---------------------------------------------------------------------------

_SQL_GEN_TEMPLATE = """\
You are an expert SQLite assistant. Given the database schema, the relevant \
tables and columns, the query complexity class, and the question, write a \
single SQLite SELECT query that correctly answers the question.

Rules:
- Output the SQL query only — no explanation, no markdown, no code fences.
- Use only the tables and columns defined in the schema.
- Do not invent column or table names.
- For NON-NESTED queries: use a subquery where needed.
- For NESTED queries: break the problem into sub-problems, solve each with a \
subquery, then combine.

### Schema:
{schema}

{denorm_block}\
{examples_block}\
### Question:
{question}
Relevant tables and columns:
{schema_links}
Query type: {complexity}

### SQL:\
"""


def _format_sql_gen_examples(examples: List[Dict]) -> str:
    if not examples:
        return ""
    parts = []
    for ex in examples:
        links = format_schema_links(ex["tables"], ex["columns"])
        parts.append(
            f"Question: {ex['question']}\n"
            f"Relevant tables and columns:\n{links}\n"
            f"Query type: {ex['complexity']}\n"
            f"SQL: {ex['sql']}"
        )
    return "### Examples:\n" + "\n\n".join(parts) + "\n\n"


def build_sql_generation_prompt(
    schema: str,
    question: str,
    schema_links: str,
    complexity: str,
    examples: List[Dict],
    *,
    structural_level: Optional[int] = None,
    include_denorm_notice: bool = True,
) -> str:
    """
    Stage 3: generate SQL given linked schema and complexity class.

    For L1/L2 structural levels the denormalization notice is prepended
    (same behaviour as prompt_builder.build_prompt).
    """
    denorm_block = ""
    if structural_level in (1, 2) and include_denorm_notice:
        denorm_block = (
            f"### Schema Denormalization Notice:\n{DENORMALIZATION_NOTICE}\n\n"
        )
    return _SQL_GEN_TEMPLATE.format(
        schema=schema,
        denorm_block=denorm_block,
        examples_block=_format_sql_gen_examples(examples),
        question=question,
        schema_links=schema_links,
        complexity=complexity,
    )


# ---------------------------------------------------------------------------
# Output parsers — robust extraction from stage 1 and 2 responses
# ---------------------------------------------------------------------------

def parse_schema_links_output(llm_output: str) -> str:
    """
    Extract the 'tables: [...]\ncolumns: [...]' block from stage 1 output.

    Returns the raw output trimmed if the expected lines are not found,
    so stage 2/3 still receive something meaningful.
    """
    tables_match  = re.search(r'(tables\s*:.*)', llm_output, re.IGNORECASE)
    columns_match = re.search(r'(columns\s*:.*)', llm_output, re.IGNORECASE)
    if tables_match and columns_match:
        return tables_match.group(1).strip() + "\n" + columns_match.group(1).strip()
    return llm_output.strip()


def parse_complexity_output(llm_output: str) -> str:
    """
    Extract EASY / NON-NESTED / NESTED from stage 2 output.
    Defaults to NON-NESTED if no recognised label is found.
    """
    upper = llm_output.upper()
    if "NESTED" in upper and "NON" not in upper.split("NESTED")[0][-5:]:
        return "NESTED"
    if "NON-NESTED" in upper or "NON NESTED" in upper:
        return "NON-NESTED"
    if "EASY" in upper:
        return "EASY"
    if "NESTED" in upper:
        return "NON-NESTED"
    return "NON-NESTED"
