"""The offline question-answering engine.

How it works (in plain terms): every piece of knowledge you give the app -- a
Q&A pair or a passage from an uploaded document -- is turned into a numerical
"fingerprint" of the words it contains. When someone asks a question, we make a
fingerprint of the question and find the stored knowledge whose fingerprint is
most similar. We also do a fuzzy text comparison to catch wording differences.

This all runs on the local CPU using standard math libraries, so it is fast,
private, and completely free to operate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from . import storage


# Below this combined score we treat the match as "not confident enough" and
# tell the user we don't have a good answer rather than guessing.
CONFIDENCE_THRESHOLD = 0.18


@dataclass
class Item:
    """One searchable unit of knowledge."""

    kind: str          # "qa" or "document"
    match_text: str    # text we compare the question against
    answer: str        # what we show the user
    source: str        # human-readable origin label


class Engine:
    def __init__(self) -> None:
        self._items: list[Item] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._dirty = True

    def mark_dirty(self) -> None:
        """Call after knowledge changes so the index rebuilds on next ask."""
        self._dirty = True

    def _load_items(self) -> list[Item]:
        items: list[Item] = []

        for qa in storage.list_qa():
            # Match mostly on the question, but include the answer so related
            # wording still scores.
            match_text = f"{qa['question']} {qa['question']} {qa['answer']}"
            items.append(
                Item(
                    kind="qa",
                    match_text=match_text,
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
        if not self._items:
            self._vectorizer = None
            self._matrix = None
        else:
            self._vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
            )
            self._matrix = self._vectorizer.fit_transform(
                [it.match_text for it in self._items]
            )
        self._dirty = False

    def ask(self, question: str, top_k: int = 3) -> dict:
        if self._dirty:
            self._rebuild()

        question = (question or "").strip()
        if not question:
            return {"found": False, "message": "Please type a question."}

        if not self._items:
            return {
                "found": False,
                "message": (
                    "I don't have any knowledge yet. Add some Q&A pairs or "
                    "upload documents on the 'Manage Knowledge' tab first."
                ),
            }

        # Cosine similarity via TF-IDF.
        q_vec = self._vectorizer.transform([question])
        cosine = linear_kernel(q_vec, self._matrix).flatten()

        # Fuzzy string score (0..1) gives a boost when wording is close,
        # which helps short Q&A questions in particular.
        fuzzy = np.array(
            [
                fuzz.token_set_ratio(question, it.match_text[:400]) / 100.0
                for it in self._items
            ]
        )

        combined = 0.7 * cosine + 0.3 * fuzzy

        order = np.argsort(combined)[::-1]
        best_idx = int(order[0])
        best_score = float(combined[best_idx])

        results = []
        for idx in order[:top_k]:
            idx = int(idx)
            if combined[idx] <= 0:
                continue
            results.append(
                {
                    "answer": self._items[idx].answer,
                    "source": self._items[idx].source,
                    "kind": self._items[idx].kind,
                    "confidence": round(float(combined[idx]), 3),
                }
            )

        if best_score < CONFIDENCE_THRESHOLD or not results:
            return {
                "found": False,
                "message": (
                    "I couldn't find a confident answer for that. Try "
                    "rephrasing, or add it on the 'Manage Knowledge' tab."
                ),
                "suggestions": results,
            }

        top = results[0]
        return {
            "found": True,
            "answer": top["answer"],
            "source": top["source"],
            "kind": top["kind"],
            "confidence": top["confidence"],
            "alternatives": results[1:],
        }


# A single shared engine instance for the whole app.
engine = Engine()
