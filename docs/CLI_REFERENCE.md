# CLI Reference

## Commands

- `sampler version`
- `sampler init`
- `sampler project list`
- `sampler index <project>`
- `sampler search <query> [--project <name>] [--format compact|table|json]`
- `sampler overview <filepath> [--format compact|table|json]`

## Output Formats (for search/overview)

- `compact` (default): One line per symbol, relative/short paths, no table borders. Token-efficient for LLM/agent use and copy-paste.
  Example:
  ```
  demo:src/app.py:42 function get_user  def get_user(user_id)
  Found 1 result(s)
  ```

- `table`: Rich table (pretty, conditional columns when --project used). Good for humans.
- `json`: Minified JSON array of lean objects (project, file, type, name, line, signature). Ideal for scripts + LLMs.

Tip: Use default compact or --format json when piping output to LLMs or MCP tools to reduce tokens read.
