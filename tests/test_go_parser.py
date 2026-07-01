from sampler.indexer.parsers.go import GoParser


def test_go_parser_extracts_struct_and_method() -> None:
    src = """package main

// Adder adds numbers.
type Adder struct {
    base int
}

// Add adds a value to base.
func (a *Adder) Add(x int) int {
    return helper(a.base, x)
}

func helper(x, y int) int {
    return x + y
}

var Version = "1.0"
const Max = 10
"""
    symbols, relationships = GoParser().parse(src, "main.go")

    by_name = {s["qualified_name"]: s for s in symbols}
    assert by_name["Adder"]["type"] == "struct"
    assert by_name["Adder"]["docstring"] == "Adder adds numbers."
    assert by_name["Adder.Add"]["type"] == "method"
    assert by_name["Adder.Add"]["docstring"] == "Add adds a value to base."
    assert by_name["helper"]["type"] == "function"
    assert by_name["Version"]["type"] == "variable"
    assert by_name["Max"]["type"] == "constant"

    rel_types = {(r["source"], r["target"], r["type"]) for r in relationships}
    assert ("Adder", "Adder.Add", "CONTAINS") in rel_types
    assert ("Adder.Add", "helper", "CALLS") in rel_types


def test_go_parser_handles_syntax_error_gracefully() -> None:
    symbols, relationships = GoParser().parse("this is not valid go {{{", "broken.go")
    # tree-sitter is error-tolerant; should not raise, may just yield fewer/no symbols.
    assert isinstance(symbols, list)
    assert isinstance(relationships, list)
