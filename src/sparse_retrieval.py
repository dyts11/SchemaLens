"""
sparse_retrieval.py

Sparse (BM25) retrieval of few-shot examples for text-to-SQL.

Same role and interface as dense_retrieval.py, but scoring is lexical/
statistical (Okapi BM25 over tokenized question text) instead of neural
sentence embeddings — the classic "sparse vector" IR baseline, no encoder
model or embedding cache required.

Retrieval scope: same db_id only, so examples always reference the same
database schema the model is working with.

Leakage guard: question_ids present in the test set are excluded from the
pool at SparseRetriever construction time (same guarantee as DenseRetriever
— see dense_retrieval.py docstring).

Usage:
    pool      = load_pool("dev_20240627/dev.json")
    retriever = build_retriever(pool, exclude_ids=reserved_ids)
    examples  = retriever.retrieve(question, db_id, k=3)
    # → List[Tuple[str, str]]  compatible with build_prompt(few_shot_examples=...)
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from rank_bm25 import BM25Okapi

from src.dense_retrieval import load_pool  # re-exported: generic dev.json loader

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokenizer shared by BM25 indexing and querying."""
    return _TOKEN_RE.findall(text.lower())


class SparseRetriever:
    """
    Retrieves the k most similar (question, SQL) pairs from a fixed pool via
    BM25, restricted to the same db_id as the query, excluding reserved
    question_ids. One BM25 index is built per db_id at construction time.
    """

    def __init__(
        self,
        pool: List[dict],
        exclude_ids: Optional[Set[int]] = None,
    ):
        self._pool = pool
        self._exclude_ids = exclude_ids or set()

        self._by_db: Dict[str, List[int]] = {}
        for i, rec in enumerate(pool):
            if int(rec["question_id"]) in self._exclude_ids:
                continue
            self._by_db.setdefault(rec["db_id"], []).append(i)

        self._bm25_by_db: Dict[str, BM25Okapi] = {}
        for db_id, indices in self._by_db.items():
            corpus = [_tokenize(pool[i]["question"]) for i in indices]
            self._bm25_by_db[db_id] = BM25Okapi(corpus)

    def retrieve(
        self,
        question: str,
        db_id: str,
        k: int,
        exclude_question_id: Optional[int] = None,
    ) -> List[Tuple[str, str]]:
        """
        Return up to k (question, SQL) pairs from the same db_id, ordered by
        descending BM25 score. The query question itself is excluded if its
        question_id is provided.
        """
        indices = self._by_db.get(db_id)
        if not indices:
            return []

        bm25 = self._bm25_by_db[db_id]
        scores = bm25.get_scores(_tokenize(question))  # aligned with `indices`

        pairs = list(zip(scores, indices))
        if exclude_question_id is not None:
            pairs = [
                (s, i) for s, i in pairs
                if int(self._pool[i]["question_id"]) != exclude_question_id
            ]
        if not pairs:
            return []

        pairs.sort(key=lambda x: (-x[0], x[1]))  # score desc, stable tie-break
        top = pairs[:k]

        return [(self._pool[i]["question"], self._pool[i]["SQL"]) for _, i in top]


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_retriever(
    pool: List[dict],
    *,
    exclude_ids: Optional[Set[int]] = None,
) -> SparseRetriever:
    """
    Build a SparseRetriever over the pool (one BM25 index per db_id).

    Args:
        pool:        Output of load_pool().
        exclude_ids: question_ids to exclude (your test set's ids).
    """
    print(f"Sparse retrieval: building BM25 index over {len(pool)} pool questions…")
    return SparseRetriever(pool, exclude_ids=exclude_ids)
