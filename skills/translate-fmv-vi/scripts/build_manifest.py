#!/usr/bin/env python3
"""Build SHA-256 manifest of source files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pipeline_common import atomic_json, digest_file

SUPPORTED_SUBTITLE_EXTS = {".srt", ".vtt", ".ass", ".ssa", ".json", ".csv", ".tsv", ".txt"}


def build_manifest(project_dir: Path) -> dict[str, str]:
    source_dir = project_dir / "source"
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    manifest_entries: list[dict[str, str]] = []

    for file_path in sorted(source_dir.rglob("*")):
        if file_path.is_file() and file_path.name != "file-manifest.json":
            rel_path = file_path.relative_to(source_dir).as_posix()
            file_hash = digest_file(file_path)
            manifest_entries.append({
                "path": rel_path,
                "size_bytes": file_path.stat().st_size,
                "sha256": file_hash,
                "extension": file_path.suffix.lower(),
                "is_subtitle": file_path.suffix.lower() in SUPPORTED_SUBTITLE_EXTS,
            })

    output_path = source_dir / "file-manifest.json"
    atomic_json(output_path, {"files": manifest_entries, "total_files": len(manifest_entries)})
    print(f"[OK] Built source manifest with {len(manifest_entries)} files -> {output_path}")
    return {entry["path"]: entry["sha256"] for entry in manifest_entries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build source files SHA-256 manifest.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    args = parser.parse_args()
    build_manifest(args.project_dir)


if __name__ == "__main__":
    main()
