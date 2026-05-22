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
"""

from typing import Optional

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

### Question:
{question}

### SQL:"""

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

### Question:
{question}

### SQL:"""


def build_prompt(
    schema: str,
    question: str,
    *,
    structural_level: Optional[int] = None,
) -> str:
    """
    Fill the prompt template with a schema string and a natural-language question.

    Args:
        schema: Output of SchemaBuilder.build(structural_level, semantic_level).
        question: Natural-language question from the BIRD dataset.
        structural_level: When 1 or 2, include the denormalization notice (L1/L2).
                          L3-L6 and None use the standard template.

    Returns:
        The complete prompt string ready to be sent to the LLM.
    """
    if structural_level in (1, 2):
        return _TEMPLATE_DENORMALIZED.format(
            denormalization_notice=DENORMALIZATION_NOTICE,
            schema=schema,
            question=question,
        )
    return _TEMPLATE.format(schema=schema, question=question)
