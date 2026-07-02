# CLI Reference

## Commands

- `sampler version [--plain]`
- `sampler init`
- `sampler project add <name> <path> --language <python|go|typescript|javascript|auto>`
- `sampler project update <name> [--path <path>] [--language <language>]`
- `sampler project list`
- `sampler project deps <name>`
- `sampler project remove <name>`
- `sampler index <project>`
- `sampler search <query> [--project <name>] [--type <t>] [--limit <n>] [--semantic] [--style plain|bars]`
- `sampler search-all <query> [--type <t>] [--limit <n>]`
- `sampler symbols <project> [--type <t>] [--limit <n>]`
- `sampler overview <filepath> [--style plain|bars]`
- `sampler callers <symbol> [--project <name>] [--file <path-or-suffix>]`
- `sampler usages <symbol> [--project <name>] [--file <path-or-suffix>]`
- `sampler related <symbol> [--project <name>] [--file <path-or-suffix>] [--style plain|bars]`
- `sampler embed <project> [--batch-size <n>]`
- `sampler stale-code <project> [--limit <n>]`
- `sampler config show`
- `sampler config embeddings [--provider <p>] [--model <m>] [--base-url <u>]`

### Notes on `config`
- `sampler config embeddings` lets you switch providers (bge-small default, ollama, hash for offline, openai, ...).
- After changing provider run `sampler embed <project>` again.
- API keys (OpenAI) come from environment variables.

### Notes on relationship commands
- If a symbol name is ambiguous, disambiguate with `--file`.
- `--file` accepts absolute paths and suffix paths.
- You can also pass selector syntax `<path>:<symbol>` as a single SYMBOL argument.

### Notes on `overview`
- Accepts relative paths (resolved from your current directory).
- If the file has no indexed symbols: prints a clear "No symbols found" message with usage tips.

### Notes on `index`
- Supports projects configured with `--language auto` for mixed-language repositories.

### Notes on semantic search
- `search --semantic` uses the configured embeddings provider (default bge-small) when precomputed vectors are available for the project.
- Falls back intelligently: provider vectors → TF-IDF (sklearn) → hash fingerprint.
- Install `pip install 'sampler-cli[embeddings]'` (or ollama-/openai- variant) for real models.
- Run `sampler embed <project>` after index or after changing provider.

### Notes on `embed`
- Generates embeddings using the provider selected in config (bge-small by default via fastembed).
- Displays progress using Rich progress bars.
- Stored vectors are tagged with the provider model so switching providers is safe (old vectors ignored until re-embed).

### Notes on `stale-code`
- Returns heuristic stale candidates: symbols called from tests but with no non-test callers.
- Excludes symbols defined inside test files (test helpers/fixtures are not reported as stale).
- Test-file detection supports common multi-language patterns:
	- directories: `tests/`, `test/`, `__tests__/`, `spec/`
	- Python: `test_*.py`, `*_test.py`
	- Go: `*_test.go`
	- TypeScript/JavaScript: `*.test.*`, `*.spec.*`

### Notes on `version`
- `sampler version --plain` prints plain text (`sampler <version>`) for scripts/CI.
- `sampler version` in TTY can render richer output; non-TTY defaults to plain format.
