# CLI Reference

## Commands

- `sampler version`
- `sampler init`
- `sampler project list`
- `sampler index <project>`
- `sampler search <query> [--project <name>] [--type <t>] [--limit <n>]`
- `sampler search-all <query> [--type <t>] [--limit <n>]`
- `sampler symbols <project> [--type <t>] [--limit <n>]`
- `sampler overview <filepath>`

### Notes on `overview`
- Accepts relative paths (resolved from your current directory).
- If the file has no indexed symbols: prints a clear "No symbols found" message with usage tips.
