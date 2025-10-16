## Purpose

This file tells AI coding agents how the file-cleaner project is organized and what conventions to follow when implementing features. Use these instructions to produce code that matches the existing project spec (found in `agents.md`).

## Big picture (what to build)

- Desktop Python app (GUI) to analyze and group files by semantic similarity and detect duplicates.
- Major modules (one file each): `main.py`, `ai_engine.py`, `file_utils.py`, `gui.py`.
- Config: `config.yaml` stores API keys and runtime settings. Default output folder: `organized_files`.

## Data flow / component responsibilities

1. GUI (`gui.py`) lets the user pick a folder and shows a file list + preview of grouping.
2. `file_utils.py` reads files (txt, docx, pdf), extracts text, computes hashes for duplicate detection, and provides per-file summaries.
3. `ai_engine.py` prepares prompts, calls the Gemini REST API, and returns a JSON grouping description like [{"group_name":..., "files":[...]}].
4. `main.py` orchestrates flow: request analysis, get grouping, show preview, then move files and write `metadata.txt` per group.

## Project-specific conventions and examples

- Config (`config.yaml`) example (must be supported exactly):

```yaml
gemini_api_key: "YOUR_API_KEY_HERE"
model: "gemini-2.5-flash"
similarity_threshold: 0.85
output_folder: "organized_files"
```

- Default similarity threshold: 0.85 — use this value unless the user explicitly changes it via config.
- Output folder name: `organized_files`.
- Metadata file: write a human-readable `metadata.txt` in each group folder containing group summary, file list, and timestamp.

## Integration details (exact patterns to follow)

- Gemini REST call pattern (refer to `agents.md` example):

  POST to
  `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`

  Headers: `Authorization: Bearer {gemini_api_key}` and JSON payload containing `model` and `input` text.

- Prompt/response contract: `ai_engine.analyze_files_with_gemini(file_summaries)` should return a parsed Python list of dicts with keys `group_name` and `files`.

## UI / UX expectations

- GUI should offer: "Choose Folder", "Analyze & Group", progress indicator, preview of grouping, "Apply" to move files, and an "Undo" for the last move.
- Always show preview (do not move files automatically). Implement a simple undo log for the last operation.

## Running & developer workflow

- Intended run command: `python main.py` (project is single-process desktop app).
- Use a virtualenv and `pip install -r requirements.txt`. If `requirements.txt` is missing, include common libs: `requests`, `PyYAML`, `python-docx`, `PyPDF2`, `tqdm`, and either `customtkinter` or rely on `tkinter`.

## Tests & quality gates

- There are no tests in the repo yet. When adding tests, place them under `tests/` and add a minimal test for `file_utils.read_text()` and `ai_engine.analyze_files_with_gemini()` (mock the network call).

## Code style & small patterns

- Keep modules small and single-responsibility. Functions should return plain Python types (dict/list/str) not custom objects unless clearly needed.
- For file moves, use `shutil.move` and preserve original timestamps when possible.
- Use `hashlib` (e.g., SHA256) for duplicate detection and include the hash in `metadata.txt` when a duplicate is placed in the `Duplikat/` folder.

## What to avoid

- Don't hardcode API keys in source. Read them from `config.yaml`.
- Don't move files before user confirms the preview.

## Where to look in this repo

- `agents.md` (project spec + example prompt and example `ai_engine` function) — the authoritative source for behavior and prompt examples.

## If files are missing (practical guidance for agents)

- This repository currently contains only docs (no implementation). If asked to implement features, bootstrap the four modules above plus `requirements.txt` and `config.yaml` (with the example values). Provide a minimal `README.md` with run steps and a tiny demo dataset under `example_data/` when appropriate.

---
If anything in this file looks wrong or incomplete, tell me which area to expand (prompts, GUI details, test harness, or Gemini integration examples).
