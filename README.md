# Sampler

Token-efficient CLI for indexing and searching code symbols across multiple projects.

Current version: 0.4.1

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
- `sampler callers <symbol> [--project <name>] [--file <path-or-suffix>]`
- `sampler usages <symbol> [--project <name>] [--file <path-or-suffix>]`
- `sampler related <symbol> [--project <name>] [--file <path-or-suffix>] [--style plain|bars]`
- Selector alternativo: `<path>:<symbol>` (ej. `app/utils/helpers.py:format_kda`)

Project management:
- `sampler project add <name> <path> --language <python|go|typescript|javascript|auto>`
- `sampler project update <name> [--path <abs-path>] [--language <lang>]`
- `sampler project list`
- `sampler project deps <name>`
- `sampler project remove <name>`

Config:
- `sampler config show`
- `sampler config embeddings [--provider P] [--model M]`

Semantic and analysis:
- `sampler embed <project> [--batch-size <n>]`
- `sampler stale-code <project> [--limit <n>]`

## Embeddings & Semantic Search

`sampler search --semantic` (and hybrid ranking) supports pluggable providers via the adapter pattern:

- **Default**: `bge-small` (BAAI/bge-small-en-v1.5 via fastembed — lightweight ONNX, ~384 dim, local).
- Other built-ins: `hash` (always-on deterministic fallback), `ollama` (e.g. nomic-embed-text), `nomic`, `openai`, `fastembed`.
- TF-IDF (sklearn, on-the-fly, no pre-embed) remains the fast lexical primary when no provider embeddings are precomputed for the active model.
- Hash fingerprint is the final always-available fallback.

Configuration (in `~/.sampler/config.yaml` or via `sampler config embeddings ...`):

```yaml
embeddings:
  provider: "bge-small"
  # provider: "ollama"
  # model: "nomic-embed-text"
  # base_url: "http://localhost:11434"
```

Install:

```bash
# For default BGE (recommended for most users)
pip install 'sampler-cli[embeddings]'

# Or for Ollama / OpenAI only
pip install 'sampler-cli[ollama-embeddings]'
pip install 'sampler-cli[openai-embeddings]'
```

`sampler embed <project>` precomputes vectors using the **current configured provider** (progress bar). Changing provider? Re-run `embed` after updating config (old vectors are ignored until re-embedded).

Offline / air-gapped: `provider: hash` (or just don't install the embeddings extra — TF-IDF + hash still work if you have `[semantic]`).

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
