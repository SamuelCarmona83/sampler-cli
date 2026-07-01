# Sampler

Token-efficient CLI for indexing and searching code symbols across multiple projects.

Current version: 0.3.0

Designed for humans and agents: compact default output, short paths, and low-noise symbol views.

## Requirements

- Python 3.11+

## Installation

```bash
pip install sampler-cli
```

Development setup:

```bash
pip install -e '.[dev]'
```

Semantic stack (TF-IDF + local hash fallback):

```bash
pip install -e '.[semantic]'
```

## Quick Start

```bash
sampler init
sampler project add myproj /absolute/path/to/project --language auto
sampler index myproj
sampler search retry --project myproj
sampler symbols myproj
sampler overview src/main.py
```

## Command Overview

Core:
- `sampler version`
- `sampler init`
- `sampler index <project>`
- `sampler search <query> [--project <name>] [--type <t>] [--limit <n>] [--semantic] [--style plain|bars]`
- `sampler search-all <query> [--type <t>] [--limit <n>]`
- `sampler symbols <project> [--type <t>] [--limit <n>]`
- `sampler overview <filepath> [--style plain|bars]`

Relationships:
- `sampler callers <symbol> [--project <name>]`
- `sampler usages <symbol> [--project <name>]`
- `sampler related <symbol> [--project <name>] [--style plain|bars]`

Project management:
- `sampler project add <name> <path> --language <python|go|typescript|javascript|auto>`
- `sampler project update <name> [--path <abs-path>] [--language <lang>]`
- `sampler project list`
- `sampler project deps <name>`
- `sampler project remove <name>`

Semantic and analysis:
- `sampler embed <project> [--batch-size <n>]`
- `sampler stale-code <project> [--limit <n>]`

## Semantic Search Backend

`sampler search --semantic` uses:

1. TF-IDF scoring over structured per-symbol text (`Function/File/Arguments/Docstring`).
2. Hash-fingerprint fallback backend (fully local, deterministic, no model provider dependency).

`sampler embed` precomputes hash fingerprints into SQLite and shows a progress bar.

## Language Support

- Python parser: stdlib AST (stable)
- Go parser: tree-sitter-go (real extraction)
- TypeScript/JavaScript parser: tree-sitter-typescript (real extraction)
- `--language auto`: per-file language detection for monorepos/multi-language projects

## Stale Code Detection

`sampler stale-code <project>` reports candidate stale functions/methods where:

- function is called from test files
- function has zero non-test callers in project call graph

This is heuristic signal, not guaranteed dead-code proof.

## Examples

```bash
$ sampler search worker --project myproj
myproj:src/tasks/celery_app.py:70 function on_worker_ready  def on_worker_ready(sender)

$ sampler related ConfigManager --project myproj --style bars
myproj:src/config.py:24-105 class ConfigManager  [parent]
...

$ sampler stale-code myproj
myproj:src/utils/retry.py:12-28 function retry_request  test_callers=2 non_test_callers=0  [tests.test_retry.test_retry_request]
```

## Data Location

- Config: `~/.sampler/config.yaml`
- DB: `~/.sampler/graph.db`

## Running Tests

```bash
pytest -q
```

## Notes

- Compact output is default by design (token-efficient for agent workflows).
- For broader roadmap details, see `TODO.md` and `PLAN.md`.
