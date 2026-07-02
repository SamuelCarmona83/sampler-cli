from __future__ import annotations

import re

_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+(?:\s*,\s*[\w\.]+)*))",
    re.MULTILINE,
)
_GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\(([^)]*)\)", re.DOTALL)
_GO_IMPORT_SINGLE_RE = re.compile(r'import\s+"([^"]+)"')
_GO_IMPORT_LINE_RE = re.compile(r'"([^"]+)"')
_TS_IMPORT_RE = re.compile(
    r"""(?:import|export)\s+(?:[^'"]*from\s*)?['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)"""
)


def extract_imports(content: str, language: str) -> list[str]:
    """Best-effort, regex-based extraction of imported module/package names.

    This is intentionally lightweight (not a real parser) and used only to
    heuristically resolve cross-project dependencies; it does not feed the
    symbol/relationship pipeline (which deliberately omits import symbols to
    keep output compact).
    """
    language = language.lower()
    if language == "python":
        return _extract_python_imports(content)
    if language == "go":
        return _extract_go_imports(content)
    if language in ("typescript", "javascript", "vue"):
        return _extract_ts_imports(content)
    return []


def _extract_python_imports(content: str) -> list[str]:
    modules: list[str] = []
    for from_mod, import_mods in _PY_IMPORT_RE.findall(content):
        if from_mod:
            modules.append(from_mod)
        elif import_mods:
            modules.extend(m.strip() for m in import_mods.split(","))
    return modules


def _extract_go_imports(content: str) -> list[str]:
    modules: list[str] = []
    for block in _GO_IMPORT_BLOCK_RE.findall(content):
        modules.extend(_GO_IMPORT_LINE_RE.findall(block))
    modules.extend(_GO_IMPORT_SINGLE_RE.findall(content))
    return modules


def _extract_ts_imports(content: str) -> list[str]:
    modules: list[str] = []
    for first, second in _TS_IMPORT_RE.findall(content):
        module = first or second
        if module:
            modules.append(module)
    return modules
