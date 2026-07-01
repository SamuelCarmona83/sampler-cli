from pathlib import Path

from sampler.indexer.discover import discover_files, discover_files_multi


def test_discover_files_filters_python_and_ignores(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "b.go").write_text("package main\n", encoding="utf-8")

    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "skip.py").write_text("print('skip')\n", encoding="utf-8")

    files = discover_files(str(tmp_path), "python")

    assert str((tmp_path / "a.py").resolve()) in files
    assert all("skip.py" not in x for x in files)
    assert all(not x.endswith("b.go") for x in files)


def test_discover_files_multi_detects_language_per_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "b.go").write_text("package main\n", encoding="utf-8")
    (tmp_path / "c.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (tmp_path / "readme.md").write_text("not code\n", encoding="utf-8")

    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "skip.js").write_text("skip();\n", encoding="utf-8")

    entries = discover_files_multi(str(tmp_path))
    by_suffix = {Path(p).suffix: lang for p, lang in entries}

    assert by_suffix[".py"] == "python"
    assert by_suffix[".go"] == "go"
    assert by_suffix[".ts"] == "typescript"
    assert ".md" not in by_suffix
    assert all("skip.js" not in p for p, _ in entries)
