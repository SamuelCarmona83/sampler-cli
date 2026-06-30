from pathlib import Path

from gitignore_parser import parse_gitignore


LANGUAGE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "go": {".go"},
    "typescript": {".ts", ".tsx", ".js", ".jsx"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
}

DEFAULT_IGNORE_PARTS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
}


def discover_files(project_path: str, language: str, ignore_patterns: list[str] | None = None) -> list[str]:
    root = Path(project_path)
    if not root.exists() or not root.is_dir():
        return []

    exts = LANGUAGE_EXTENSIONS.get(language.lower())
    if exts is None:
        return []

    gitignore = root / ".gitignore"
    gitignore_matcher = parse_gitignore(gitignore) if gitignore.exists() else None

    discovered: list[str] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in exts:
            continue
        if any(part in DEFAULT_IGNORE_PARTS for part in file_path.parts):
            continue
        if ignore_patterns and any(pattern in str(file_path) for pattern in ignore_patterns):
            continue
        if gitignore_matcher and gitignore_matcher(str(file_path)):
            continue
        discovered.append(str(file_path.resolve()))

    return sorted(discovered)
