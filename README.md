# Operations Assistant

A **shared, offline** question-and-answer program for day-to-day operations.
One PC on your network hosts a single shared knowledge base; everyone else
just opens it in a browser. It's **free to run** — no cloud, no API keys, no
subscriptions, and your data never leaves your network.

You "train" it two ways:

1. **Q&A pairs** — type a question and the exact answer you want returned.
2. **Documents** — upload manuals, spec sheets, and procedures (PDF, Word,
   Excel, text, or CSV) and it learns to answer from their contents.

When someone asks a question in plain English, the app finds the most relevant
knowledge and — if the local AI is enabled — writes a clear, conversational
answer grounded in it. If the AI is off, it returns the best matching passage
directly. Either way it won't make up answers it wasn't given.

---

## How it's set up: one host, many users

- **Host PC** — one always-on computer on your network runs
  `OperationsAssistant.exe`. It holds the shared knowledge base and (optionally)
  the local AI. **Knowledge is managed only on the host PC.**
- **Everyone else** — opens the assistant in their web browser. No install
  needed. They can ask questions; they cannot change the knowledge base.

### Free local AI (recommended)

Smart, conversational answers come from **Ollama**, a free program that runs an
AI model **on the host PC only**. Your other PCs stay light — they just use a
browser. Without Ollama the app still works using plain search; with it, answers
read like a knowledgeable coworker wrote them.

---

## Setting up the HOST PC (one time)

1. **Get the program.** Download `OperationsAssistant.exe` (see *Downloading*).
2. **Enable local AI (recommended).**
   - Install Ollama (free): https://ollama.com/download
   - Run **`setup-ai.bat`** (included). It downloads the AI models once.
     Defaults are tuned for a strong PC: `llama3.1:8b` for answers and
     `nomic-embed-text` for smarter search.
3. **Open the network.** Right-click **`allow-firewall.bat`** → *Run as
   administrator* (once) so other PCs can connect.
4. **Start it.** Double-click `OperationsAssistant.exe`. A window opens showing:
   - the **share address** for everyone else (e.g. `http://192.168.1.20:8731`),
   - the **management address** for this host (`http://localhost:8731`),
   - whether **Local AI** is On.
   Keep this window open — closing it stops the Assistant for everyone.
5. **Add your knowledge.** On the host, use the **Manage Knowledge** tab to add
   Q&A pairs and upload documents.

> Tip: For reliability, host it on a PC that stays on during business hours.

## For everyone else (users)

Open your browser and go to the **share address** the host shows
(e.g. `http://office-pc:8731` or `http://192.168.1.20:8731`). Ask away. Bookmark
it for easy access. You'll see an *Ask a Question* tab only — editing is done on
the host.

---

## Downloading the program

- **Easiest — from the repo's main page:** look at the **Releases** panel on
  the right-hand side of the repository home page, click the latest release, and
  download **`OperationsAssistant.exe`** under *Assets*. (Releases are published
  automatically whenever a version tag like `v1.0.0` is pushed.)
- **Newest build (in between releases):** repository **Actions** tab → newest
  *Build Windows App* run → download the **OperationsAssistant-windows**
  artifact → unzip to get `OperationsAssistant.exe`.

(First run, Windows SmartScreen may warn about an "unknown publisher" because
the app isn't code-signed. Click **More info → Run anyway**.)

---

## Choosing a different AI model

Defaults suit a strong host (32GB+ RAM / GPU). To use a different model, pull it
with Ollama and set an environment variable before launching:

| Host machine | Suggested `OA_CHAT_MODEL` |
|--------------|---------------------------|
| Strong (GPU / 32GB+) | `llama3.1:8b` (default) or `llama3.1:70b` |
| Typical office (16GB) | `llama3.2:3b` |
| Older / low-end (8GB) | `llama3.2:1b` |

Environment variables (all optional):
`OA_CHAT_MODEL`, `OA_EMBED_MODEL`, `OLLAMA_HOST`.

---

## For developers

### Run from source
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Build the Windows .exe locally
On a Windows PC with Python 3.11+: run `build.bat`. Output:
`dist\OperationsAssistant.exe`.

### Project layout
| Path | Purpose |
|------|---------|
| `run.py` | Entry point (dev + build). |
| `src/main.py` | Starts the network server, prints share URL + AI status. |
| `src/server.py` | Web routes; enforces host-only editing. |
| `src/retriever.py` | Search engine (embeddings or TF-IDF) returning candidates. |
| `src/ai.py` | Local AI via Ollama: embeddings + grounded answer generation. |
| `src/ingest.py` | Reads PDF/Word/Excel/text/CSV into searchable text. |
| `src/storage.py` | Shared SQLite knowledge base in the host's AppData folder. |
| `src/static/` | The user interface (HTML/CSS/JS). |
| `setup-ai.bat` | One-time local-AI model install (host). |
| `allow-firewall.bat` | Opens TCP 8731 for the LAN (host, run as admin). |
| `OperationsAssistant.spec` | PyInstaller build recipe. |
| `.github/workflows/build-windows.yml` | Automated Windows build. |

### How answering works
1. The retriever finds the top matching passages (semantic embeddings if the
   local AI is available, otherwise TF-IDF + fuzzy matching).
2. If the local AI is on, those passages are sent to the model with strict
   instructions to answer only from them — then a natural answer is returned
   with its sources. If the AI is off or fails, the best passage is returned
   directly.

### Where data is stored
Host only: `%APPDATA%\OperationsAssistant\knowledge.db`. Survives app updates.
