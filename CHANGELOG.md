# Changelog

## [0.4.1] - 2026-07-01

### Added
- Relationship commands (`callers`, `usages`, `related`) now support disambiguation by file:
  - `--file <path-or-suffix>`
  - selector syntax `<path>:<symbol>` (example: `app/utils/helpers.py:format_kda`).

### Changed
- Cross-file relation resolution in index/store improved with safe heuristics:
  - exact local/project match first
  - unique leaf-name fallback for dotted calls (`module.fn` -> `fn`)
  - class-aware method preference (`Class.method` for `self.method` style calls)
  - ambiguity-safe behavior (skip unresolved relations instead of linking wrong symbol)
- Ambiguity hints in relationship commands now guide to `--file` when `--project` is already provided.

### Notes
- This release improves precision of `callers`/`usages` on real multi-file projects.
- Test suite status after change: 46 passed.

## [0.4.0] - 2026-07-01

### Added
- Embeddings layer redesigned as pluggable **EmbeddingProvider** adapter (per design in user request).
  - Interface: `embed(text, *, for_query=False) -> list[float]`, `embed_batch`, `.name`, `.dimension`, `.model_id`.
  - Providers: `BGEProvider` (default) + `HashProvider` (offline). Others (Nomic/Ollama/OpenAI/Fast) second stage per request. Interface supports adding without touching rest of system.
  - Global config support under `embeddings:` (`provider`, `model`, `base_url`).
  - New CLI: `sampler config show`, `sampler config embeddings --provider ...`.
- `sampler embed` now uses the active provider from config; progress + final message include provider details.
- Semantic scoring prefers provider vectors (when pre-embedded + model matches) → TF-IDF → hash.
- Much cleaner command output: Rich markup (dim paths, bold symbol names, colored types by kind, highlighted scores), Rich tables for `project list`, consistent ✓ success messages, less noisy stale-code etc.
- New optional extras: `[embeddings]`, `[ollama-embeddings]`, `[openai-embeddings]`.
- `tests/test_embeddings.py` + expanded semantic/config/cli tests with provider mocks.
- Helpful errors + offline guidance when ML provider deps missing.
- Updated docs (README embeddings section + examples, TODO, CLI_REFERENCE, ARCHITECTURE).

### Changed
- `Embedder` evolved to accept `provider=` and default to config-driven provider while preserving full backward compat + legacy encode_fn/hash_bits paths.
- `embed` help and messages updated; `project list` now uses table by default.
- All existing commands continue to work; hash/TF-IDF paths unchanged for users without embeddings extras.

### Notes
- Default provider is now `bge-small`. Existing projects keep working (hash fallback in scoring).
- To use real vectors: `pip install 'sampler-cli[embeddings]'` then `sampler embed <proj>`.
- For fully offline: `sampler config embeddings --provider hash`.
- All 42 tests green.

## [0.3.0] - 2026-07-01

### Added
- Real Go parser (tree-sitter-go): functions, methods with receiver, structs/interfaces, constants/variables, `CALLS` + `CONTAINS` relations.
- Real TypeScript/JavaScript parser (tree-sitter-typescript): functions, classes/methods, interfaces, arrow-function vars, `CALLS` + `CONTAINS`.
- Monorepo/multi-language indexing via `--language auto` (per-file language detection + parser dispatch).
- New relationship commands: `callers`, `usages`, `related`.
- New project command: `project update`.
- New project dependency command: `project deps` (heuristic import-based cross-project dependency mapping).
- New stale code command: `stale-code` (functions called by tests but not by non-test code).
- `--style bars` output mode for `search`, `overview`, and `related`.

### Changed
- Semantic backend migrated away from model-based embeddings to local deterministic stack:
	- TF-IDF (primary semantic backend).
	- Hash fingerprint vectors (fallback backend, no provider/model dependency).
- `embed` command now builds local hash fingerprints and shows progress with Rich.
- `end_line` now exposed in query outputs used by CLI views.

### Removed
- Runtime dependency on `sentence-transformers` for semantic search.

### Notes
- All tests green after release changes.

## [0.2.1] - 2026-07-01

### Added
- `symbols <project>` command to list all symbols of a project (with `--type` and `--limit` filters). Great for quick overview.
- Smart relative path support in `overview` (resolves from cwd and also tries relative to registered project roots).
- Clear "No symbols found" message + usage tips when `overview` finds nothing.

### Changed
- Improved error messages across commands with exact command suggestions and tips (e.g. for missing projects).
- README fully rewritten in English, with example outputs, explanation of `project add` requirement, and token-efficient usage notes.
- Added `no_args_is_help=True` for better default CLI help.

### Fixed
- Better handling and messaging for missing files in overview.

See PLAN.md and TODO.md for roadmap.

## [0.2.0] - 2026-07-01

### Added
- Type filters (`--type`), limit (`--limit`) and `search-all` command for QueryEngine.
- Python AST parser improvements: AsyncFunctionDef, decorators in metadata, full annotations/returns in signatures.
- Ultra-minimal default outputs for `search`, `overview`, `project list` (compact lines, short paths, no tables) for lowest token use with LLMs/agents.
- Removed noisy `module::` and `import::` symbols from index.

### Changed
- Switched to pure compact output by default (no --format option in core commands for simplicity).
- Project list now shows `name ~/short/path` (or tail for non-home).

### Fixed
- SQL precedence in type filters.

See PLAN.md and TODO.md for roadmap.

## [0.1.2] - 2026-06-30
Initial MVP with core indexing/search/overview and basic token optimizations.
