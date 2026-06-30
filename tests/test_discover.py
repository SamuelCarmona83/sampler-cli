from pathlib import Path

from sampler.indexer.discover import discover_files


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
