"""The offline search engine that finds the most relevant knowledge.

It runs in one of two modes, chosen automatically:

  * "embeddings" -- if the local AI (Ollama) has an embedding model available,
    we compare the *meaning* of the question to stored knowledge. Best quality.
  * "tfidf"      -- otherwise we fall back to keyword/term-frequency matching
    plus fuzzy text comparison. Always works, needs nothing extra.

Either way it returns ranked candidate passages. The server then either hands
those passages to the local AI to write a conversational answer, or (if AI is
off) returns the best passage directly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from . import ai, storage


# Minimum score to consider a passage relevant at all (mode-specific).
FLOOR = {"tfidf": 0.05, "embeddings": 0.25}

# When the AI is OFF we must be stricter, since we return the raw passage.
NO_AI_THRESHOLD = {"tfidf": 0.18, "embeddings": 0.45}


@dataclass
class Item:
    kind: str          # "qa" or "document"
    match_text: str    # text we compare the question against
    answer: str        # the passage we show / feed to the AI
    source: str        # human-readable origin label


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class Engine:
    def __init__(self) -> None:
        self._items: list[Item] = []
        self._mode = "tfidf"
        self._dirty = True

        # tfidf mode
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

        # embeddings mode
        self._embeddings: np.ndarray | None = None
        self._embed_cache: dict[str, list[float]] = {}

    @property
    def mode(self) -> str:
        return self._mode

    def mark_dirty(self) -> None:
        self._dirty = True

    # ------------------------------------------------------------------
    def _load_items(self) -> list[Item]:
        items: list[Item] = []
        for qa in storage.list_qa():
            items.append(
                Item(
                    kind="qa",
                    match_text=f"{qa['question']} {qa['question']} {qa['answer']}",
                    answer=qa["answer"],
                    source="Saved Q&A",
                )
            )
        for chunk in storage.all_chunks():
            items.append(
                Item(
                    kind="document",
                    match_text=chunk["text"],
                    answer=chunk["text"],
                    source=f"Document: {chunk['filename']}",
                )
            )
        return items

    def _rebuild(self) -> None:
        self._items = self._load_items()
        self._vectorizer = None
        self._matrix = None
        self._embeddings = None

        if not self._items:
            self._mode = "embeddings" if ai.embeddings_available() else "tfidf"
            self._dirty = False
            return

        if ai.embeddings_available() and self._build_embeddings():
            self._mode = "embeddings"
        else:
            self._build_tfidf()
            self._mode = "tfidf"

        self._dirty = False

    def _build_tfidf(self) -> None:
        self._vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        )
        self._matrix = self._vectorizer.fit_transform(
            [it.match_text for it in self._items]
        )

    def _build_embeddings(self) -> bool:
        """Embed any not-yet-cached items, then assemble the matrix.

        Returns False if embedding fails, so we can fall back to tf-idf.
        """
        texts = [it.match_text[:2000] for it in self._items]
        missing = [t for t in texts if _hash(t) not in self._embed_cache]
        if missing:
            vectors = ai.embed(missing)
            if vectors is None:
                return False
            for text, vec in zip(missing, vectors):
                self._embed_cache[_hash(text)] = vec

        try:
            matrix = np.array([self._embed_cache[_hash(t)] for t in texts], dtype=float)
        except KeyError:
            return False

        # Normalize for cosine similarity via dot product.
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._embeddings = matrix / norms
        return True

    # ------------------------------------------------------------------
    def _scores(self, question: str) -> np.ndarray | None:
        if self._mode == "embeddings" and self._embeddings is not None:
            qv = ai.embed([question])
            if not qv:
                return None
            q = np.array(qv[0], dtype=float)
            n = np.linalg.norm(q) or 1.0
            cosine = self._embeddings @ (q / n)
        else:
            if self._vectorizer is None:
                return None
            q_vec = self._vectorizer.transform([question])
            cosine = linear_kernel(q_vec, self._matrix).flatten()

        fuzzy = np.array(
            [
                fuzz.token_set_ratio(question, it.match_text[:400]) / 100.0
                for it in self._items
            ]
        )
        return 0.75 * cosine + 0.25 * fuzzy

    def search(self, question: str, top_k: int = 4) -> dict:
        """Return ranked candidate passages for a question."""
        if self._dirty:
            self._rebuild()

        question = (question or "").strip()
        result = {"mode": self._mode, "has_items": bool(self._items), "candidates": []}
        if not question or not self._items:
            return result

        scores = self._scores(question)
        if scores is None:
            # Embedding the query failed; rebuild as tf-idf and retry once.
            self._mode = "tfidf"
            self._build_tfidf()
            scores = self._scores(question)
            result["mode"] = self._mode
            if scores is None:
                return result

        order = np.argsort(scores)[::-1]
        candidates = []
        for idx in order[:top_k]:
            idx = int(idx)
            if scores[idx] <= 0:
                continue
            candidates.append(
                {
                    "answer": self._items[idx].answer,
                    "source": self._items[idx].source,
                    "kind": self._items[idx].kind,
                    "confidence": round(float(scores[idx]), 3),
                }
            )
        result["candidates"] = candidates
        return result

    # Thresholds for the current mode -------------------------------------
    def floor(self) -> float:
        return FLOOR.get(self._mode, 0.05)

    def no_ai_threshold(self) -> float:
        return NO_AI_THRESHOLD.get(self._mode, 0.18)


engine = Engine()
