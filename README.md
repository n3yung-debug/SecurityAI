# Operations Assistant

A simple, **offline** question-and-answer program for day-to-day operations.
You "train" it with your own knowledge in two ways:

1. **Q&A pairs** — type a question and the exact answer you want returned.
2. **Documents** — upload manuals, spec sheets, and procedures (PDF, Word,
   Excel, text, or CSV) and it learns to answer from their contents.

When someone types a question in plain English, the app searches everything
you've taught it and returns the best-matching answer, a confidence rating,
and the source.

## Why it's free to run

Everything happens **on the PC itself** — there is no cloud service, no API
key, no subscription, and no per-question cost. Your data never leaves the
computer, which is also good for privacy. (The trade-off: it answers from the
knowledge you give it rather than "chatting" like a paid online AI.)

---

## For everyday users (running the program)

1. Get `OperationsAssistant.exe` (see *Downloading* below).
2. Double-click it. A small black window opens and your web browser pops up
   showing the assistant. **Keep the black window open** while you use it —
   closing it shuts the program down.
3. Use the **Ask a Question** tab to get answers, and the **Manage Knowledge**
   tab to add Q&A pairs or upload documents.

Windows SmartScreen may warn that the program is from an "unknown publisher"
the first time (because it isn't code-signed). Click **More info → Run anyway**.

## Downloading the program

The Windows program is built automatically:

- **Latest build:** Go to the repository's **Actions** tab → open the most
  recent *Build Windows App* run → download the **OperationsAssistant-windows**
  artifact at the bottom. Unzip it to get `OperationsAssistant.exe`.
- **Released versions:** Pushing a version tag (e.g. `v1.0.0`) also publishes
  the `.exe` under **Releases**.

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
On a Windows PC with Python 3.11+:
```bat
build.bat
```
The finished program appears at `dist\OperationsAssistant.exe`.

### Project layout
| Path | Purpose |
|------|---------|
| `run.py` | Entry point (dev + build). |
| `src/main.py` | Starts the local server and opens the browser. |
| `src/server.py` | Web routes (ask, Q&A, documents). |
| `src/retriever.py` | The offline search/answer engine. |
| `src/ingest.py` | Reads PDF/Word/Excel/text/CSV into searchable text. |
| `src/storage.py` | Local SQLite storage in the user's AppData folder. |
| `src/static/` | The user interface (HTML/CSS/JS). |
| `OperationsAssistant.spec` | PyInstaller build recipe. |
| `.github/workflows/build-windows.yml` | Automated Windows build. |

### Where data is stored
On Windows: `%APPDATA%\OperationsAssistant\knowledge.db`. Removing the program
does not delete this folder, so your knowledge survives updates.
