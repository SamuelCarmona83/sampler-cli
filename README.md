# Sampler

**Token-efficient CLI for indexing and searching code symbols across multiple projects.**

Current version: 0.2.1

Designed for humans and LLMs/agents: default outputs are compact, single-line, with short paths and no noisy table formatting.

## Requirements

- Python 3.11+
- (Optional) Go, if you plan to use Go parser support in the future

## Installation

```bash
pip install sampler-cli
```

For development (tests, linters, etc.):

```bash
pip install -e '.[dev]'
```

## Quick Start

```bash
sampler init
sampler project add myproj /absolute/path/to/project --language python
sampler project list
sampler index myproj
sampler search add --project myproj
sampler overview /absolute/path/to/project/some/file.py
sampler symbols myproj
```

## Examples with Output

**List projects (compact):**
```bash
$ sampler project list
myproj /home/user/projects/myproj
demo   ~/work/demo
```

**Search (default compact, LLM-friendly):**
```bash
$ sampler search worker --project myproj
myproj:src/tasks/celery_app.py:70 function on_worker_ready  def on_worker_ready(sender)
```

**List all symbols for a project:**
```bash
$ sampler symbols myproj --type function --limit 5
myproj:src/utils.py:10 function helper  def helper(x)
myproj:src/models.py:25 function validate  def validate(data)
...
```

**Overview of a file (supports relative paths):**
```bash
$ sampler overview src/app.py
12: function main  def main()
25: class App  class App
```

If the file has no indexed symbols (or was never indexed):
```bash
$ sampler overview nonexistent.py
No symbols found for file: nonexistent.py
Tip: Make sure the project is registered with 'sampler project add' and indexed with 'sampler index <project>'.
The path must match a file that was indexed (relative paths are resolved to absolute).
```

## Why "project add" is required

- `sampler project add <name> <path>` registers the project in `~/.sampler/config.yaml`.
- `index` looks up the project there to know the root path and language.
- Without it, commands like `index`, `symbols`, and filtered searches will fail with a clear "not found" message and usage hint.
- The actual symbol data lives in the SQLite DB (`~/.sampler/graph.db`), but registration is the control plane.

You can have data in the DB without the config entry (e.g. after `project remove`), but you won't be able to re-index or easily manage it.

## Relative Paths

- `overview` now resolves relative paths against the current working directory (e.g. `sampler overview ./src/app.py` or `sampler overview ../other/file.py`).
- Stored paths are absolute (resolved at index time), so the resolution makes overview work naturally.
- Other file-based commands behave similarly where applicable.

## Error Messages & Help

We try to give actionable errors:

- Unknown project → tells you the exact `project add` command to run and suggests `project list`.
- File with no symbols → clear "No symbols found" + tips.
- Typer automatically shows command usage and available options on invalid arguments.

Run any command with `--help` for full details (e.g. `sampler search --help`, `sampler symbols --help`).

## Current Features

- Global config in `~/.sampler/config.yaml`
- Project management (`add`, `list`, `remove`)
- Incremental indexing with file hashing (Python AST-based parser)
- Compact, token-efficient output by default (great for LLMs)
- Search with type filters and limits
- `search-all` across every registered project
- `symbols <project>` to dump/list symbols for a project
- `overview <file>` (relative paths supported)
- Basic relationship extraction (CALLS, CONTAINS)

## Stability Note

- Python parser uses stdlib `ast` (we switched from tree-sitter-python after native crashes on macOS ARM during real indexing).
- Go and TypeScript/JavaScript parsers are stubs for now (return no symbols).

## Project Structure

```
src/sampler/
├── cli/main.py          # Typer commands (search, overview, symbols, index, project ...)
├── config.py            # YAML config manager
├── db.py                # SQLite layer
├── indexer/
│   ├── builder.py
│   ├── discover.py
│   ├── store.py
│   └── parsers/python.py
└── query/engine.py
```

## Running Tests

```bash
pytest -q
```

## Roadmap Highlights (see TODO.md and PLAN.md)

- Cross-file relation improvements
- Better call graph queries (`callers`, `usages`, ...)
- Real Go / TypeScript parsers
- Semantic search + MCP server (for agents)
- More context-generation helpers
