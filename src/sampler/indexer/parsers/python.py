from __future__ import annotations

import ast

from sampler.indexer.parsers.base import BaseParser


class PythonParser(BaseParser):
    language = "python"

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        symbols: list[dict] = []
        relationships: list[dict] = []

        try:
            module = ast.parse(content)
        except SyntaxError:
            # Syntax error: no symbols extracted for this file (indexing continues).
            return symbols, relationships

        for stmt in module.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        symbols.append(
                            {
                                "type": "variable",
                                "name": target.id,
                                "qualified_name": target.id,
                                "signature": None,
                                "docstring": None,
                                "start_line": getattr(stmt, "lineno", 1),
                                "end_line": getattr(stmt, "end_lineno", getattr(stmt, "lineno", 1)),
                                "metadata": {"scope": "module"},
                            }
                        )

            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._append_function(stmt, symbols, relationships, class_name=None)

            elif isinstance(stmt, ast.ClassDef):
                decos = [ast.unparse(d) if not isinstance(d, ast.Name) else d.id for d in stmt.decorator_list] or None
                symbols.append(
                    {
                        "type": "class",
                        "name": stmt.name,
                        "qualified_name": stmt.name,
                        "signature": f"class {stmt.name}",
                        "docstring": ast.get_docstring(stmt),
                        "start_line": getattr(stmt, "lineno", 1),
                        "end_line": getattr(stmt, "end_lineno", getattr(stmt, "lineno", 1)),
                        "metadata": {"decorators": decos} if decos else None,
                    }
                )
                for class_stmt in stmt.body:
                    if isinstance(class_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self._append_function(class_stmt, symbols, relationships, class_name=stmt.name)
                        relationships.append(
                            {
                                "source": stmt.name,
                                "target": f"{stmt.name}.{class_stmt.name}",
                                "type": "CONTAINS",
                                "line": getattr(class_stmt, "lineno", 1),
                                "metadata": None,
                            }
                        )

        return symbols, relationships

    def _append_function(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        symbols: list[dict],
        relationships: list[dict],
        class_name: str | None,
    ) -> None:
        qualified = f"{class_name}.{func.name}" if class_name else func.name
        signature = self._build_signature(func)
        is_async = isinstance(func, ast.AsyncFunctionDef)
        typ = ("async method" if class_name else "async function") if is_async else ("method" if class_name else "function")
        decos = [ast.unparse(d) if not isinstance(d, ast.Name) else d.id for d in func.decorator_list] or None
        meta = {"class": class_name} if class_name else {}
        if decos:
            meta["decorators"] = decos
        symbols.append(
            {
                "type": typ,
                "name": func.name,
                "qualified_name": qualified,
                "signature": signature,
                "docstring": ast.get_docstring(func),
                "start_line": getattr(func, "lineno", 1),
                "end_line": getattr(func, "end_lineno", getattr(func, "lineno", 1)),
                "metadata": meta or None,
            }
        )

        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            callee = self._call_name(node.func)
            if not callee:
                continue
            relationships.append(
                {
                    "source": qualified,
                    "target": callee,
                    "type": "CALLS",
                    "line": getattr(node, "lineno", getattr(func, "lineno", 1)),
                    "metadata": None,
                }
            )

    def _build_signature(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        prefix = "async def" if isinstance(func, ast.AsyncFunctionDef) else "def"
        args = []
        for arg in func.args.args:
            a = arg.arg
            if arg.annotation:
                a += f": {ast.unparse(arg.annotation)}"
            args.append(a)
        sig = f"{prefix} {func.name}({', '.join(args)})"
        if func.returns:
            sig += f" -> {ast.unparse(func.returns)}"
        return sig

    def _call_name(self, func_expr: ast.expr) -> str | None:
        if isinstance(func_expr, ast.Name):
            return func_expr.id
        if isinstance(func_expr, ast.Attribute):
            chain: list[str] = []
            current: ast.expr | None = func_expr
            while isinstance(current, ast.Attribute):
                chain.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                chain.append(current.id)
            return ".".join(reversed(chain)) if chain else None
        return None
