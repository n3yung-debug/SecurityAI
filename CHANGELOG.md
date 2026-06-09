# Changelog

All notable changes to Operations Assistant are recorded here, newest first.
Each entry corresponds to a versioned release on the repository's home page.

## How versions work

The current version lives in the [`VERSION`](VERSION) file. When `VERSION` is
bumped and merged into `main`, the build publishes a **new** release
`v<VERSION>` (with the Windows `.exe` attached) — previous versions are kept,
so you can always see and download any past version and review what changed.

Use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`
- **PATCH** (1.0.0 → 1.0.1): small fixes, no behavior change for users.
- **MINOR** (1.0.0 → 1.1.0): new features, backward compatible.
- **MAJOR** (1.0.0 → 2.0.0): big or breaking changes.

To cut a release: update `VERSION`, add a section below describing the changes,
and merge to `main`.

---

## v1.0.2 — Easier-to-open docs in the bundle

- The documentation in the setup bundle now ships as **`README.txt`** (instead
  of `README.md`) so it opens directly in Notepad with a double-click.

## v1.0.1 — Complete host setup bundle in the release

- Releases now include **`OperationsAssistant-Setup.zip`**, containing
  everything the host needs in one download: the program, `setup-ai.bat`,
  `allow-firewall.bat`, a plain-text `HOST-SETUP.txt` guide, and the README.
  (Ollama is still installed separately — it's the only external piece.)
- The standalone `OperationsAssistant.exe` is still attached for convenience.

## v1.0.0 — Initial release

First version of Operations Assistant.

- Shared, offline question-and-answer tool for day-to-day operations.
- One host PC serves a single shared knowledge base to the whole network;
  everyone else connects from a browser (no install needed).
- "Trained" two ways: hand-written Q&A pairs and uploaded documents
  (PDF, Word, Excel, text, CSV).
- Host-only editing: knowledge is managed only on the host machine; remote
  users are ask-only (enforced server-side).
- Free local AI via Ollama (host-only): semantic search plus natural,
  grounded answers, with automatic fallback to keyword search when AI is off.
- Automated Windows build published as a downloadable release.
