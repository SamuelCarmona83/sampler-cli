# Changelog

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
