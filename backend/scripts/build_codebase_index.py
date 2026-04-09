"""Build a searchable index of the Reaction Commerce codebase.

Run at Docker build time:
    python scripts/build_codebase_index.py /tmp/reaction /app/codebase_data

Produces:
    - index.json: Full file index with code snippets
    - manifest.txt: Condensed file list for LLM consumption (~8K tokens)
"""

import json
import re
import sys
from pathlib import Path

INDEXED_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".graphql",
    ".gql",
    ".md",
}

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".cache",
    "coverage",
    ".nyc_output",
    "vendor",
}

SKIP_FILENAME_PATTERNS = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".DS_Store",
}

MAX_FIRST_LINES = 80
MAX_MANIFEST_ENTRIES = 500

EXPORT_PATTERN = re.compile(
    r"(?:export\s+(?:default\s+)?(?:class|function|const|let|var|async\s+function)\s+(\w+))"
    r"|(?:module\.exports\s*=)"
    r"|(?:exports\.(\w+)\s*=)",
    re.MULTILINE,
)


def extract_exports(content: str) -> list[str]:
    """Extract exported symbol names from JS/TS source."""
    exports = []
    for match in EXPORT_PATTERN.finditer(content):
        name = match.group(1) or match.group(2)
        if name:
            exports.append(name)
        elif "module.exports" in match.group(0):
            exports.append("module.exports")
    return exports[:10]


def summarize_file(rel_path: str, content: str, language: str) -> str:
    """Generate a one-line summary for the manifest."""
    exports = extract_exports(content)
    if exports:
        return f"{rel_path} [{language}] exports: {', '.join(exports[:5])}"

    first_line = content.strip().split("\n")[0][:100] if content.strip() else ""
    if first_line.startswith(("//", "#", "/*", "/**", "<!--")):
        comment = first_line.lstrip("/#*<>!- ").strip()
        if comment:
            return f"{rel_path} [{language}] {comment}"

    return f"{rel_path} [{language}]"


def get_language(ext: str) -> str:
    return {
        ".js": "javascript",
        ".jsx": "javascript-react",
        ".ts": "typescript",
        ".tsx": "typescript-react",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".graphql": "graphql",
        ".gql": "graphql",
        ".md": "markdown",
    }.get(ext, "unknown")


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def build_index(repo_path: Path, output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    manifest_lines: list[str] = []

    all_files = sorted(
        f
        for f in repo_path.rglob("*")
        if f.is_file()
        and f.suffix in INDEXED_EXTENSIONS
        and not should_skip(f.relative_to(repo_path))
        and f.name not in SKIP_FILENAME_PATTERNS
    )

    print(f"Found {len(all_files)} files to index")

    for filepath in all_files:
        rel_path = str(filepath.relative_to(repo_path))
        language = get_language(filepath.suffix)

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  Skipping {rel_path}: {e}")
            continue

        lines = content.split("\n")
        first_lines = "\n".join(lines[:MAX_FIRST_LINES])
        exports = extract_exports(content)

        entry = {
            "path": rel_path,
            "language": language,
            "size_bytes": filepath.stat().st_size,
            "line_count": len(lines),
            "first_80_lines": first_lines,
            "exports": exports,
        }
        index.append(entry)

        summary = summarize_file(rel_path, content, language)
        manifest_lines.append(summary)

    # Cap manifest at MAX_MANIFEST_ENTRIES (prioritize src/ and core paths)
    def sort_key(line: str) -> tuple[int, str]:
        priority = 0
        if any(
            p in line
            for p in ("src/", "imports/", "server/", "lib/", "api/", "plugins/")
        ):
            priority = -1
        if any(p in line for p in ("test", "spec", "mock", "fixture", "__tests__")):
            priority = 1
        return (priority, line)

    manifest_lines.sort(key=sort_key)
    manifest_lines = manifest_lines[:MAX_MANIFEST_ENTRIES]

    # Write outputs
    index_path = output_path / "index.json"
    manifest_path = output_path / "manifest.txt"

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    with open(manifest_path, "w") as f:
        f.write("\n".join(manifest_lines))

    print(f"Index: {len(index)} files → {index_path}")
    print(f"Manifest: {len(manifest_lines)} entries → {manifest_path}")
    print(f"Index size: {index_path.stat().st_size / 1024:.1f} KB")
    print(f"Manifest size: {manifest_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <repo_path> <output_path>")
        sys.exit(1)

    repo = Path(sys.argv[1])
    output = Path(sys.argv[2])

    if not repo.is_dir():
        print(f"Error: {repo} is not a directory")
        sys.exit(1)

    build_index(repo, output)
