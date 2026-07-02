from sampler.indexer.parsers.vue import VueParser
from sampler.indexer.parsers.typescript import TypeScriptParser


def test_vue_parser_extracts_script_and_offsets_lines() -> None:
    src = """<template>
  <div>Hello {{ msg }}</div>
</template>

<script setup lang="ts">
// comment
export const vArrow = (x: number) => x + 1;

export function setupHelper() {
    return vArrow(41);
}

const run = () => setupHelper();
</script>

<style>
div { color: red; }
</style>
"""
    symbols, relationships = VueParser().parse(src, "Comp.vue")

    by_name = {s["qualified_name"]: s for s in symbols}
    assert "vArrow" in by_name
    assert by_name["vArrow"]["type"] == "function"
    # script body starts around line 6-7 in the src above; line numbers must be offset (not 1)
    assert by_name["vArrow"]["start_line"] > 5
    assert by_name["setupHelper"]["type"] == "function"
    assert "run" in by_name

    # Relationships (CALLS) should be present and lines offset
    rel_targets = {r["target"] for r in relationships}
    assert "setupHelper" in rel_targets or "vArrow" in rel_targets  # at least one call captured

    # No template/style symbols
    assert not any("template" in (s.get("name") or "").lower() for s in symbols)


def test_vue_parser_handles_script_without_lang_and_setup() -> None:
    src = """<script>
export function plainJs() { return 42; }
const arr = () => plainJs();
</script>
"""
    symbols, _ = VueParser().parse(src, "Widget.vue")
    names = {s["name"] for s in symbols}
    assert "plainJs" in names
    assert "arr" in names
    # lines should be sensible (>1 because of the <script> tag)
    assert any(s["start_line"] > 1 for s in symbols)


def test_vue_parser_returns_empty_for_no_script() -> None:
    src = """<template><p>no script here</p></template>
<style>.foo{}</style>
"""
    symbols, relationships = VueParser().parse(src, "NoScript.vue")
    assert symbols == []
    assert relationships == []


def test_vue_parser_graceful_on_bad_inner_content() -> None:
    src = """<script setup>
function ((( broken
</script>
"""
    symbols, relationships = VueParser().parse(src, "Broken.vue")
    # Delegate (TS parser) is tolerant; we just get what it gives (lists)
    assert isinstance(symbols, list)
    assert isinstance(relationships, list)


def test_vue_parser_delegates_and_reuses_ts_logic() -> None:
    # Sanity: the inner logic (including arrows via const, classes, etc) is provided by delegate
    # (we don't re-test all TS cases here)
    src = """<script lang="ts">
export class Foo {
    bar = () => 1;  // arrow field -> should surface via delegate
}
const helper = (y) => y * 2;
</script>
"""
    symbols, _ = VueParser().parse(src, "WithClass.vue")
    names = {s["qualified_name"] for s in symbols}
    assert "Foo" in names
    # The delegate will surface "Foo.bar" as method (or at minimum the class); helper too
    assert any("helper" in n for n in names)
