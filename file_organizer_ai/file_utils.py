"""Utility functions for scanning, summarising, and organising files."""
from __future__ import annotations

import csv
import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
from tqdm import tqdm

try:
    from docx import Document  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Document = None

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
    ".docx",
    ".pdf",
}


@dataclass
class FileInfo:
    """Representation of a single file and its extracted metadata."""

    path: Path
    name: str
    extension: str
    size: int
    modified_at: datetime
    sha256: str
    summary: str
    extra_metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def folder(self) -> Path:
        return self.path.parent


def _read_text_file(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def _read_docx_file(path: Path) -> str:
    if Document is None:
        raise RuntimeError("python-docx is required to read DOCX files")
    document = Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _read_pdf_file(path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is required to read PDF files")
    reader = PdfReader(str(path))
    texts: List[str] = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return "\n".join(texts)


def extract_text(path: Path) -> str:
    """Extract textual content from supported file types."""

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".py", ".json", ".csv"}:
        return _read_text_file(path)
    if suffix == ".docx":
        return _read_docx_file(path)
    if suffix == ".pdf":
        return _read_pdf_file(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def generate_summary(text: str, max_characters: int = 400) -> str:
    text = " ".join(text.split())
    return text[:max_characters] + ("…" if len(text) > max_characters else "")


def compute_hash(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def scan_directory(directory: Path) -> List[FileInfo]:
    """Scan a directory recursively and return metadata for supported files."""

    files: List[FileInfo] = []
    paths = [p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    for path in tqdm(paths, desc="Membaca file", unit="berkas", disable=True):
        try:
            text = extract_text(path)
        except Exception as exc:
            text = f"Gagal membaca isi file: {exc}"
        summary = generate_summary(text)
        stat = path.stat()
        files.append(
            FileInfo(
                path=path,
                name=path.name,
                extension=path.suffix.lower(),
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                sha256=compute_hash(path),
                summary=summary,
                extra_metadata={
                    "relative_path": str(path.relative_to(directory)),
                },
            )
        )
    return files


def summarise_for_prompt(files: Iterable[FileInfo]) -> str:
    lines = []
    for info in files:
        lines.append(
            f"Nama: {info.name}\nLokasi: {info.extra_metadata.get('relative_path', info.name)}\nRingkasan: {info.summary}\n---"
        )
    return "\n".join(lines)


def detect_duplicates(files: Iterable[FileInfo], threshold: float) -> Dict[str, List[FileInfo]]:
    """Detect duplicates by hash. Threshold kept for API parity."""

    duplicates: Dict[str, List[FileInfo]] = {}
    for file in files:
        duplicates.setdefault(file.sha256, []).append(file)
    filtered = {hash_value: infos for hash_value, infos in duplicates.items() if len(infos) > 1}
    return filtered


def sanitize_group_name(name: str) -> str:
    cleaned = "_".join(name.strip().split())
    return cleaned or "Kelompok"


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def apply_grouping(
    groups: List[Dict[str, object]],
    file_lookup: Dict[str, FileInfo],
    output_dir: Path,
    duplicates: Dict[str, List[FileInfo]],
) -> List[Dict[str, Path]]:
    """Move files into grouped folders and write metadata. Returns undo operations."""

    ensure_directory(output_dir)
    undo_operations: List[Dict[str, Path]] = []
    metadata_rows: List[Dict[str, object]] = []
    timestamp = datetime.now().isoformat(timespec="seconds")

    for group in groups:
        group_name = str(group.get("group_name", "Kelompok"))
        description = str(group.get("summary", ""))
        files = [str(f) for f in group.get("files", [])]
        folder_name = sanitize_group_name(group_name)
        target_folder = output_dir / folder_name
        ensure_directory(target_folder)

        metadata_lines = [f"Nama grup : {group_name}", f"Deskripsi : {description}", f"Dibuat pada : {timestamp}", "", "Daftar file:"]

        for file_name in files:
            info = file_lookup.get(file_name)
            if not info:
                continue
            destination = target_folder / info.name
            ensure_directory(destination.parent)
            shutil.move(str(info.path), destination)
            undo_operations.append({"source": destination, "target": info.path})
            metadata_lines.append(f"- {info.name}")
            metadata_rows.append(
                {
                    "group_name": group_name,
                    "file_name": info.name,
                    "original_path": str(info.path),
                    "new_path": str(destination),
                    "description": description,
                    "timestamp": timestamp,
                }
            )
            info.path = destination

        metadata_path = target_folder / "metadata.txt"
        metadata_path.write_text("\n".join(metadata_lines), encoding="utf-8")

    if duplicates:
        dup_folder = output_dir / "Duplikat"
        ensure_directory(dup_folder)
        metadata_lines = ["Nama grup : Duplikat", "Deskripsi : File dengan isi serupa", f"Dibuat pada : {timestamp}", "", "Daftar file:"]
        for infos in duplicates.values():
            for info in infos[1:]:
                destination = dup_folder / info.name
                ensure_directory(destination.parent)
                shutil.move(str(info.path), destination)
                undo_operations.append({"source": destination, "target": info.path})
                metadata_lines.append(f"- {info.name} (duplikat dari {infos[0].name})")
                metadata_rows.append(
                    {
                        "group_name": "Duplikat",
                        "file_name": info.name,
                        "original_path": str(info.path),
                        "new_path": str(destination),
                        "description": "File duplikat berdasarkan hash",
                        "timestamp": timestamp,
                    }
                )
                info.path = destination
        (dup_folder / "metadata.txt").write_text("\n".join(metadata_lines), encoding="utf-8")

    export_metadata_to_csv(output_dir, metadata_rows)
    return undo_operations


def export_metadata_to_csv(output_dir: Path, rows: List[Dict[str, object]]) -> Optional[Path]:
    if not rows:
        return None
    csv_path = output_dir / "metadata_summary.csv"
    fieldnames = ["group_name", "file_name", "original_path", "new_path", "description", "timestamp"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    try:
        pd.DataFrame(rows).to_csv(output_dir / "metadata_summary.xlsx", index=False)
    except Exception:
        # Excel export is best-effort only.
        pass
    return csv_path


def build_file_lookup(files: Iterable[FileInfo]) -> Dict[str, FileInfo]:
    lookup: Dict[str, FileInfo] = {}
    for info in files:
        lookup[info.name] = info
        relative = info.extra_metadata.get("relative_path")
        if relative:
            lookup[relative] = info
    return lookup


def undo_moves(operations: List[Dict[str, Path]]) -> None:
    while operations:
        operation = operations.pop()
        source = operation["source"]
        target = operation["target"]
        ensure_directory(target.parent)
        shutil.move(str(source), target)
        try:
            if not any(source.parent.iterdir()):
                source.parent.rmdir()
        except Exception:
            pass


def describe_duplicates(duplicates: Dict[str, List[FileInfo]]) -> str:
    if not duplicates:
        return "Tidak ada duplikat terdeteksi."
    lines = ["Duplikat terdeteksi:"]
    for infos in duplicates.values():
        primary = infos[0]
        others = ", ".join(info.name for info in infos[1:])
        lines.append(f"- {primary.name} -> {others}")
    return "\n".join(lines)
