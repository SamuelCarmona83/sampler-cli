from sampler.indexer.parsers.typescript import TypeScriptParser


def test_typescript_parser_extracts_function_class_interface() -> None:
    src = """
// Adds two numbers.
export function add(a: number, b: number): number {
    return a + b;
}

interface Shape {
    area(): number;
}

export class Calculator {
    // Computes total.
    total(a: number, b: number): number {
        return add(a, b);
    }
}

const run = (x: number) => add(x, 1);
"""
    symbols, relationships = TypeScriptParser().parse(src, "app.ts")

    by_name = {s["qualified_name"]: s for s in symbols}
    assert by_name["add"]["type"] == "function"
    assert by_name["add"]["docstring"] == "Adds two numbers."
    assert by_name["Shape"]["type"] == "interface"
    assert by_name["Calculator"]["type"] == "class"
    assert by_name["Calculator.total"]["type"] == "method"
    assert by_name["Calculator.total"]["docstring"] == "Computes total."
    assert by_name["run"]["type"] == "function"

    rel_types = {(r["source"], r["target"], r["type"]) for r in relationships}
    assert ("Calculator", "Calculator.total", "CONTAINS") in rel_types
    assert ("Calculator.total", "add", "CALLS") in rel_types
    assert ("run", "add", "CALLS") in rel_types


def test_typescript_parser_handles_jsx_extension() -> None:
    src = """
export function Widget() {
    return callHelper();
}
"""
    symbols, relationships = TypeScriptParser().parse(src, "widget.jsx")
    assert any(s["qualified_name"] == "Widget" for s in symbols)
    assert any(r["target"] == "callHelper" for r in relationships)


def test_typescript_parser_handles_syntax_error_gracefully() -> None:
    symbols, relationships = TypeScriptParser().parse("function ((( broken", "broken.ts")
    assert isinstance(symbols, list)
    assert isinstance(relationships, list)
