<p align="center">
  <img src="./assets/sampler.png" alt="Sampler logo" width="220">
</p>

<h1 align="center">Sampler</h1>

<p align="center">
  <strong>Token-efficient CLI for indexing and searching code symbols across projects.</strong><br>
  Compact output. Short paths. Low-noise symbol views.
</p>

<p align="center">
  <a href="https://pypi.org/project/sampler-cli/"><img src="https://img.shields.io/pypi/v/sampler-cli" alt="PyPI version"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
</p>

---

> *The code isn't the problem. The problem is the distance between you and the code.*
>
> Sampler closes that distance. One index. One query. The right symbol, the right relationship, the right context — delivered without the noise. Because in a world drowning in repositories, the person who finds what matters first is the person who moves the work forward.

## Installation

```bash
pip install sampler-cli
```

Development:

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

## Commands

### Core

| Command | Description |
| --- | --- |
| `sampler version [--plain]` | Show version |
| `sampler init` | Initialize Sampler config and data directory |
| `sampler index <project>` | Index a project's symbols and relationships |
| `sampler search <query>` | Search symbols across a project |
| `sampler search-all <query>` | Search across all indexed projects |
| `sampler symbols <project>` | List symbols in a project |
| `sampler overview <filepath>` | Show symbol overview for a file |

**Search options:** `--project`, `--type`, `--limit`, `--semantic`, `--style plain|bars`

### Relationships

| Command | Description |
| --- | --- |
| `sampler callers <symbol>` | Find callers of a symbol |
| `sampler usages <symbol>` | Find usages of a symbol |
| `sampler related <symbol>` | Find related symbols |

Symbols can also be selected as `<path>:<symbol>`, e.g. `app/utils/helpers.py:format_kda`.

### Project Management

| Command | Description |
| --- | --- |
| `sampler project add <name> <path> --language <lang>` | Add a project |
| `sampler project update <name>` | Update project path or language |
| `sampler project list` | List projects |
| `sampler project deps <name>` | Show project dependencies |
| `sampler project remove <name>` | Remove a project |

Languages: `python`, `go`, `typescript`, `javascript`, `vue`, `auto`.

### Config & Analysis

| Command | Description |
| --- | --- |
| `sampler config show` | Show current config |
| `sampler config embeddings` | Configure embedding provider |
| `sampler embed <project>` | Precompute embeddings |
| `sampler stale-code <project>` | Find candidate stale code |

## Embeddings & Semantic Search

`sampler search --semantic` uses a pluggable adapter pattern:

- **Default:** `bge-small` (BAAI/bge-small-en-v1.5 via fastembed — local ONNX, ~384 dim)
- **Built-ins:** `hash` (deterministic fallback), `ollama`, `nomic`, `openai`, `fastembed`
- **Lexical primary:** TF-IDF (sklearn, on-the-fly, no pre-embedding required)
- **Final fallback:** hash fingerprint (always available)

Configure in `~/.sampler/config.yaml` or via `sampler config embeddings`:

```yaml
embeddings:
  provider: "bge-small"
  # provider: "ollama"
  # model: "nomic-embed-text"
  # base_url: "http://localhost:11434"
```

Install extras:

```bash
pip install 'sampler-cli[embeddings]'        # BGE (recommended)
pip install 'sampler-cli[ollama-embeddings]'
pip install 'sampler-cli[openai-embeddings]'
```

Run `sampler embed <project>` to precompute vectors for the active provider. Change providers? Re-run `embed` after updating config.

Offline or air-gapped: set `provider: hash`, or rely on TF-IDF + hash with the `[semantic]` extra.

## Language Support

| Language | Parser |
| --- | --- |
| Python | stdlib AST |
| Go | tree-sitter-go |
| TypeScript / JavaScript | tree-sitter-typescript |
| Vue | Extracts `<script>` / `<script setup>`, delegates to TS/JS parser |
| Auto | Per-file detection for monorepos and multi-language projects |

## Stale Code Detection

`sampler stale-code <project>` finds functions that may no longer be needed:

- Called only from test files
- Zero non-test callers in the project call graph
- Defined in production code

Supported test patterns:

- Python: `tests/`, `test_*.py`, `*_test.py`
- Go: `*_test.go`
- TypeScript / JavaScript / Vue: `__tests__/`, `test/`, `spec/`, `*.test.*`, `*.spec.*`

This is a heuristic signal, not a guarantee of dead code.

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
- Database: `~/.sampler/graph.db`

## Running Tests

```bash
pytest -q
```

## Notes

- Compact output is the default by design — built for agent workflows and fast human scanning.
- For roadmap details, see [TODO.md](TODO.md) and [PLAN.md](PLAN.md).
