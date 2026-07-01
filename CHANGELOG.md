# Changelog

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
