# File Cleaner AI Conventions

## Project Overview

**File Cleaner** is a Python desktop application that organizes files by analyzing content with Google Gemini and grouping them into structured folders. The app provides a GUI for non-technical users to quickly classify documents without manual work.

### Architecture

The codebase is split into **4 core modules**:

- **`gui.py`**: `tk.Tk` app with folder selection, file listing, grouping preview, and undo stack
- **`ai_engine.py`**: Gemini API integration, prompt building, response parsing with graceful fallback
- **`file_utils.py`**: Recursive file scanning, text extraction (TXT/DOCX/PDF), SHA-256 deduplication, batch file operations
- **`config.yaml`**: API key + model configuration (read by both `ai_engine` and `gui` for thresholds/output paths)

**Key Data Flow**: User selects folder → `scan_directory()` extracts file metadata (including 400-char summaries) → `group_files_with_ai()` sends to Gemini with prompt → results parsed into JSON groups → `apply_grouping()` moves files and creates `metadata.txt` per folder + CSV export.

## Critical Patterns

### Threading & UI Safety
- GUI runs on main thread; long operations (`scan_directory`, Gemini calls) run in daemon threads via `threading.Thread`
- Use `self.after(0, callback)` to marshal UI updates back to main thread (see `_finalize_analysis`)
- All logging via `self.log()` which detects thread context automatically

### Error Handling & Fallback
- **API Failure**: `group_files_with_ai()` catches Gemini errors and falls back to file-extension-based grouping (`_fallback_grouping()`)
- **Missing Dependencies**: Text extractors wrap imports in try-except; `Document = None` and `PdfReader = None` indicate optional deps
- **Partial Read Failures**: `extract_text()` catches per-file exceptions; bad PDFs/DOCXs log but don't crash the full scan

### Configuration Pattern
- `config.yaml` is read fresh each call: `load_config(config_path="config.yaml")` in both `ai_engine.py` and `gui.py`
- Required keys: `gemini_api_key`, `model`, `similarity_threshold`, `output_folder`
- **Note**: API key validation happens at Gemini call time, not startup

### File Deduplication
- Uses SHA-256 hashing (`compute_hash()`) over file content, **not** filename matching
- `detect_duplicates()` groups files by hash; `threshold` param unused (kept for API parity)
- Duplicates moved to `Duplikat/` folder with metadata referencing original

### Metadata Generation
- Each group gets `metadata.txt` (human-readable) and centralized `metadata_summary.csv` + optional `.xlsx`
- CSV includes: `group_name`, `file_name`, `original_path`, `new_path`, `description`, `timestamp`
- Metadata written *after* all file moves to ensure atomic operation

### File Paths & Locale
- Use `Path` from `pathlib` exclusively (all existing code does); avoid `os.path` strings
- Text is **all Indonesian** (UI labels, log messages, error text, metadata) — maintain this for user consistency
- Relative paths stored in `extra_metadata['relative_path']` for grouping prompts

## Development Workflows

### Running Locally
```bash
python main.py
```
Starts the GUI. Application auto-falls back from `customtkinter` to `tkinter` if not installed.

### Testing Configuration
- Place test files in a folder and update `config.yaml` with a valid Gemini API key
- Set `similarity_threshold: 0.85` and `output_folder: organized_files` for standard behavior

### Debugging Gemini Responses
- `_parse_groups_from_text()` extracts JSON from markdown code blocks (triple backticks) or raw JSON
- Falls back to line-by-line parser if JSON fails: expects `Group_Name:` lines followed by comma-separated filenames
- Examine raw response in returned `GroupingResult.raw_response` if parsing fails

### Undo Stack Design
- `gui.py` maintains `self.undo_stack: List[List[dict]]` of move operations (source/target paths)
- Each `apply_grouping()` call pushes one list of ops; `undo_last_move()` pops and reverses
- Undo attempts to remove empty folders but ignores errors (folder may have new files)

## Code Conventions

- **Type Hints**: Use `from __future__ import annotations` + full type hints (e.g., `List[Dict[str, object]]`)
- **Dataclasses**: `FileInfo` uses `@dataclass` with `field(default_factory=...)` for mutable defaults
- **Imports**: Relative imports in module (`from .gui import FileOrganizerApp`), fallback to absolute when run as script
- **Logging**: Use `logging.getLogger(__name__)` per module; configured in `main.py` via `configure_logging()`
- **Path Operations**: `Path.rglob("*")` for recursion, `Path.suffix.lower()` for extension matching
- **String Formatting**: Use f-strings; concatenate multi-line prompts with explicit `\n`

## Extension Points

**Adding a new file type**: Update `SUPPORTED_EXTENSIONS` in `file_utils.py`, then add extraction function (e.g., `_read_xlsx_file()`) and register in `extract_text()`.

**Customizing Grouping Logic**: Modify `_build_prompt()` in `ai_engine.py` to change the instruction sent to Gemini (currently Indonesian). Parser in `_parse_groups_from_text()` must handle the response format.

**UI Customization**: All widgets in `gui.py:_build_widgets()`. The app respects `customtkinter` theme if available; stick to `ttk` widgets for fallback compatibility.
