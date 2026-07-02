# Architecture

Sampler is a local-first code intelligence CLI composed of 5 layers:

1. CLI (`src/sampler/cli/main.py`)
2. Indexing (`src/sampler/indexer/`)
3. Persistence (`src/sampler/db.py`)
4. Query engine (`src/sampler/query/`)
5. Optional MCP server (`src/sampler/mcp/server.py`)

## High-Level Flow

1. Register project (`project add` / `project update`) in `~/.sampler/config.yaml`.
2. Index source files (`index`) with language-aware parsers.
3. Persist symbols + relationships in SQLite (`~/.sampler/graph.db`).
4. Query by name, relationships, semantic search, and stale-code heuristics.

## Components

### CLI

- Entry point: `src/sampler/cli/main.py`
- Rendering helpers: `src/sampler/cli/render.py`
- Commands include:
	- project management (`add`, `update`, `list`, `deps`, `remove`)
	- indexing/search/overview/symbols
	- graph commands (`callers`, `usages`, `related`)
	- semantic embedding (`embed`)
	- stale code detection (`stale-code`)

### Indexer

- Discovery: `src/sampler/indexer/discover.py`
	- Supports monorepo mode via `--language auto`.
- Build orchestration: `src/sampler/indexer/builder.py`
- Storage adapter: `src/sampler/indexer/store.py`
	- Cross-file relation resolver uses safe heuristics (exact match -> unique leaf fallback -> class-method preference) and skips ambiguous links.
- Import heuristics for cross-project deps: `src/sampler/indexer/imports.py`
- Embedding generation: `src/sampler/indexer/embedder.py` + `src/sampler/embeddings.py` (single file adapter layer)
	- Pluggable EmbeddingProvider adapter (BGE default + hash now; others second stage)
	- Hash fingerprint still fully supported as zero-dep fallback
	- Config-driven (GlobalConfig.embeddings) + factory
	- Rich progress callbacks for batch generation

### Parsers

- Python: `src/sampler/indexer/parsers/python.py` (stdlib AST)
- Go: `src/sampler/indexer/parsers/go.py` (tree-sitter-go)
- TypeScript/JavaScript: `src/sampler/indexer/parsers/typescript.py` (tree-sitter-typescript)

Parsers emit:
- symbols (function, method, class, interface, variable, etc.)
- relationships (`CONTAINS`, `CALLS`)

### Database

Core module: `src/sampler/db.py`

Main entities:
- `projects`
- `files`
- `symbols`
- `relationships`
- `project_dependencies`
- `embeddings`

Supports:
- incremental updates (file hash-aware index pipeline)
- relationship traversals (callers/usages/related)
- embedding storage/retrieval for semantic ranking

### Query Layer

- API facade: `src/sampler/query/engine.py`
- Semantic ranker: `src/sampler/query/semantic.py`
- Stale-code heuristic (`QueryEngine.stale_code_candidates`):
	- flags production symbols called only from tests
	- excludes symbols defined in test files
	- test-path classification is multi-language aware (Python/Go/TypeScript/JavaScript):
		- directories: `tests/`, `test/`, `__tests__/`, `spec/`
		- suffix/patterns: `test_*.py`, `*_test.py`, `*_test.go`, `*.test.*`, `*.spec.*`

Semantic strategy:
1. Configured provider vectors (BGE/Ollama/etc) when `embed` has been run for that model (preferred when available).
2. TF-IDF candidate scoring (on-the-fly, great lexical fallback, sklearn optional).
3. Hash-fingerprint cosine similarity (always works).
4. Hybrid ranking supported for mixed lexical/semantic behavior.

### MCP Layer

- `src/sampler/mcp/server.py` exposes search/query capabilities for agent tooling.

## Design Choices

- Local-first operation: no required external embedding/model provider.
- Compact CLI output by default for token-efficient agent workflows.
- Parser stability priority on Python via stdlib AST.
