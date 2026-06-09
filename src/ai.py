"""Local AI engine via Ollama (free, runs entirely on the host PC).

This module talks to a locally running Ollama server (default
http://127.0.0.1:11434). It is used for two things:

  1. Embeddings  -- turning text into vectors for smarter search.
  2. Generation  -- writing a natural, conversational answer that is
                    grounded in the knowledge we retrieved.

Everything degrades gracefully: if Ollama is not installed or not running,
every function reports "unavailable" and the app falls back to plain search.
No part of the program requires the internet or any paid service.

Configuration (optional environment variables):
  OLLAMA_HOST     - base URL of the Ollama server (default 127.0.0.1:11434)
  OA_CHAT_MODEL   - model used to write answers   (default llama3.1:8b)
  OA_EMBED_MODEL  - model used for embeddings      (default nomic-embed-text)
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = os.environ.get("OA_CHAT_MODEL", "llama3.1:8b")
EMBED_MODEL = os.environ.get("OA_EMBED_MODEL", "nomic-embed-text")

# How long to wait for the model to write an answer (generation can be slow).
GENERATE_TIMEOUT = 120
QUICK_TIMEOUT = 5

_SYSTEM_PROMPT = (
    "You are an operations assistant for a security systems company. "
    "Answer the user's question using ONLY the information in the provided "
    "context passages. Be concise, clear, and practical, as if briefing a "
    "coworker. If the context does not contain the answer, say you don't have "
    "that information yet and suggest they check with a manager or add it to "
    "the knowledge base. Never invent specifics such as part numbers, codes, "
    "phone numbers, prices, or procedures that are not in the context."
)


# --------------------------------------------------------------------------
# Low-level HTTP helpers (standard library only -- nothing extra to bundle)
# --------------------------------------------------------------------------
def _get(path: str, timeout: int):
    req = urllib.request.Request(OLLAMA_HOST + path, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, payload: dict, timeout: int):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_HOST + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# --------------------------------------------------------------------------
# Status (cached briefly so we don't probe Ollama on every keystroke)
# --------------------------------------------------------------------------
_status_cache: dict | None = None
_status_time = 0.0
_STATUS_TTL = 10.0


def _installed_models() -> list[str]:
    try:
        data = _get("/api/tags", QUICK_TIMEOUT)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return []
    return [m.get("name", "") for m in data.get("models", [])]


def _has_model(installed: list[str], wanted: str) -> bool:
    base = wanted.split(":")[0]
    return any(name == wanted or name.split(":")[0] == base for name in installed)


def status(force: bool = False) -> dict:
    """Return what the local AI can currently do."""
    global _status_cache, _status_time
    now = time.time()
    if not force and _status_cache is not None and (now - _status_time) < _STATUS_TTL:
        return _status_cache

    installed = _installed_models()
    reachable = bool(installed) or _ollama_reachable()
    info = {
        "reachable": reachable,
        "chat_model": CHAT_MODEL,
        "embed_model": EMBED_MODEL,
        "chat_ready": _has_model(installed, CHAT_MODEL),
        "embed_ready": _has_model(installed, EMBED_MODEL),
        "installed_models": installed,
    }
    _status_cache, _status_time = info, now
    return info


def _ollama_reachable() -> bool:
    try:
        _get("/api/version", QUICK_TIMEOUT)
        return True
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False


def invalidate_status() -> None:
    global _status_cache
    _status_cache = None


def generation_available() -> bool:
    return status().get("chat_ready", False)


def embeddings_available() -> bool:
    return status().get("embed_ready", False)


# --------------------------------------------------------------------------
# Embeddings
# --------------------------------------------------------------------------
def embed(texts: list[str]) -> list[list[float]] | None:
    """Return one embedding vector per input text, or None on any failure."""
    if not texts:
        return []
    # Newer Ollama: /api/embed accepts a list via "input".
    try:
        data = _post(
            "/api/embed",
            {"model": EMBED_MODEL, "input": texts},
            GENERATE_TIMEOUT,
        )
        vectors = data.get("embeddings")
        if vectors and len(vectors) == len(texts):
            return vectors
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        pass

    # Older Ollama fallback: /api/embeddings, one prompt at a time.
    out: list[list[float]] = []
    for text in texts:
        try:
            data = _post(
                "/api/embeddings",
                {"model": EMBED_MODEL, "prompt": text},
                GENERATE_TIMEOUT,
            )
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return None
        vec = data.get("embedding")
        if not vec:
            return None
        out.append(vec)
    return out


# --------------------------------------------------------------------------
# Generation (RAG: answer grounded in retrieved context)
# --------------------------------------------------------------------------
def generate(question: str, contexts: list[str]) -> str | None:
    """Write a conversational answer grounded in the given context passages.

    Returns the answer text, or None if generation is unavailable/failed so
    the caller can fall back to plain search results.
    """
    if not generation_available():
        return None

    numbered = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
    user_msg = (
        f"Question: {question}\n\n"
        f"Context passages:\n{numbered if numbered else '(none provided)'}"
    )

    try:
        data = _post(
            "/api/chat",
            {
                "model": CHAT_MODEL,
                "stream": False,
                "options": {"temperature": 0.2},
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            },
            GENERATE_TIMEOUT,
        )
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None

    message = data.get("message") or {}
    answer = (message.get("content") or "").strip()
    return answer or None
