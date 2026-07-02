from __future__ import annotations

import re

from sampler.indexer.parsers.base import BaseParser
from sampler.indexer.parsers.typescript import TypeScriptParser


class VueParser(BaseParser):
    """Parser for Vue single-file components (.vue).

    Extracts the <script> (or <script setup>) section using stdlib re (supports lang="ts|tsx|js|jsx|typescript",
    setup attribute, various quoting). Delegates symbol/relationship extraction to the existing
    TypeScriptParser (which covers JS/TS + arrows/classes/etc.) using a dummy filepath so that
    the delegate's _select_language picks the right grammar (ts vs tsx).

    Line numbers in results are offset so they are correct relative to the original .vue file.
    Graceful empty return if no <script> section or other issues.
    """

    language = "vue"

    _SCRIPT_RE = re.compile(
        r"(?is)<script([^>]*)>(.*?)</script>"
    )

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        symbols: list[dict] = []
        relationships: list[dict] = []

        if not filepath.lower().endswith(".vue"):
            # Shouldn't normally happen, but delegate to TS parser for safety
            return TypeScriptParser().parse(content, filepath)

        extracted = self._extract_vue_script(content)
        if extracted is None:
            return symbols, relationships

        script_text, line_offset, is_tsx = extracted

        # Dummy filepath controls grammar selection inside the (unchanged) TS parser
        dummy = "Comp.script.tsx" if is_tsx else "Comp.script.ts"
        inner_symbols, inner_relationships = TypeScriptParser().parse(script_text, dummy)

        # Offset lines so they refer to the original .vue file (script content lines are 0-based in tree)
        for s in inner_symbols:
            s["start_line"] += line_offset
            s["end_line"] += line_offset
        for r in inner_relationships:
            if "line" in r and r["line"] is not None:
                r["line"] += line_offset

        return inner_symbols, inner_relationships

    def _extract_vue_script(self, content: str) -> tuple[str, int, bool] | None:
        """Return (script_text, 0-based_line_offset_for_script_body, use_tsx) or None."""
        m = self._SCRIPT_RE.search(content)
        if not m:
            return None

        attrs = m.group(1) or ""
        script = m.group(2)

        # Compute offset: number of newlines before the start of the script body
        prefix = content[: m.start(2)]
        line_offset = prefix.count("\n")

        # Detect if we should force TSX grammar inside delegate (rare for Vue but supported)
        lang_match = re.search(r'lang\s*=\s*["\']?([^"\'\s>]+)', attrs, re.IGNORECASE)
        lang_val = (lang_match.group(1) if lang_match else "").lower()
        use_tsx = lang_val in ("tsx", "jsx")

        return script, line_offset, use_tsx
