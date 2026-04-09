"""Codebase search tool for the Reaction Commerce e-commerce repository.

The index files are built at Docker image build time by scripts/build_codebase_index.py.
If the index is not available (local dev), functions return empty results.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("uvicorn.error")

CODEBASE_DIR = Path("/app/codebase_data")

_index_cache: list[dict[str, Any]] | None = None
_manifest_cache: str | None = None


def _load_index() -> list[dict[str, Any]]:
    global _index_cache
    if _index_cache is not None:
        return _index_cache

    index_path = CODEBASE_DIR / "index.json"
    if not index_path.exists():
        logger.warning("Codebase index not found at %s — search disabled", index_path)
        _index_cache = []
        return _index_cache

    _index_cache = json.loads(index_path.read_text())
    logger.info("Loaded codebase index: %d files", len(_index_cache))
    return _index_cache


def get_codebase_manifest() -> str:
    """Return the condensed manifest for LLM file selection."""
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache

    manifest_path = CODEBASE_DIR / "manifest.txt"
    if not manifest_path.exists():
        logger.warning(
            "Codebase manifest not found at %s — search disabled", manifest_path
        )
        _manifest_cache = ""
        return _manifest_cache

    _manifest_cache = manifest_path.read_text()
    logger.info("Loaded codebase manifest: %d chars", len(_manifest_cache))
    return _manifest_cache


def get_file_details(file_paths: list[str]) -> dict[str, str]:
    """Given a list of relative file paths, return their indexed content."""
    index = _load_index()
    lookup = {entry["path"]: entry for entry in index}
    results = {}
    for fp in file_paths:
        if fp in lookup:
            results[fp] = lookup[fp].get("first_80_lines", "")
        else:
            logger.warning("File not found in index: %s", fp)
    return results


def search_codebase_by_keywords(keywords: list[str]) -> list[dict[str, Any]]:
    """Simple keyword search across the index. Returns top 10 matches."""
    index = _load_index()
    if not index or not keywords:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in index:
        text = (
            entry["path"]
            + " "
            + " ".join(entry.get("exports", []))
            + " "
            + entry.get("first_80_lines", "")[:500]
        ).lower()

        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:10]]
