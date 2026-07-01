# CLI Reference

## Commands

- `sampler version`
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
- `sampler callers <symbol> [--project <name>]`
- `sampler usages <symbol> [--project <name>]`
- `sampler related <symbol> [--project <name>] [--style plain|bars]`
- `sampler embed <project> [--batch-size <n>]`
- `sampler stale-code <project> [--limit <n>]`

### Notes on `overview`
- Accepts relative paths (resolved from your current directory).
- If the file has no indexed symbols: prints a clear "No symbols found" message with usage tips.

### Notes on `index`
- Supports projects configured with `--language auto` for mixed-language repositories.

### Notes on semantic search
- `search --semantic` uses TF-IDF as primary ranking backend.
- Falls back to local hash fingerprint similarity when needed.

### Notes on `embed`
- Generates deterministic local hash fingerprints for symbols.
- Displays progress using Rich progress bars.

### Notes on `stale-code`
- Returns heuristic stale candidates: symbols called from tests but with no non-test callers.
