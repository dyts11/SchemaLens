"""
dense_retrieval.py

Dense retrieval of few-shot examples for text-to-SQL.

For each test question, the k most similar questions from a pool (dev.json)
are retrieved by cosine similarity of sentence embeddings and used as few-shot
examples in the prompt — same interface as the fixed few-shot approach.

Retrieval scope: same db_id only, so examples always reference the same
database schema the model is working with.

Leakage guard: question_ids present in the test set are excluded from the
pool at DenseRetriever construction time.

Usage:
    pool     = load_pool("dev_20240627/dev.json")
    retriever = build_retriever(pool, exclude_ids=reserved_ids,
                                cache_dir="dev_20240627/embeddings_cache")
    examples  = retriever.retrieve(question, db_id, k=3)
    # → List[Tuple[str, str]]  compatible with build_prompt(few_shot_examples=...)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Pool loading
# ---------------------------------------------------------------------------

def load_pool(dev_json_path: str) -> List[dict]:
    """Load the example pool from a BIRD-format dev.json."""
    with open(dev_json_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _cache_filename(texts: List[str], model_name: str) -> str:
    """Deterministic filename based on content + model so cache is invalidated on change."""
    h = hashlib.md5((model_name + "".join(texts)).encode()).hexdigest()[:12]
    safe_model = model_name.replace("/", "_").replace("-", "_")
    return f"embeddings_{safe_model}_{h}.npy"


def _embed(
    texts: List[str],
    model_name: str = _MODEL_NAME,
    batch_size: int = 128,
    cache_path: Optional[Path] = None,
) -> np.ndarray:
    """
    Encode texts into L2-normalised embeddings.
    If cache_path exists, load from disk; otherwise encode and save.
    """
    if cache_path is not None and cache_path.exists():
        return np.load(str(cache_path))

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    embeddings = embeddings.astype(np.float32)

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(cache_path), embeddings)
        print(f"  Saved embedding cache: {cache_path}")

    return embeddings


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class DenseRetriever:
    """
    Retrieves the k most similar (question, SQL) pairs from a fixed pool,
    restricted to the same db_id as the query, excluding reserved question_ids.
    """

    def __init__(
        self,
        pool: List[dict],
        embeddings: np.ndarray,
        model_name: str = _MODEL_NAME,
        exclude_ids: Optional[Set[int]] = None,
    ):
        self._pool = pool
        self._embeddings = embeddings  # (N, D), L2-normalised
        self._model_name = model_name
        self._exclude_ids = exclude_ids or set()
        self._encoder = None  # lazy-loaded for query encoding

        # Build per-db_id candidate index (list of row indices into pool/embeddings)
        self._by_db: Dict[str, List[int]] = {}
        for i, rec in enumerate(pool):
            if int(rec["question_id"]) in self._exclude_ids:
                continue
            self._by_db.setdefault(rec["db_id"], []).append(i)

    def _encode_query(self, text: str) -> np.ndarray:
        """Encode a single query string, reusing the loaded encoder."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self._model_name)
        vec = self._encoder.encode(
            [text], normalize_embeddings=True, convert_to_numpy=True
        )
        return vec[0].astype(np.float32)

    def retrieve(
        self,
        question: str,
        db_id: str,
        k: int,
        exclude_question_id: Optional[int] = None,
    ) -> List[Tuple[str, str]]:
        """
        Return up to k (question, SQL) pairs from the same db_id, ordered by
        descending cosine similarity. The query question itself is excluded if
        its question_id is provided.
        """
        candidates = list(self._by_db.get(db_id, []))
        if exclude_question_id is not None:
            candidates = [
                i for i in candidates
                if int(self._pool[i]["question_id"]) != exclude_question_id
            ]
        if not candidates:
            return []

        query_vec = self._encode_query(question)
        cand_embs = self._embeddings[candidates]          # (M, D)
        scores = cand_embs @ query_vec                    # cosine similarity

        top_k = min(k, len(candidates))
        top_indices = np.argpartition(-scores, top_k - 1)[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]  # sort descending

        return [
            (self._pool[candidates[i]]["question"], self._pool[candidates[i]]["SQL"])
            for i in top_indices
        ]


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_retriever(
    pool: List[dict],
    *,
    exclude_ids: Optional[Set[int]] = None,
    cache_dir: Optional[str] = None,
    model_name: str = _MODEL_NAME,
    batch_size: int = 128,
) -> DenseRetriever:
    """
    Embed the pool (or load from cache) and return a DenseRetriever.

    Args:
        pool:        Output of load_pool().
        exclude_ids: question_ids to exclude (your test set's ids).
        cache_dir:   Directory for the .npy embedding cache. Pass None to
                     skip caching (embeddings are recomputed each run).
        model_name:  Sentence-transformers model to use.
        batch_size:  Encoding batch size.
    """
    texts = [rec["question"] for rec in pool]

    cache_path: Optional[Path] = None
    if cache_dir is not None:
        fname = _cache_filename(texts, model_name)
        cache_path = Path(cache_dir) / fname

    print(f"Dense retrieval: embedding {len(texts)} pool questions with {model_name}…")
    embeddings = _embed(texts, model_name=model_name, batch_size=batch_size, cache_path=cache_path)
    print(f"  Pool embeddings shape: {embeddings.shape}")

    return DenseRetriever(pool, embeddings, model_name=model_name, exclude_ids=exclude_ids)
