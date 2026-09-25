"""
prompt_builder.py

Assembles the full prompt string sent to the LLM for a single question
under a given schema condition.

L3-L6 use a minimal template (schema + question only).
L1-L2 add a Schema Denormalization Notice before the schema block.

Usage:
    from src.prompt_builder import build_prompt
    prompt = build_prompt(schema_string, question)
    prompt = build_prompt(schema_string, question, structural_level=2)
    prompt = build_prompt(schema_string, question, few_shot_examples=[("Q?", "SELECT ...")])
    prompt = build_prompt(schema_string, question, include_cot=True)
    prompt = build_prompt(schema_string, question, evidence="value1 refers to X")
"""

from typing import List, Optional, Tuple

from src.denormalization_notice import DENORMALIZATION_NOTICE

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_TEMPLATE = """\
You are an expert SQLite assistant. Given the database schema and the question \
below, write a single SQLite SELECT query that correctly answers the question.

Rules:
- Output the SQL query only — no explanation, no markdown, no code fences.
- Use only the tables and columns defined in the schema.
- Do not invent column or table names.

### Schema:
{schema}

{few_shot_block}### Question:
{question}

{evidence_block}{cot_block}### SQL:"""

_TEMPLATE_DENORMALIZED = """\
You are an expert SQLite assistant. Given the database schema and the question \
below, write a single SQLite SELECT query that correctly answers the question.

Rules:
- Output the SQL query only — no explanation, no markdown, no code fences.
- Use only the tables and columns defined in the schema.
- Do not invent column or table names.

### Schema Denormalization Notice:
{denormalization_notice}

### Schema:
{schema}

{few_shot_block}### Question:
{question}

{evidence_block}{cot_block}### SQL:"""

# Fixed chain-of-thought instruction block injected when include_cot=True.
# Based on QDecomp+InterCOL (Guo et al., EMNLP 2023 main track): question decomposition
# with interleaved schema grounding. Shown to outperform clause-by-clause CoT, which
# causes error propagation, and least-to-most prompting on Spider (+5.2 / +6.5 pts).
_COT_BLOCK = """\
### Query Writing Guide:
Before writing the SQL, work through the following steps internally:

1. Question decomposition — if the question is complex, break it into ordered \
sub-questions, each of which can be answered by a simpler SQL fragment. \
For straightforward questions, proceed directly to step 2.

2. Schema grounding — for each sub-question (or the question as a whole), \
explicitly identify:
   - Output columns: which table(column) pairs provide the values to return in SELECT.
   - Filter columns: which table(column) pairs correspond to constraints in the question. \
If Evidence is provided, apply its value mappings here to resolve the exact filter values.
   - Join columns: which foreign-key pairs link the required tables \
(format: table1(col) = table2(col)).
   - Grouping columns: which table(column) to GROUP BY if the question asks for \
per-group statistics.
   Use only names that appear in the schema; do not invent any.

3. SQL generation — using only the grounded elements from step 2, build the query \
in this order: filters and joins first (to narrow the working set), then aggregation \
and grouping, then ORDER BY / LIMIT only if the question explicitly asks for ranking \
or a specific number of results.

"""


def _format_few_shot_block(examples: List[Tuple[str, str]]) -> str:
    """Return a formatted '### Examples:' block, or empty string if no examples."""
    if not examples:
        return ""
    parts = [f"Question: {q}\nSQL: {sql}" for q, sql in examples]
    return "### Examples:\n" + "\n\n".join(parts) + "\n\n"


def _format_evidence_block(
    evidence: Optional[str],
    structural_level: Optional[int] = None,
    semantic_level: Optional[int] = None,
) -> str:
    """Return a formatted '### Evidence:' block, or empty string if no evidence.

    Appends a schema-mismatch warning when column or table names in the current
    schema differ from those used in the evidence (which is always written for the
    original 3NF database with original column names):
      - L1/L2 (structural_level 1 or 2): table structure is reorganised — strong warning.
      - S1/S2 (semantic_level 1 or 2) with L3+: same tables but columns are renamed.
    """
    if not evidence:
        return ""
    header = (
        "### Evidence:\n"
        "The following domain knowledge accompanies this question. "
        "It may define how specific values, categories, or terms in the question "
        "map to actual column values in the database (e.g. 'active means status = 1', "
        "'Male refers to sex = \\'M\\''), or provide other hints needed to write "
        "correct filters and conditions. Apply this information when constructing "
        "WHERE or HAVING clauses.\n"
    )
    if structural_level in (1, 2):
        warning = (
            "Important: this evidence was written for the original normalised database "
            "and its table and column names may not match the denormalised schema shown "
            "above. Use the evidence only to understand value semantics and domain-specific "
            "mappings (e.g. what a value means). Always use the schema above as the "
            "authoritative source for actual table and column names.\n"
        )
    elif semantic_level in (1, 2, 3):
        warning = (
            "Important: this evidence uses the original column names from the source "
            "database, which may differ from the column names in the schema shown above. "
            "Cross-reference the schema to find the correct current column name for any "
            "column mentioned in the evidence before writing filters or conditions.\n"
        )
    else:
        warning = ""
    return f"{header}{warning}{evidence}\n\n"


def build_prompt(
    schema: str,
    question: str,
    *,
    structural_level: Optional[int] = None,
    semantic_level: Optional[int] = None,
    include_denorm_notice: bool = True,
    few_shot_examples: Optional[List[Tuple[str, str]]] = None,
    include_cot: bool = False,
    evidence: Optional[str] = None,
) -> str:
    """
    Fill the prompt template with a schema string and a natural-language question.

    Args:
        schema: Output of SchemaBuilder.build(structural_level, semantic_level).
        question: Natural-language question from the BIRD dataset.
        structural_level: When 1 or 2, may include the denormalization notice (L1/L2).
                          L3-L6 and None use the standard template.
        semantic_level: Used to warn the LLM when evidence column names differ from
                        those in the current schema (S1/S2 rename columns).
        include_denorm_notice: If False, L1/L2 use the same template as L3-L6
                               (schema + question only, no notice block).
        few_shot_examples: Optional list of (question, sql) pairs inserted as
                           a '### Examples:' block before the target question.
                           Pass None or [] for zero-shot (default).
        include_cot: If True, prepend a step-by-step query writing guide before
                     the schema block.
        evidence: Optional hint string from the dataset (e.g. value mappings or
                  domain knowledge). When provided, inserted as a '### Evidence:'
                  block immediately before the question.

    Returns:
        The complete prompt string ready to be sent to the LLM.
    """
    cot_block = _COT_BLOCK if include_cot else ""
    few_shot_block = _format_few_shot_block(few_shot_examples or [])
    evidence_block = _format_evidence_block(evidence, structural_level, semantic_level)

    if structural_level in (1, 2) and include_denorm_notice:
        return _TEMPLATE_DENORMALIZED.format(
            cot_block=cot_block,
            denormalization_notice=DENORMALIZATION_NOTICE,
            schema=schema,
            few_shot_block=few_shot_block,
            evidence_block=evidence_block,
            question=question,
        )
    return _TEMPLATE.format(
        cot_block=cot_block,
        schema=schema,
        few_shot_block=few_shot_block,
        evidence_block=evidence_block,
        question=question,
    )
