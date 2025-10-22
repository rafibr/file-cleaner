"""Graphical user interface for the File Organizer AI application."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import customtkinter as ctk
except Exception:  # pragma: no cover - fallback to tkinter
    ctk = None

try:
    from . import ai_engine
    from .file_utils import (
        FileInfo,
        apply_grouping,
        build_file_lookup,
        describe_duplicates,
        detect_duplicates,
        scan_directory,
        undo_moves,
    )
except ImportError:  # pragma: no cover - fallback when executed as script
    import ai_engine  # type: ignore
    from file_utils import (  # type: ignore
        FileInfo,
        apply_grouping,
        build_file_lookup,
        describe_duplicates,
        detect_duplicates,
        scan_directory,
        undo_moves,
    )


class FileOrganizerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("File Organizer AI")
        self.geometry("900x600")

        self.current_folder: Optional[Path] = None
        self.file_infos: List[FileInfo] = []
        self.grouping_preview: List[dict] = []
        self.duplicate_map: Dict[str, List[FileInfo]] = {}
        self.undo_stack: List[List[dict]] = []

        self._build_widgets()

    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        if ctk:
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X)

        self.folder_label = ttk.Label(top_frame, text="Pilih folder untuk dianalisis")
        self.folder_label.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(top_frame, text="Pilih Folder", command=self.select_folder).pack(side=tk.LEFT)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.analyze_button = ttk.Button(button_frame, text="Analisis & Kelompokkan", command=self.analyze_folder)
        self.analyze_button.pack(side=tk.LEFT)

        self.apply_button = ttk.Button(button_frame, text="Terapkan Grouping", command=self.apply_grouping, state=tk.DISABLED)
        self.apply_button.pack(side=tk.LEFT, padx=5)

        self.undo_button = ttk.Button(button_frame, text="Undo", command=self.undo_last_move, state=tk.DISABLED)
        self.undo_button.pack(side=tk.LEFT)

        self.open_output_button = ttk.Button(button_frame, text="Buka Folder Hasil", command=self.open_output_folder, state=tk.DISABLED)
        self.open_output_button.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(main_frame, mode="determinate")
        self.progress.pack(fill=tk.X)

        content_frame = ttk.Panedwindow(main_frame, orient=tk.HORIZONTAL)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        left_frame = ttk.Frame(content_frame)
        right_frame = ttk.Frame(content_frame)
        content_frame.add(left_frame, weight=1)
        content_frame.add(right_frame, weight=2)

        ttk.Label(left_frame, text="Daftar File").pack(anchor=tk.W)
        self.file_list = tk.Listbox(left_frame)
        self.file_list.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right_frame, text="Log & Hasil").pack(anchor=tk.W)
        self.log_text = tk.Text(right_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def select_folder(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.current_folder = Path(folder)
        self.folder_label.config(text=str(self.current_folder))
        self.log(f"Folder dipilih: {self.current_folder}")
        self.list_files()

    def list_files(self) -> None:
        self.file_list.delete(0, tk.END)
        if not self.current_folder:
            return
        for path in sorted(self.current_folder.rglob("*")):
            if path.is_file():
                self.file_list.insert(tk.END, str(path.relative_to(self.current_folder)))

    # ------------------------------------------------------------------
    def analyze_folder(self) -> None:
        if not self.current_folder:
            messagebox.showwarning("Perhatian", "Silakan pilih folder terlebih dahulu.")
            return

        self.analyze_button.config(state=tk.DISABLED)
        self.apply_button.config(state=tk.DISABLED)
        self.progress.config(mode="indeterminate")
        self.progress.start(10)
        self.log("Memulai analisis folder…")

        threading.Thread(target=self._analyze_worker, daemon=True).start()

    def _analyze_worker(self) -> None:
        assert self.current_folder is not None
        try:
            files = scan_directory(self.current_folder)
            cfg = ai_engine.load_config()
            threshold = float(cfg.get("similarity_threshold", 0.85))
            duplicates = detect_duplicates(files, threshold)
            duplicate_summary = describe_duplicates(duplicates)
            result = ai_engine.group_files_with_ai(files, duplicate_summary, log=self.log)
            self.after(
                0,
                lambda: self._finalize_analysis(files, duplicates, result, duplicate_summary),
            )
        except Exception as exc:
            self.after(0, lambda: self._handle_analysis_error(exc))

    def _finalize_analysis(
        self,
        files: List[FileInfo],
        duplicates: Dict[str, List[FileInfo]],
        result: ai_engine.GroupingResult,
        duplicate_summary: str,
    ) -> None:
        self.file_infos = files
        self.duplicate_map = duplicates
        self.grouping_preview = result.groups
        self.log("Analisis selesai. Hasil grouping siap ditinjau.")
        if result.used_fallback:
            self.log("Menggunakan fallback lokal karena respons Gemini tidak tersedia.")
        self.log(self._format_grouping_preview(self.grouping_preview))
        if duplicates:
            self.log(duplicate_summary)
        self.apply_button.config(state=tk.NORMAL if self.grouping_preview else tk.DISABLED)
        self.analyze_button.config(state=tk.NORMAL)
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)

    def _handle_analysis_error(self, error: Exception) -> None:
        self.log(f"Terjadi kesalahan saat analisis: {error}")
        messagebox.showerror("Kesalahan", str(error))
        self.analyze_button.config(state=tk.NORMAL)
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)

    def _format_grouping_preview(self, groups: List[dict]) -> str:
        lines = ["Hasil grouping (preview):"]
        for group in groups:
            name = group.get("group_name", "Tanpa Nama")
            summary = group.get("summary", "")
            files = ", ".join(group.get("files", []))
            lines.append(f"- {name}: {summary}\n  File: {files}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def apply_grouping(self) -> None:
        if not (self.current_folder and self.grouping_preview):
            messagebox.showinfo("Info", "Tidak ada hasil grouping untuk diterapkan.")
            return
        try:
            cfg = ai_engine.load_config()
            output_folder = Path(cfg.get("output_folder", "organized_files"))
            if not output_folder.is_absolute():
                output_folder = self.current_folder / output_folder
            lookup = build_file_lookup(self.file_infos)
            undo_ops = apply_grouping(self.grouping_preview, lookup, output_folder, self.duplicate_map)
            if undo_ops:
                self.undo_stack.append(undo_ops)
            self.open_output_button.config(state=tk.NORMAL)
            self.undo_button.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
            self.log(f"File berhasil dipindahkan ke {output_folder}")
            self.list_files()
            messagebox.showinfo("Sukses", f"Grouping diterapkan ke {output_folder}")
        except Exception as exc:
            self.log(f"Gagal menerapkan grouping: {exc}")
            messagebox.showerror("Kesalahan", str(exc))

    def undo_last_move(self) -> None:
        if not self.undo_stack:
            messagebox.showinfo("Info", "Tidak ada operasi untuk di-undo.")
            return
        last_ops = self.undo_stack.pop()
        undo_moves(last_ops)
        self.undo_button.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        self.log("Perubahan terakhir berhasil dibatalkan.")
        if self.current_folder:
            self.list_files()

    def open_output_folder(self) -> None:
        if not self.current_folder:
            return
        cfg = ai_engine.load_config()
        output_folder = Path(cfg.get("output_folder", "organized_files"))
        if not output_folder.is_absolute():
            output_folder = self.current_folder / output_folder
        if not output_folder.exists():
            messagebox.showwarning("Perhatian", "Folder hasil belum dibuat.")
            return
        self.log(f"Membuka folder: {output_folder}")
        try:
            if sys.platform.startswith("darwin"):
                subprocess.run(["open", str(output_folder)], check=False)
            elif os.name == "nt":
                os.startfile(str(output_folder))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(output_folder)], check=False)
        except Exception as exc:
            messagebox.showerror("Kesalahan", f"Tidak dapat membuka folder: {exc}")

    # ------------------------------------------------------------------
    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def log(self, message: str) -> None:
        if threading.current_thread() is threading.main_thread():
            self._append_log(message)
        else:
            self.after(0, lambda: self._append_log(message))


__all__ = ["FileOrganizerApp"]
