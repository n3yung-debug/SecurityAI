"""Flask web server that powers the Operations Assistant window.

The program runs a tiny web server on the local machine (localhost) and opens
it in the browser. Nothing is exposed to the internet -- it only listens on the
local computer.
"""

from __future__ import annotations

import os
import sys

from flask import Flask, jsonify, request, send_from_directory

from . import ingest, storage
from .retriever import engine


def resource_path(relative: str) -> str:
    """Locate bundled files whether running from source or a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


STATIC_DIR = resource_path("static")

app = Flask(__name__, static_folder=None)


# --------------------------------------------------------------------------
# Front-end (single page app)
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# --------------------------------------------------------------------------
# Ask a question
# --------------------------------------------------------------------------
@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    return jsonify(engine.ask(question))


# --------------------------------------------------------------------------
# Q&A pairs
# --------------------------------------------------------------------------
@app.get("/api/qa")
def get_qa():
    return jsonify(storage.list_qa())


@app.post("/api/qa")
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
def remove_qa(qa_id):
    storage.delete_qa(qa_id)
    engine.mark_dirty()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------
@app.get("/api/documents")
def get_documents():
    return jsonify(storage.list_documents())


@app.post("/api/documents")
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
def remove_document(doc_id):
    storage.delete_document(doc_id)
    engine.mark_dirty()
    return jsonify({"ok": True})


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
    """On a brand-new install, add a few example Q&A pairs so the user sees
    how the app works. These are clearly marked and can be deleted."""
    if not storage.list_qa() and not storage.list_documents():
        for question, answer in EXAMPLE_QA:
            storage.add_qa(question, answer)


def create_app() -> Flask:
    storage.init_db()
    _seed_examples_if_empty()
    return app
