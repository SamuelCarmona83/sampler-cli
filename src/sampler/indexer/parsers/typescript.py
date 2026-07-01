from __future__ import annotations

from sampler.indexer.parsers.base import BaseParser

try:
    import tree_sitter_typescript as _tsts
    from tree_sitter import Language, Parser as TSParser

    _TS_LANGUAGE = Language(_tsts.language_typescript())
    _TSX_LANGUAGE = Language(_tsts.language_tsx())
except ImportError:
    _TS_LANGUAGE = None
    _TSX_LANGUAGE = None

_FUNCTION_VALUE_TYPES = ("arrow_function", "function_expression", "function")


class TypeScriptParser(BaseParser):
    """Handles TypeScript/TSX and (as a reasonable approximation) JavaScript/JSX files."""

    language = "typescript"

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        symbols: list[dict] = []
        relationships: list[dict] = []

        lang = self._select_language(filepath)
        if lang is None:
            # tree-sitter-typescript isn't installed; skip gracefully.
            return symbols, relationships

        source = content.encode("utf-8")
        parser = TSParser(lang)
        tree = parser.parse(source)

        for node in tree.root_node.children:
            self._handle_top_level(node, source, symbols, relationships)

        return symbols, relationships

    def _select_language(self, filepath: str):
        if _TS_LANGUAGE is None or _TSX_LANGUAGE is None:
            return None
        if filepath.endswith((".tsx", ".jsx")):
            return _TSX_LANGUAGE
        return _TS_LANGUAGE

    def _handle_top_level(
        self,
        node,
        source: bytes,
        symbols: list[dict],
        relationships: list[dict],
        comment_anchor=None,
    ) -> None:
        if node.type == "export_statement":
            inner = node.child_by_field_name("declaration")
            if inner is not None:
                self._handle_top_level(inner, source, symbols, relationships, comment_anchor=node)
            return
        anchor = comment_anchor or node
        if node.type == "function_declaration":
            self._append_function(node, source, symbols, relationships, class_name=None, comment_anchor=anchor)
        elif node.type == "class_declaration":
            self._append_class(node, source, symbols, relationships, comment_anchor=anchor)
        elif node.type == "interface_declaration":
            self._append_interface(node, source, symbols, comment_anchor=anchor)
        elif node.type in ("lexical_declaration", "variable_declaration"):
            self._append_variable_declarations(node, source, symbols, relationships, comment_anchor=anchor)

    def _append_function(
        self,
        node,
        source: bytes,
        symbols: list[dict],
        relationships: list[dict],
        class_name: str | None,
        comment_anchor=None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = self._text(source, name_node)
        qualified = f"{class_name}.{name}" if class_name else name

        body_node = node.child_by_field_name("body")
        sig_end = body_node.start_byte if body_node is not None else node.end_byte
        signature = " ".join(self._text(source, node)[: sig_end - node.start_byte].split())

        symbols.append(
            {
                "type": "method" if class_name else "function",
                "name": name,
                "qualified_name": qualified,
                "signature": signature,
                "docstring": self._leading_comment(comment_anchor or node, source),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "metadata": {"class": class_name} if class_name else None,
            }
        )

        if body_node is not None:
            self._append_calls(body_node, source, relationships, qualified)

    def _append_class(
        self, node, source: bytes, symbols: list[dict], relationships: list[dict], comment_anchor=None
    ) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = self._text(source, name_node)
        symbols.append(
            {
                "type": "class",
                "name": name,
                "qualified_name": name,
                "signature": f"class {name}",
                "docstring": self._leading_comment(comment_anchor or node, source),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "metadata": None,
            }
        )

        body = node.child_by_field_name("body")
        if body is None:
            return
        for member in body.named_children:
            if member.type != "method_definition":
                continue
            self._append_function(member, source, symbols, relationships, class_name=name)
            method_name_node = member.child_by_field_name("name")
            if method_name_node is not None:
                method_name = self._text(source, method_name_node)
                relationships.append(
                    {
                        "source": name,
                        "target": f"{name}.{method_name}",
                        "type": "CONTAINS",
                        "line": member.start_point[0] + 1,
                        "metadata": None,
                    }
                )

    def _append_interface(self, node, source: bytes, symbols: list[dict], comment_anchor=None) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = self._text(source, name_node)
        symbols.append(
            {
                "type": "interface",
                "name": name,
                "qualified_name": name,
                "signature": f"interface {name}",
                "docstring": self._leading_comment(comment_anchor or node, source),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "metadata": None,
            }
        )

    def _append_variable_declarations(
        self,
        node,
        source: bytes,
        symbols: list[dict],
        relationships: list[dict],
        comment_anchor=None,
    ) -> None:
        for declarator in node.named_children:
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            value_node = declarator.child_by_field_name("value")
            if name_node is None:
                continue
            name = self._text(source, name_node)

            if value_node is not None and value_node.type in _FUNCTION_VALUE_TYPES:
                body_node = value_node.child_by_field_name("body")
                sig_end = body_node.start_byte if body_node is not None else value_node.end_byte
                value_sig = " ".join(self._text(source, value_node)[: sig_end - value_node.start_byte].split())
                symbols.append(
                    {
                        "type": "function",
                        "name": name,
                        "qualified_name": name,
                        "signature": f"const {name} = {value_sig}",
                        "docstring": self._leading_comment(comment_anchor or node, source),
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "metadata": None,
                    }
                )
                if body_node is not None:
                    self._append_calls(body_node, source, relationships, name)
            else:
                symbols.append(
                    {
                        "type": "variable",
                        "name": name,
                        "qualified_name": name,
                        "signature": None,
                        "docstring": None,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "metadata": {"scope": "module"},
                    }
                )

    def _append_calls(self, body_node, source: bytes, relationships: list[dict], qualified_source: str) -> None:
        for call_node in self._find_calls(body_node):
            callee = self._call_name(call_node, source)
            if not callee:
                continue
            relationships.append(
                {
                    "source": qualified_source,
                    "target": callee,
                    "type": "CALLS",
                    "line": call_node.start_point[0] + 1,
                    "metadata": None,
                }
            )

    def _find_calls(self, node) -> list:
        calls = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.type == "call_expression":
                calls.append(current)
            stack.extend(current.children)
        return calls

    def _call_name(self, call_node, source: bytes) -> str | None:
        func_node = call_node.child_by_field_name("function")
        if func_node is None:
            return None
        if func_node.type == "identifier":
            return self._text(source, func_node)
        if func_node.type == "member_expression":
            return "".join(self._text(source, func_node).split())
        return None

    def _leading_comment(self, node, source: bytes) -> str | None:
        comments = []
        prev = node.prev_sibling
        while prev is not None and prev.type == "comment":
            comments.insert(0, self._text(source, prev).lstrip("/").strip())
            prev = prev.prev_sibling
        return "\n".join(comments) if comments else None

    def _text(self, source: bytes, node) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
