from __future__ import annotations

from sampler.indexer.parsers.base import BaseParser

try:
    import tree_sitter_go as _tsgo
    from tree_sitter import Language, Parser as TSParser

    _GO_LANGUAGE = Language(_tsgo.language())
except ImportError:
    _GO_LANGUAGE = None


class GoParser(BaseParser):
    language = "go"

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        symbols: list[dict] = []
        relationships: list[dict] = []

        if _GO_LANGUAGE is None:
            # tree-sitter-go isn't installed; skip gracefully (base install has no Go support).
            return symbols, relationships

        source = content.encode("utf-8")
        parser = TSParser(_GO_LANGUAGE)
        tree = parser.parse(source)

        for node in tree.root_node.children:
            if node.type == "function_declaration":
                self._append_function(node, source, symbols, relationships, receiver=None)
            elif node.type == "method_declaration":
                receiver = self._receiver_type(node, source)
                self._append_function(node, source, symbols, relationships, receiver=receiver)
            elif node.type == "type_declaration":
                self._append_type(node, source, symbols)
            elif node.type in ("var_declaration", "const_declaration"):
                self._append_package_vars(node, source, symbols)

        return symbols, relationships

    def _append_function(
        self,
        node,
        source: bytes,
        symbols: list[dict],
        relationships: list[dict],
        receiver: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = self._text(source, name_node)
        qualified = f"{receiver}.{name}" if receiver else name

        body_node = node.child_by_field_name("body")
        sig_end = body_node.start_byte if body_node is not None else node.end_byte
        signature = " ".join(self._text(source, node)[: sig_end - node.start_byte].split())

        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        symbols.append(
            {
                "type": "method" if receiver else "function",
                "name": name,
                "qualified_name": qualified,
                "signature": signature,
                "docstring": self._leading_comment(node, source),
                "start_line": start_line,
                "end_line": end_line,
                "metadata": {"receiver": receiver} if receiver else None,
            }
        )

        if receiver:
            relationships.append(
                {
                    "source": receiver,
                    "target": qualified,
                    "type": "CONTAINS",
                    "line": start_line,
                    "metadata": None,
                }
            )

        if body_node is not None:
            for call_node in self._find_calls(body_node):
                callee = self._call_name(call_node, source)
                if not callee:
                    continue
                relationships.append(
                    {
                        "source": qualified,
                        "target": callee,
                        "type": "CALLS",
                        "line": call_node.start_point[0] + 1,
                        "metadata": None,
                    }
                )

    def _receiver_type(self, node, source: bytes) -> str | None:
        receiver_node = node.child_by_field_name("receiver")
        if receiver_node is None:
            return None
        for child in receiver_node.named_children:
            if child.type != "parameter_declaration":
                continue
            type_node = child.child_by_field_name("type")
            if type_node is None:
                continue
            if type_node.type == "pointer_type" and type_node.named_children:
                return self._text(source, type_node.named_children[0])
            return self._text(source, type_node)
        return None

    def _append_type(self, node, source: bytes, symbols: list[dict]) -> None:
        for spec in node.named_children:
            if spec.type != "type_spec":
                continue
            name_node = spec.child_by_field_name("name")
            type_node = spec.child_by_field_name("type")
            if name_node is None:
                continue
            name = self._text(source, name_node)
            if type_node is not None and type_node.type == "struct_type":
                kind = "struct"
            elif type_node is not None and type_node.type == "interface_type":
                kind = "interface"
            else:
                kind = "type"
            symbols.append(
                {
                    "type": kind,
                    "name": name,
                    "qualified_name": name,
                    "signature": f"type {name} {kind}",
                    "docstring": self._leading_comment(node, source),
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "metadata": None,
                }
            )

    def _append_package_vars(self, node, source: bytes, symbols: list[dict]) -> None:
        kind = "variable" if node.type == "var_declaration" else "constant"
        for spec in node.named_children:
            if spec.type not in ("var_spec", "const_spec"):
                continue
            name_node = spec.child_by_field_name("name")
            if name_node is None:
                continue
            name = self._text(source, name_node)
            symbols.append(
                {
                    "type": kind,
                    "name": name,
                    "qualified_name": name,
                    "signature": None,
                    "docstring": None,
                    "start_line": spec.start_point[0] + 1,
                    "end_line": spec.end_point[0] + 1,
                    "metadata": {"scope": "package"},
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
        if func_node.type == "selector_expression":
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
