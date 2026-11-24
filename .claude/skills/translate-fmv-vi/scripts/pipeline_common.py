#!/usr/bin/env python3
"""Shared utilities for the FMV game localization pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

# Vietnamese diacritics reference set (134 standard accented Latin characters)
VIETNAMESE_ACCENTED_CHARS = set(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
)

# Vietnamese Anti-AI-Slop phrase patterns (phrases that strongly indicate lazy/unnatural machine translation)
VIETNAMESE_SLOP_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(tôi\s+và\s+bạn|tôi\s+với\s+bạn|tôi\s+-\s+bạn)\b", re.IGNORECASE), "toi_ban_cliche", "Lạm dụng đại từ rập khuôn 'Tôi - Bạn'"),
    (re.compile(r"\b(chết\s+tiệt|quỷ\s+tha\s+ma\s+bắt)\b", re.IGNORECASE), "swearing_cliche", "Chửi thề dịch máy sáo rỗng ('chết tiệt' / 'quỷ tha ma bắt')"),
    (re.compile(r"\b(một\s+cách\s+(nhanh\s+chóng|dễ\s+dàng|chậm\s+chạp|cẩn\s+thận|tự\s+nhiên))\b", re.IGNORECASE), "adverb_calque", "Cấu trúc trạng từ dịch thô 'một cách [tính từ]'"),
    (re.compile(r"\b(bởi\s+vì\s+.*?cho\s+nên)\b", re.IGNORECASE), "connective_cliche", "Cặp từ nối văn viết rườm rà 'bởi vì... cho nên...'"),
    (re.compile(r"\b(cảm\s+thấy\s+(rằng|được))\b", re.IGNORECASE), "filler_feeling", "Hư từ dịch thô 'cảm thấy rằng / cảm thấy được'"),
    (re.compile(r"\b(ở\s+một\s+mức\s+độ\s+nào\s+đó)\b", re.IGNORECASE), "filler_hedge", "Thành ngữ dịch gượng 'ở một mức độ nào đó'"),
    (re.compile(r"\b(lắc\s+đầu\s+một\s+cái|gật\s+đầu\s+một\s+cái)\b", re.IGNORECASE), "chinese_action_calque", "Hành động dịch bợt từ tiếng Trung 'lắc/gật đầu một cái'"),
    (re.compile(r"\b(ta\s+đây\s+liền|ngươi\s+muốn\s+làm\s+cái\s+gì)\b", re.IGNORECASE), "pseudo_wuxia_in_modern", "Văn phong kiếm hiệp giả cầy trong FMV hiện đại")
]


def digest_text(text: str) -> str:
    """Return SHA-256 digest with sha256: prefix."""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def digest_file(path: Path) -> str:
    """Return SHA-256 digest of file content with sha256: prefix."""
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def digest_value(value: Any) -> str:
    """Return deterministic SHA-256 of JSON-serializable value."""
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def atomic_text(path: Path, content: str) -> None:
    """Write text atomically using a temporary sibling file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.tmp-",
    )
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def atomic_json(path: Path, value: Any, indent: int = 2) -> None:
    """Write JSON data atomically."""
    content = json.dumps(value, indent=indent, ensure_ascii=False) + "\n"
    atomic_text(path, content)


def read_text(path: Path) -> str:
    """Read UTF-8 text file, tolerating BOM."""
    with path.open("r", encoding="utf-8-sig") as stream:
        return stream.read()


def read_json(path: Path) -> Any:
    """Read JSON file with UTF-8 BOM tolerance."""
    return json.loads(read_text(path))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_num, line in enumerate(stream, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                item = json.loads(line_str)
                if isinstance(item, dict):
                    item["__line__"] = line_num
                    records.append(item)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_num}: invalid JSON: {exc}") from exc
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    """Write an iterable of dicts to a JSONL file atomically."""
    lines: list[str] = []
    for item in records:
        clean = {k: v for k, v in item.items() if not k.startswith("__")}
        lines.append(json.dumps(clean, ensure_ascii=False, separators=(",", ":")))
    content = "\n".join(lines) + ("\n" if lines else "")
    atomic_text(path, content)


def read_tsv(path: Path) -> list[dict[str, str]]:
    """Read a tab-separated values file."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        return [dict(row) for row in reader]


# ---------------------------------------------------------
# Subtitle Timecode Parsing & CPS Calculation
# ---------------------------------------------------------

def timecode_to_ms(tc: str) -> int:
    """Convert SRT (00:01:23,450) or VTT (00:01:23.450 / 01:23.450) timecode to milliseconds."""
    tc = tc.strip().replace(",", ".")
    parts = tc.split(":")
    if len(parts) == 3:
        h, m, s = parts
        hours = int(h)
        minutes = int(m)
        seconds = float(s)
    elif len(parts) == 2:
        m, s = parts
        hours = 0
        minutes = int(m)
        seconds = float(s)
    else:
        raise ValueError(f"Invalid timecode format: {tc}")
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return int(round(total_seconds * 1000))


def ms_to_srt_timecode(ms: int) -> str:
    """Convert milliseconds to SRT timecode format: 00:01:23,450."""
    ms = max(0, ms)
    total_sec, millis = divmod(ms, 1000)
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def ms_to_vtt_timecode(ms: int) -> str:
    """Convert milliseconds to WebVTT timecode format: 00:01:23.450."""
    ms = max(0, ms)
    total_sec, millis = divmod(ms, 1000)
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def ms_to_ass_timecode(ms: int) -> str:
    """Convert milliseconds to ASS timecode format: 0:01:23.45 (centiseconds)."""
    ms = max(0, ms)
    total_sec, millis = divmod(ms, 1000)
    centis = millis // 10
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"


def calculate_cps(text: str, duration_ms: int) -> float:
    """Calculate Characters Per Second (CPS) including spaces."""
    if duration_ms <= 0:
        return 0.0
    duration_sec = duration_ms / 1000.0
    char_count = len(text.strip())
    return round(char_count / duration_sec, 2)


# ---------------------------------------------------------
# Conservative Token Counter
# ---------------------------------------------------------

class TokenCounter:
    """Conservative token estimator across CJK, Latin, and Vietnamese."""

    def __init__(self) -> None:
        pass

    def count(self, text: str) -> int:
        if not text:
            return 0
        tokens = 0
        # Vietnamese and Latin words
        latin_words = len(re.findall(r"[a-zA-ZÀ-ỹ0-9_]+", text))
        # CJK characters (each roughly 1-2 tokens)
        cjk_chars = len(re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]", text))
        # Other symbols
        other_chars = len(re.findall(r"[^\w\s\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]", text))
        tokens = int(latin_words * 1.3) + int(cjk_chars * 1.6) + int(other_chars * 0.8)
        return max(1, tokens)
