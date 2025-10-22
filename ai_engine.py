"""Integration with Google Gemini and helper utilities for grouping."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import requests
import yaml

from .file_utils import FileInfo, summarise_for_prompt

logger = logging.getLogger(__name__)


@dataclass
class GroupingResult:
    groups: List[Dict[str, object]]
    raw_response: Dict[str, object]
    used_fallback: bool = False


def load_config(config_path: str = "config.yaml") -> Dict[str, object]:
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _build_prompt(file_summaries: str, duplicate_summary: str) -> str:
    return (
        "Anda adalah asisten AI yang membantu mengelompokkan file berdasarkan kesamaan konteks isi dokumen.\n"
        "Gunakan data berikut untuk mengelompokkan file ke dalam grup yang logis.\n"
        "Setiap grup harus memiliki nama, ringkasan singkat, dan daftar nama file.\n"
        "Jika menemukan file yang tampak duplikat, cantumkan pada grup khusus bernama 'Duplikat'.\n"
        "Berikan hasil dalam format JSON dengan skema: "
        "[{\"group_name\": str, \"summary\": str, \"files\": [str, ...]}].\n"
        "Berikut daftar file:\n"
        f"{file_summaries}\n\n"
        f"Ringkasan duplikat:\n{duplicate_summary}"
    )


def _call_gemini(prompt: str, config: Dict[str, object]) -> Dict[str, object]:
    api_key = config.get("gemini_api_key")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise RuntimeError("Gemini API key belum dikonfigurasi pada config.yaml")

    model = config.get("model", "gemini-2.5-flash")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ]
    }
    response = requests.post(endpoint, headers=headers, params=params, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _extract_text_from_response(response: Dict[str, object]) -> str:
    candidates = response.get("candidates", [])
    for candidate in candidates:
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            text = part.get("text")
            if text:
                return text
    if "text" in response:
        return str(response["text"])
    raise ValueError("Tidak dapat menemukan teks pada respons Gemini")


def _parse_groups_from_text(text: str) -> List[Dict[str, object]]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    try:
        groups = json.loads(text)
        if isinstance(groups, list):
            return groups
    except json.JSONDecodeError:
        pass

    # Fallback simple parser: expect lines formatted as Group: file1, file2
    groups: List[Dict[str, object]] = []
    current_group: Optional[Dict[str, object]] = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(":"):
            if current_group:
                groups.append(current_group)
            current_group = {"group_name": line[:-1], "summary": "", "files": []}
        elif line.lower().startswith("summary:") and current_group is not None:
            current_group["summary"] = line.split(":", 1)[1].strip()
        elif current_group is not None:
            current_group.setdefault("files", []).extend([part.strip() for part in line.split(",") if part.strip()])
    if current_group:
        groups.append(current_group)
    return groups


def _fallback_grouping(files: Iterable[FileInfo]) -> List[Dict[str, object]]:
    buckets: Dict[str, List[str]] = {}
    for info in files:
        key = info.extension or "lainnya"
        buckets.setdefault(key, []).append(info.name)
    groups = []
    for ext, items in buckets.items():
        groups.append(
            {
                "group_name": f"File {ext.upper()}" if ext.startswith(".") else ext,
                "summary": f"Pengelompokan otomatis berdasarkan ekstensi {ext}",
                "files": items,
            }
        )
    return groups


def group_files_with_ai(
    files: Iterable[FileInfo],
    duplicate_summary: str,
    log: Optional[Callable[[str], None]] = None,
) -> GroupingResult:
    files = list(files)
    config = load_config()
    prompt = _build_prompt(summarise_for_prompt(files), duplicate_summary)
    logger.debug("Prompt yang dikirim ke Gemini: %s", prompt)
    if log:
        log("Mengirim ringkasan file ke Gemini…")
    try:
        response = _call_gemini(prompt, config)
        text = _extract_text_from_response(response)
        groups = _parse_groups_from_text(text)
        if not groups:
            raise ValueError("Respons Gemini tidak menghasilkan grup")
        return GroupingResult(groups=groups, raw_response=response)
    except Exception as exc:
        logger.exception("Gagal memanggil Gemini: %s", exc)
        if log:
            log(f"Gagal menggunakan Gemini: {exc}. Menggunakan fallback berdasarkan tipe file.")
        groups = _fallback_grouping(files)
        return GroupingResult(groups=groups, raw_response={"error": str(exc)}, used_fallback=True)


def validate_similarity(score: float, threshold: float) -> bool:
    return score >= threshold
