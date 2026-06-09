"""Flask web server that powers the Operations Assistant.

Runs on the HOST PC and is reachable by everyone on the local network at
http://<host>:8731. There is a single shared knowledge base.

Access rules:
  * Anyone on the network can ASK questions.
  * Adding / editing / deleting knowledge is allowed only from the host machine
    itself (i.e. requests coming from localhost). This enforces "managed on the
    host" without needing passwords. Remote users get an ask-only interface.
"""

from __future__ import annotations

import functools
import os
import sys

from flask import Flask, jsonify, request, send_from_directory

from . import ai, ingest, storage
from .retriever import engine


def resource_path(relative: str) -> str:
    """Locate bundled files whether running from source or a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


STATIC_DIR = resource_path("static")

app = Flask(__name__, static_folder=None)

# Loopback addresses count as "the host machine".
_LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}


def is_host_request() -> bool:
    return (request.remote_addr or "") in _LOOPBACK


def host_only(view):
    """Reject knowledge-changing requests that don't come from the host."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not is_host_request():
            return (
                jsonify(
                    {
                        "error": "Knowledge can only be changed on the host PC. "
                        "Please ask whoever manages the Assistant."
                    }
                ),
                403,
            )
        return view(*args, **kwargs)

    return wrapper


# --------------------------------------------------------------------------
# Front-end (single page app)
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.get("/api/whoami")
def whoami():
    """Tell the UI whether this user may edit, and what the AI can do."""
    ai_status = ai.status()
    return jsonify(
        {
            "is_host": is_host_request(),
            "ai": {
                "generation": ai_status.get("chat_ready", False),
                "embeddings": ai_status.get("embed_ready", False),
                "reachable": ai_status.get("reachable", False),
                "chat_model": ai_status.get("chat_model"),
            },
            "search_mode": engine.mode,
        }
    )


# --------------------------------------------------------------------------
# Ask a question  (retrieval + optional local-AI generation)
# --------------------------------------------------------------------------
@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"found": False, "message": "Please type a question."})

    search = engine.search(question, top_k=4)
    if not search["has_items"]:
        return jsonify(
            {
                "found": False,
                "message": (
                    "I don't have any knowledge yet. On the host PC, add Q&A "
                    "pairs or upload documents on the 'Manage Knowledge' tab."
                ),
            }
        )

    candidates = search["candidates"]
    best = candidates[0]["confidence"] if candidates else 0.0

    # Nothing remotely relevant -> say so rather than guess.
    if not candidates or best < engine.floor():
        return jsonify(
            {
                "found": False,
                "message": (
                    "I couldn't find anything relevant for that. Try rephrasing, "
                    "or have someone add it on the host PC."
                ),
                "suggestions": candidates[:3],
            }
        )

    # Try a conversational, grounded answer from the local AI.
    if ai.generation_available():
        contexts = [c["answer"][:1500] for c in candidates]
        generated = ai.generate(question, contexts)
        if generated:
            return jsonify(
                {
                    "found": True,
                    "answer": generated,
                    "mode": "ai",
                    "sources": [
                        {"source": c["source"], "kind": c["kind"]}
                        for c in candidates
                    ],
                    "confidence": best,
                }
            )

    # Fallback: AI off or failed -> return the best matching passage directly,
    # but only if we're confident enough for a raw passage to be useful.
    if best < engine.no_ai_threshold():
        return jsonify(
            {
                "found": False,
                "message": (
                    "I couldn't find a confident answer for that. Try rephrasing, "
                    "or have someone add it on the host PC."
                ),
                "suggestions": candidates[:3],
            }
        )

    top = candidates[0]
    return jsonify(
        {
            "found": True,
            "answer": top["answer"],
            "mode": "search",
            "source": top["source"],
            "kind": top["kind"],
            "confidence": top["confidence"],
            "alternatives": candidates[1:],
        }
    )


# --------------------------------------------------------------------------
# Q&A pairs  (host-only for changes)
# --------------------------------------------------------------------------
@app.get("/api/qa")
def get_qa():
    return jsonify(storage.list_qa())


@app.post("/api/qa")
@host_only
def create_qa():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    answer = (payload.get("answer") or "").strip()
    if not question or not answer:
        return jsonify({"error": "Both a question and an answer are required."}), 400
    qa_id = storage.add_qa(question, answer)
    engine.mark_dirty()
    return jsonify({"id": qa_id}), 201


@app.put("/api/qa/<int:qa_id>")
@host_only
def edit_qa(qa_id):
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    answer = (payload.get("answer") or "").strip()
    if not question or not answer:
        return jsonify({"error": "Both a question and an answer are required."}), 400
    storage.update_qa(qa_id, question, answer)
    engine.mark_dirty()
    return jsonify({"ok": True})


@app.delete("/api/qa/<int:qa_id>")
@host_only
def remove_qa(qa_id):
    storage.delete_qa(qa_id)
    engine.mark_dirty()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Documents  (host-only for changes)
# --------------------------------------------------------------------------
@app.get("/api/documents")
def get_documents():
    return jsonify(storage.list_documents())


@app.post("/api/documents")
@host_only
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file was uploaded."}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file was selected."}), 400

    data = file.read()
    try:
        chunks = ingest.file_to_chunks(file.filename, data)
    except ingest.UnsupportedFileType as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": f"Could not read that file: {exc}"}), 400

    if not chunks:
        return jsonify({"error": "No readable text was found in that file."}), 400

    doc_id = storage.add_document(file.filename, chunks)
    engine.mark_dirty()
    return jsonify({"id": doc_id, "chunk_count": len(chunks)}), 201


@app.delete("/api/documents/<int:doc_id>")
@host_only
def remove_document(doc_id):
    storage.delete_document(doc_id)
    engine.mark_dirty()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# First-run example data
# --------------------------------------------------------------------------
EXAMPLE_QA = [
    (
        "How do I reset the alarm panel after a power outage?",
        "After power is restored, the panel reboots automatically. If it shows a "
        "trouble light, enter your installer/master code followed by the disarm "
        "button twice to clear the fault. Verify the backup battery indicator is "
        "green before leaving the site. (Edit or delete this example on the "
        "Manage Knowledge tab.)",
    ),
    (
        "What is our standard camera resolution for new installs?",
        "Standard installs use 4MP cameras for general coverage and 8MP (4K) at "
        "entrances and points of sale. Confirm available NVR storage supports the "
        "chosen resolution and retention period. (Example entry -- replace with "
        "your real standard.)",
    ),
    (
        "Who do I contact for after-hours technical support?",
        "Replace this with your real escalation contact and phone number so staff "
        "always have the right after-hours number on hand. (Example entry.)",
    ),
]


def _seed_examples_if_empty() -> None:
    if not storage.list_qa() and not storage.list_documents():
        for question, answer in EXAMPLE_QA:
            storage.add_qa(question, answer)


def create_app() -> Flask:
    storage.init_db()
    _seed_examples_if_empty()
    return app
