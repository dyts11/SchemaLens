"""
prompt_builder.py

Assembles the full prompt string sent to the LLM for a single question
under a given schema condition.

The template is intentionally minimal and held CONSTANT across all 24
experimental conditions — only the {schema} block changes between conditions,
and {question} changes per question. This ensures that any accuracy differences
are attributable solely to the schema representation.

Usage:
    from src.prompt_builder import build_prompt
    prompt = build_prompt(schema_string, question)
"""

# ---------------------------------------------------------------------------
# Prompt template — do not modify between experimental conditions
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


def build_prompt(schema: str, question: str) -> str:
    """
    Fill the prompt template with a schema string and a natural-language question.

    Args:
        schema  : Output of SchemaBuilder.build(structural_level, semantic_level).
        question: Natural-language question from the BIRD dataset.

    Returns:
        The complete prompt string ready to be sent to the LLM.
    """
    return _TEMPLATE.format(schema=schema, question=question)
