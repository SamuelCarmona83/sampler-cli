from __future__ import annotations

import ast

from sampler.indexer.parsers.base import BaseParser


class PythonParser(BaseParser):
    language = "python"

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        end_line = max(1, len(content.splitlines()))

        module_qualified = f"module::{filepath}"
        symbols: list[dict] = [
            {
                "type": "module",
                "name": module_qualified,
                "qualified_name": module_qualified,
                "signature": None,
                "docstring": None,
                "start_line": 1,
                "end_line": end_line,
                "metadata": {"filepath": filepath},
            }
        ]
        relationships: list[dict] = []

        try:
            module = ast.parse(content)
        except SyntaxError:
            # If AST fails, return at least module symbol so indexing can continue.
            return symbols, relationships

        for stmt in module.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    import_name = alias.name
                    import_qn = f"import::{import_name}"
                    symbols.append(
                        {
                            "type": "import",
                            "name": import_name,
                            "qualified_name": import_qn,
                            "signature": None,
                            "docstring": None,
                            "start_line": getattr(stmt, "lineno", 1),
                            "end_line": getattr(stmt, "end_lineno", getattr(stmt, "lineno", 1)),
                            "metadata": None,
                        }
                    )
                    relationships.append(
                        {
                            "source": module_qualified,
                            "target": import_qn,
                            "type": "IMPORTS",
                            "line": getattr(stmt, "lineno", 1),
                            "metadata": None,
                        }
                    )

            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    import_qn = f"import::{stmt.module}"
                    symbols.append(
                        {
                            "type": "import",
                            "name": stmt.module,
                            "qualified_name": import_qn,
                            "signature": None,
                            "docstring": None,
                            "start_line": getattr(stmt, "lineno", 1),
                            "end_line": getattr(stmt, "end_lineno", getattr(stmt, "lineno", 1)),
                            "metadata": None,
                        }
                    )
                    relationships.append(
                        {
                            "source": module_qualified,
                            "target": import_qn,
                            "type": "IMPORTS",
                            "line": getattr(stmt, "lineno", 1),
                            "metadata": None,
                        }
                    )

            elif isinstance(stmt, ast.Assign):
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

            elif isinstance(stmt, ast.FunctionDef):
                self._append_function(stmt, symbols, relationships, class_name=None)

            elif isinstance(stmt, ast.ClassDef):
                symbols.append(
                    {
                        "type": "class",
                        "name": stmt.name,
                        "qualified_name": stmt.name,
                        "signature": f"class {stmt.name}",
                        "docstring": ast.get_docstring(stmt),
                        "start_line": getattr(stmt, "lineno", 1),
                        "end_line": getattr(stmt, "end_lineno", getattr(stmt, "lineno", 1)),
                        "metadata": None,
                    }
                )
                for class_stmt in stmt.body:
                    if isinstance(class_stmt, ast.FunctionDef):
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
        func: ast.FunctionDef,
        symbols: list[dict],
        relationships: list[dict],
        class_name: str | None,
    ) -> None:
        qualified = f"{class_name}.{func.name}" if class_name else func.name
        signature = self._build_signature(func)
        symbols.append(
            {
                "type": "method" if class_name else "function",
                "name": func.name,
                "qualified_name": qualified,
                "signature": signature,
                "docstring": ast.get_docstring(func),
                "start_line": getattr(func, "lineno", 1),
                "end_line": getattr(func, "end_lineno", getattr(func, "lineno", 1)),
                "metadata": {"class": class_name} if class_name else None,
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

    def _build_signature(self, func: ast.FunctionDef) -> str:
        args = [arg.arg for arg in func.args.args]
        return f"def {func.name}({', '.join(args)})"

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
