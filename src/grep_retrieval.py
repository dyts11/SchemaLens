"""
grep_retrieval.py

Naive lexical-overlap ("grep") retrieval of few-shot examples for text-to-SQL.

Same role and interface as dense_retrieval.py / sparse_retrieval.py, but
scoring has no term weighting at all: a candidate's score is just the count
of distinct query words that also appear in the candidate question — the
"grep -c" of retrieval, with no TF-IDF/BM25 rarity weighting and no neural
encoder. Intended as the naive floor of the retrieval-sophistication ladder
(dense > sparse > grep).

Retrieval scope: same db_id only, so examples always reference the same
database schema the model is working with.

Leakage guard: question_ids present in the test set are excluded from the
pool at GrepRetriever construction time (same guarantee as DenseRetriever
— see dense_retrieval.py docstring).

Usage:
    pool      = load_pool("dev_20240627/dev.json")
    retriever = build_retriever(pool, exclude_ids=reserved_ids)
    examples  = retriever.retrieve(question, db_id, k=3)
    # → List[Tuple[str, str]]  compatible with build_prompt(few_shot_examples=...)
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from src.dense_retrieval import load_pool  # re-exported: generic dev.json loader

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> Set[str]:
    """Lowercase word tokenizer, returned as a set (grep cares about presence, not count)."""
    return set(_TOKEN_RE.findall(text.lower()))


class GrepRetriever:
    """
    Retrieves the k most similar (question, SQL) pairs from a fixed pool by
    literal word-overlap count, restricted to the same db_id as the query,
    excluding reserved question_ids.
    """

    def __init__(
        self,
        pool: List[dict],
        exclude_ids: Optional[Set[int]] = None,
    ):
        self._pool = pool
        self._exclude_ids = exclude_ids or set()

        self._by_db: Dict[str, List[int]] = {}
        self._tokens_by_idx: Dict[int, Set[str]] = {}
        for i, rec in enumerate(pool):
            if int(rec["question_id"]) in self._exclude_ids:
                continue
            self._by_db.setdefault(rec["db_id"], []).append(i)
            self._tokens_by_idx[i] = _tokenize(rec["question"])

    def retrieve(
        self,
        question: str,
        db_id: str,
        k: int,
        exclude_question_id: Optional[int] = None,
    ) -> List[Tuple[str, str]]:
        """
        Return up to k (question, SQL) pairs from the same db_id, ordered by
        descending shared-word count. The query question itself is excluded
        if its question_id is provided.
        """
        candidates = self._by_db.get(db_id)
        if not candidates:
            return []
        if exclude_question_id is not None:
            candidates = [
                i for i in candidates
                if int(self._pool[i]["question_id"]) != exclude_question_id
            ]
        if not candidates:
            return []

        query_tokens = _tokenize(question)
        scored = [
            (len(query_tokens & self._tokens_by_idx[i]), i) for i in candidates
        ]
        scored.sort(key=lambda x: (-x[0], x[1]))  # overlap desc, stable tie-break
        top = scored[:k]

        return [(self._pool[i]["question"], self._pool[i]["SQL"]) for _, i in top]


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_retriever(
    pool: List[dict],
    *,
    exclude_ids: Optional[Set[int]] = None,
) -> GrepRetriever:
    """
    Build a GrepRetriever over the pool.

    Args:
        pool:        Output of load_pool().
        exclude_ids: question_ids to exclude (your test set's ids).
    """
    print(f"Grep retrieval: indexing {len(pool)} pool questions by word overlap…")
    return GrepRetriever(pool, exclude_ids=exclude_ids)
