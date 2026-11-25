#!/usr/bin/env python3
"""Shared utilities for the FMV game localization pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
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

_VN_LEFT = r"(?<![0-9A-Za-zÀ-ỹ_])"
_VN_RIGHT = r"(?![0-9A-Za-zÀ-ỹ_])"

# Vietnamese Anti-AI-Slop and word-by-word translation calque patterns
VIETNAMESE_SLOP_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(tôi\s+và\s+bạn|tôi\s+với\s+bạn|tôi\s+-\s+bạn)\b", re.IGNORECASE), "toi_ban_cliche", "Lạm dụng đại từ rập khuôn 'Tôi - Bạn'"),
    (re.compile(r"\b(chết\s+tiệt|quỷ\s+tha\s+ma\s+bắt)\b", re.IGNORECASE), "swearing_cliche", "Chửi thề dịch máy sáo rỗng ('chết tiệt' / 'quỷ tha ma bắt')"),
    (re.compile(r"\b(một\s+cách\s+(nhanh\s+chóng|dễ\s+dàng|chậm\s+chạp|cẩn\s+thận|tự\s+nhiên|chính\s+xác|hoàn\s+hảo|im\s+lặng))\b", re.IGNORECASE), "adverb_calque", "Cấu trúc trạng từ dịch thô word-by-word 'một cách [tính từ]'"),
    (re.compile(r"\b(bởi\s+vì\s+.*?cho\s+nên)\b", re.IGNORECASE), "connective_cliche", "Cặp từ nối văn viết rườm rà 'bởi vì... cho nên...'"),
    (re.compile(r"\b(cảm\s+thấy\s+(rằng|được))\b", re.IGNORECASE), "filler_feeling", "Hư từ dịch thô 'cảm thấy rằng / cảm thấy được'"),
    (re.compile(r"\b(ở\s+một\s+mức\s+độ\s+nào\s+đó)\b", re.IGNORECASE), "filler_hedge", "Thành ngữ dịch gượng 'ở một mức độ nào đó'"),
    (re.compile(r"\b(lắc\s+đầu\s+một\s+cái|gật\s+đầu\s+một\s+cái)\b", re.IGNORECASE), "chinese_action_calque", "Hành động dịch bợt từ tiếng Trung 'lắc/gật đầu một cái'"),
    (re.compile(r"\b(ta\s+đây\s+liền|ngươi\s+muốn\s+làm\s+cái\s+gì)\b", re.IGNORECASE), "pseudo_wuxia_in_modern", "Văn phong kiếm hiệp giả cầy trong FMV hiện đại"),
    (re.compile(f"{_VN_LEFT}(điều\\s+đó\\s+có\\s+(nghĩa|ý\\s+nghĩa)\\s+là|nó\\s+có\\s+(nghĩa|ý\\s+nghĩa)\\s+là){_VN_RIGHT}", re.IGNORECASE), "word_by_word_means", "Dịch máy word-by-word ('điều đó/nó có nghĩa là' -> nên nói 'ý là / nghĩa là')"),
    (re.compile(f"{_VN_LEFT}(tôi|anh|em|cậu)\\s+(nghĩ|cho|tin|e|hiểu)\\s+rằng{_VN_RIGHT}", re.IGNORECASE), "word_by_word_that_clause", "Dịch thô mệnh đề 'that' ('nghĩ/tin rằng' -> bỏ 'rằng' cho tự nhiên)"),
    (re.compile(f"{_VN_LEFT}những\\s+gì\\s+(tôi|anh|em|cậu|bạn)\\s+(muốn|đang|vừa|đã)\\s+nói{_VN_RIGHT}", re.IGNORECASE), "word_by_word_what_i_mean", "Dịch word-by-word 'những gì [ai] muốn nói' -> nên dùng 'ý [ai] là'"),
    (re.compile(f"{_VN_LEFT}hãy\\s+để\\s+(tôi|chúng\\s+ta)\\s+(giúp|nói|làm|xem){_VN_RIGHT}", re.IGNORECASE), "word_by_word_let_me", "Dịch cứng 'hãy để tôi/chúng ta...' -> nên dùng 'để tôi/anh/em...'"),
    (re.compile(f"{_VN_LEFT}(trong\\s+trường\\s+hợp\\s+(này|đó)|dưới\\s+tình\\s+huống\\s+(này|đó)){_VN_RIGHT}", re.IGNORECASE), "bureaucratic_calque", "Văn phong hành chính 'trong trường hợp/dưới tình huống này'"),
    (re.compile(f"{_VN_LEFT}có\\s+(chuyện|vấn\\s+đề)\\s+gì\\s+sai\\s+với{_VN_RIGHT}", re.IGNORECASE), "word_by_word_wrong_with", "Dịch word-by-word 'what is wrong with' -> nên dùng 'bị làm sao thế'"),
    (re.compile(f"{_VN_LEFT}(bạn\\s+có\\s+ổn\\s+không|tất\\s+cả\\s+mọi\\s+thứ\\s+đều\\s+ổn\\s+chứ){_VN_RIGHT}", re.IGNORECASE), "word_by_word_are_you_ok", "Dịch máy rập khuôn 'bạn có ổn không'"),
]

GENERIC_CHOICE_SPEAKERS = {
    "", "system", "choice", "choice1", "choice2", "choice3", "choice4",
    "qte", "ui", "player", "player_choice", "option", "option1", "option2",
    "protagonist", "mc", "main", "main_character", "narrator",
}


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
        latin_words = len(re.findall(r"[a-zA-ZÀ-ỹ0-9_]+", text))
        cjk_chars = len(re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]", text))
        other_chars = len(re.findall(r"[^\w\s\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]", text))
        tokens = int(latin_words * 1.3) + int(cjk_chars * 1.6) + int(other_chars * 0.8)
        return max(1, tokens)


# ---------------------------------------------------------
# Bible Loading, Character Resolution & Scenario Pronoun Locks
# ---------------------------------------------------------

def load_bible(project_dir: Path) -> dict[str, Any]:
    """Load all localization Bible artifacts if present."""
    bible_dir = project_dir / "bible"
    return {
        "world_md": read_text(bible_dir / "world.md") if (bible_dir / "world.md").exists() else "",
        "characters": read_json(bible_dir / "characters.json") if (bible_dir / "characters.json").exists() else {},
        "pronoun_matrix": read_json(bible_dir / "pronoun_matrix.json") if (bible_dir / "pronoun_matrix.json").exists() else {},
        "timeline_relationships": read_json(bible_dir / "timeline_relationships.json") if (bible_dir / "timeline_relationships.json").exists() else {},
        "voice": read_json(bible_dir / "voice.json") if (bible_dir / "voice.json").exists() else {},
        "glossary": read_tsv(bible_dir / "glossary.tsv") if (bible_dir / "glossary.tsv").exists() else [],
    }


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def _iter_character_entries(characters_data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = characters_data.get("characters")
    if isinstance(raw, list):
        return [c for c in raw if isinstance(c, dict)]
    if isinstance(raw, dict):
        result = []
        for key, item in raw.items():
            if isinstance(item, dict):
                entry = dict(item)
                entry.setdefault("id", key)
                result.append(entry)
        return result
    return []


def build_character_resolver(characters_data: dict[str, Any]) -> dict[str, Any]:
    """Build alias lookup map and identify the protagonist character."""
    entries = _iter_character_entries(characters_data)
    alias_to_id: dict[str, str] = {}
    by_id: dict[str, dict[str, Any]] = {}
    protagonist_id: str | None = characters_data.get("protagonist_id")

    for char in entries:
        cid = char.get("id")
        if not cid:
            continue
        by_id[cid] = char
        if char.get("is_protagonist") and not protagonist_id:
            protagonist_id = cid

        names = [cid, char.get("canonical_name", ""), *char.get("aliases", [])]
        for name in names:
            norm = _normalize_key(str(name))
            if norm:
                alias_to_id[norm] = cid

    if not protagonist_id:
        for cid in by_id:
            low = cid.lower()
            if "protagonist" in low or "male_lead" in low or "female_lead_mc" in low:
                protagonist_id = cid
                break

    return {
        "by_id": by_id,
        "alias_to_id": alias_to_id,
        "protagonist_id": protagonist_id,
    }


def resolve_speaker_id(
    raw_speaker: str,
    resolver: dict[str, Any],
    is_choice: bool = False,
) -> str | None:
    """Resolve raw speaker string to canonical character ID (or protagonist for choices)."""
    norm = _normalize_key(raw_speaker or "")
    alias_to_id = resolver.get("alias_to_id", {})
    if norm and norm in alias_to_id:
        return alias_to_id[norm]
    if is_choice:
        protagonist_id = resolver.get("protagonist_id")
        if protagonist_id and (not norm or norm in GENERIC_CHOICE_SPEAKERS or norm.startswith("choice") or norm.startswith("qte")):
            return protagonist_id
    return None


def display_character_name(char_id_or_name: str, resolver: dict[str, Any]) -> str:
    """Return human-readable canonical name for a character ID or fallback string."""
    by_id = resolver.get("by_id", {})
    if char_id_or_name in by_id:
        char = by_id[char_id_or_name]
        # Prefer first concrete alias if canonical_name is generic like "Nam Chính"
        aliases = char.get("aliases") or []
        canonical = char.get("canonical_name") or char_id_or_name
        if canonical in {"Nam Chính", "Nữ Chính", "Nhân Vật Chính"} and aliases:
            return f"{aliases[0]} ({canonical})"
        return canonical
    return char_id_or_name


def normalize_pronoun_rules(pronoun_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize both relationship_rules list schema and nested relationships.phases schema."""
    rules: list[dict[str, Any]] = []

    for item in pronoun_matrix.get("relationship_rules", []):
        if isinstance(item, dict):
            rules.append(dict(item))

    relationships = pronoun_matrix.get("relationships", {})
    if isinstance(relationships, dict):
        for rel_data in relationships.values():
            if not isinstance(rel_data, dict):
                continue
            pair = rel_data.get("pair", [])
            if len(pair) != 2:
                continue
            speaker_a, speaker_b = pair[0], pair[1]
            phases = rel_data.get("phases", {})
            for phase_name, pdata in phases.items():
                if not isinstance(pdata, dict):
                    continue
                # Try to map generic or named fields
                a_calls_b = pdata.get("a_calls_b", "")
                a_calls_self = pdata.get("a_calls_self", "")
                b_calls_a = pdata.get("b_calls_a", "")
                b_calls_self = pdata.get("b_calls_self", "")
                for k, v in pdata.items():
                    if k.endswith("_calls_self") and not a_calls_self:
                        a_calls_self = v
                    elif k.endswith("_calls_her") or k.endswith("_calls_him"):
                        if not a_calls_b:
                            a_calls_b = v
                        else:
                            b_calls_a = v
                rules.append({
                    "pair": pair,
                    "phase": phase_name,
                    "phase_label": pdata.get("description", phase_name),
                    "speaker_a": speaker_a,
                    "speaker_b": speaker_b,
                    "a_calls_b": a_calls_b,
                    "a_calls_self": a_calls_self,
                    "b_calls_a": b_calls_a,
                    "b_calls_self": b_calls_self,
                    "forbidden_a_self": pdata.get("forbidden_a_self", []),
                    "forbidden_a_to_b": pdata.get("forbidden_a_to_b", []),
                    "forbidden_b_self": pdata.get("forbidden_b_self", []),
                    "forbidden_b_to_a": pdata.get("forbidden_b_to_a", []),
                    "choice_guidance": pdata.get("choice_guidance", ""),
                    "notes": pdata.get("description", ""),
                })

    return rules


def make_pair_key(char_a: str, char_b: str) -> str:
    """Create deterministic pair key preserving alphabetical sort."""
    a, b = sorted([char_a, char_b])
    return f"{a}__{b}"


def find_phase_override(
    active_phases: dict[str, str],
    char_a: str,
    char_b: str,
) -> str | None:
    """Look up phase override in active_phases under either key order."""
    candidates = [
        f"{char_a}__{char_b}",
        f"{char_b}__{char_a}",
        make_pair_key(char_a, char_b),
    ]
    for key in candidates:
        if key in active_phases:
            return active_phases[key]
    return None


def resolve_scenario_pronoun_rules(
    participants: list[str],
    bible: dict[str, Any],
    route: str = "common",
    scenario_active_phases: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Filter pronoun rules strictly to active participants and their single active phase."""
    all_rules = normalize_pronoun_rules(bible.get("pronoun_matrix", {}))
    timeline_routes = bible.get("timeline_relationships", {}).get("routes", {})
    route_phases = timeline_routes.get(route, {}).get("active_phases", {})
    combined_phases = dict(route_phases)
    if scenario_active_phases:
        combined_phases.update(scenario_active_phases)

    participant_set = set(participants)
    # Group rules by unordered character pair
    rules_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rule in all_rules:
        pair = rule.get("pair") or [rule.get("speaker_a", ""), rule.get("speaker_b", "")]
        if len(pair) != 2 or not pair[0] or not pair[1]:
            continue
        if participant_set and not (pair[0] in participant_set and pair[1] in participant_set):
            continue
        pkey = tuple(sorted([pair[0], pair[1]]))
        rules_by_pair.setdefault(pkey, []).append(rule)

    resolved: list[dict[str, Any]] = []
    warnings: list[str] = []

    for (c1, c2), candidates in rules_by_pair.items():
        phase_override = find_phase_override(combined_phases, c1, c2)
        if phase_override:
            matched = [r for r in candidates if r.get("phase") == phase_override]
            if matched:
                resolved.append(matched[0])
            else:
                warnings.append(
                    f"Phase '{phase_override}' cho cặp {c1} <-> {c2} không tìm thấy trong pronoun_matrix.json."
                )
        elif len(candidates) == 1:
            resolved.append(candidates[0])
        else:
            default_matches = [r for r in candidates if r.get("phase") == "default"]
            if default_matches:
                resolved.append(default_matches[0])
            else:
                available = [r.get("phase", "?") for r in candidates]
                warnings.append(
                    f"Chưa khóa giai đoạn xưng hô (active_phases) cho cặp {c1} <-> {c2}. Các phase khả dụng: {available}. Tạm chọn phase đầu tiên ({available[0]}) — hãy cập nhật planning/scenarios.json!"
                )
                resolved.append(candidates[0])

    return resolved, warnings


def build_directional_locks(
    rules: list[dict[str, Any]],
    resolver: dict[str, Any],
) -> list[dict[str, Any]]:
    """Expand dyad rules into explicit Speaker -> Addressee Vietnamese pronoun instructions."""
    locks: list[dict[str, Any]] = []
    for r in rules:
        a = r.get("speaker_a") or (r.get("pair") or ["", ""])[0]
        b = r.get("speaker_b") or (r.get("pair") or ["", ""])[1]
        a_name = display_character_name(a, resolver)
        b_name = display_character_name(b, resolver)
        phase = r.get("phase", "default")
        phase_label = r.get("phase_label") or r.get("notes") or phase

        locks.append({
            "from_id": a,
            "from_name": a_name,
            "to_id": b,
            "to_name": b_name,
            "phase": phase,
            "phase_label": phase_label,
            "self_pronouns": r.get("a_calls_self", ""),
            "address_pronouns": r.get("a_calls_b", ""),
            "forbidden_self": list(r.get("forbidden_a_self", [])),
            "forbidden_address": list(r.get("forbidden_a_to_b", [])),
            "choice_guidance": r.get("choice_guidance", ""),
        })
        locks.append({
            "from_id": b,
            "from_name": b_name,
            "to_id": a,
            "to_name": a_name,
            "phase": phase,
            "phase_label": phase_label,
            "self_pronouns": r.get("b_calls_self", ""),
            "address_pronouns": r.get("b_calls_a", ""),
            "forbidden_self": list(r.get("forbidden_b_self", [])),
            "forbidden_address": list(r.get("forbidden_b_to_a", [])),
            "choice_guidance": r.get("choice_guidance", ""),
        })
    return locks


def split_pronoun_options(expr: str) -> list[str]:
    """Parse 'em / tôi' into normalized lower-case options ['em', 'tôi']."""
    if not expr:
        return []
    return [part.strip().lower() for part in expr.split("/") if part.strip()]


def contains_pronoun_token(text: str, token: str) -> bool:
    """Check whether a Vietnamese pronoun/phrase appears as a standalone token (avoiding compound nouns like 'bạn thân')."""
    t = token.strip()
    if not t:
        return False
    pattern = re.compile(f"{_VN_LEFT}{re.escape(t)}{_VN_RIGHT}", re.IGNORECASE)
    low = t.lower()

    if low == "bạn":
        compound_after = (
            "bè", "thân", "gái", "trai", "học", "cũ", "mới", "đời",
            "diễn", "đồng nghiệp", "đồng hành", "tâm giao", "tri kỷ",
            "đọc", "xem", "đường", "hàng", "nhậu", "của",
        )
        compound_before = (
            "người", "kết", "làm", "tình", "đôi", "hội", "nhóm",
            "đám", "lũ", "cô", "anh", "thằng", "con",
        )
        for m in pattern.finditer(text):
            imm_after = text[m.end():].lstrip().lower()
            imm_before = text[:m.start()].rstrip().lower()
            is_comp = any(
                imm_after.startswith(w) and (len(imm_after) == len(w) or not imm_after[len(w)].isalnum())
                for w in compound_after
            ) or any(
                imm_before.endswith(w) and (len(imm_before) == len(w) or not imm_before[-len(w) - 1].isalnum())
                for w in compound_before
            )
            if not is_comp:
                return True
        return False

    if low in {"anh", "em", "chị", "cô", "chú", "bác", "ông", "bà"}:
        third_person_after = ("ấy", "ta", "kia", "nọ", "đó", "này", "trai", "gái", "dâu", "rể", "họ")
        for m in pattern.finditer(text):
            imm_after = text[m.end():].lstrip().lower()
            is_third = any(
                imm_after.startswith(w) and (len(imm_after) == len(w) or not imm_after[len(w)].isalnum())
                for w in third_person_after
            )
            if not is_third:
                return True
        return False

    return bool(pattern.search(text))


def contains_forbidden_address(
    text: str,
    token: str,
    allowed_self_tokens: set[str],
    is_choice: bool = False,
) -> bool:
    """Detect forbidden address pronoun while avoiding false positives when same word is allowed as self-reference."""
    t = token.strip().lower()
    if not t:
        return False

    # Special case for choices: third-person references like "cô ấy / cô ta" or "bạn" directed at target
    if t not in allowed_self_tokens:
        if is_choice and t in {"cô ấy", "anh ấy", "cô ta", "hắn"}:
            pattern = re.compile(f"{_VN_LEFT}{re.escape(t)}{_VN_RIGHT}", re.IGNORECASE)
            return bool(pattern.search(text))
        return contains_pronoun_token(text, t)

    # If the word (e.g. 'em') is allowed as self-pronoun, only flag explicit vocative/2nd-person forms
    vocative_patterns = [
        re.compile(f"{_VN_LEFT}(này|ơi|chào|tạm\\s+biệt)\\s+{re.escape(t)}{_VN_RIGHT}", re.IGNORECASE),
        re.compile(f"{_VN_LEFT}{re.escape(t)}\\s+(ơi|à|ạ|nhé|nhá|nè|yêu){_VN_RIGHT}", re.IGNORECASE),
    ]
    return any(p.search(text) for p in vocative_patterns)
