# Sampler Skill for Pi Coding Agent

**Name**: sampler  
**Description**: Provides deep codebase understanding through structural graph queries and semantic search. Use this skill when you need to explore how code connects, find callers/usages, understand architecture, or perform intelligent searches beyond simple grep.  
**Version**: 1.0  
**Author**: Samuel Carmona  
**Requires**: `sampler-cli` installed and projects indexed.

## Overview

`sampler` builds a knowledge graph of your codebase (symbols, relationships, embeddings).  
It enables powerful queries that reduce hallucinations and token usage when working with large projects.

**Key capabilities**:
- Index projects (multi-language: Python, Go, TypeScript/JavaScript, etc.)
- Structural queries: callers, usages, related symbols
- Semantic search (with embeddings)
- Project management and stale code detection
- Configurable embeddings providers (local-first friendly)

## When to Use Sampler

Use `sampler` commands (via the `bash` tool) in these situations:

- Understanding architecture or data flow ("how is authentication handled?")
- Finding impact of changes ("what calls this function?")
- Exploring unfamiliar code ("show me all usages of UserService")
- Semantic discovery ("find code related to retry logic or error handling")
- Refactoring or dead code cleanup
- Preparing context for complex edits

**Do not use** for simple file reads (use native `read` tool instead).

## Core Commands & Best Practices

### 1. Project Management
```bash
# List configured projects
sampler project list

# Add a new project (auto-detects language when possible)
sampler project add myapp /path/to/project --language auto

# Update or re-index
sampler project update myapp --path /new/path
sampler index myapp
```

**Tip**: Always ensure the project is indexed before querying.

### 2. Exploration Commands

#### Search
```bash
# Basic name search
sampler search "UserService" --project myapp

# Semantic search (recommended for meaning-based queries)
sampler search "retry logic or exponential backoff" --semantic --project myapp --limit 15

# Search across all projects
sampler search-all "payment processing"
```

**When to use `--semantic`**:
- Vague or conceptual queries
- Finding similar concepts across different naming conventions

#### Structural Queries (Most Powerful)
```bash
# Who calls this symbol?
sampler callers "processPayment" --project myapp --file src/services/payment.ts

# Where is it used?
sampler usages "User" --project myapp

# Related symbols (graph neighbors)
sampler related "AuthService" --project myapp --style bars
```

**Disambiguation tip**: If a symbol name is ambiguous, use `--file <path-or-suffix>` or the selector syntax:
```bash
sampler callers "src/services/payment.ts:processPayment"
```

### 3. Code Understanding
```bash
# Overview of a file (symbols + structure)
sampler overview src/components/UserProfile.tsx --style bars

# Find potentially stale code (defined in tests but no real callers)
sampler stale-code myapp --limit 20
```

### 4. Embeddings & Semantic Search Setup
```bash
# Configure embeddings (default is bge-small via fastembed - local & fast)
sampler config embeddings --provider bge-small

# Or use Ollama for local models
sampler config embeddings --provider ollama --model nomic-embed-text --base-url http://localhost:11434

# Generate embeddings (run after indexing or changing provider)
sampler embed myapp
```

**Note**: After changing provider, always re-run `sampler embed <project>`.

### 5. Other Useful Commands
- `sampler symbols <project> --type function --limit 50`
- `sampler project deps <name>` (shows dependencies if parsed)
- `sampler config show`
- `sampler version --plain` (for scripts)

## Recommended Workflow with Pi

1. **Index the project** (if not already done):
   ```bash
   sampler project add current . --language auto
   sampler index current
   sampler embed current   # if using semantic search
   ```

2. **Explore structurally** first:
   - Use `callers`, `usages`, `related` to build mental model.

3. **Use semantic search** for conceptual questions.

4. **Combine with native tools**:
   - Use `sampler` to find relevant symbols/files.
   - Then use `read` on the most important ones.

5. **For refactoring**:
   - `sampler callers` + `sampler usages` to understand impact.
   - `sampler related` to find similar patterns.

## Example Prompts / Usage Patterns

**Good prompt**:
> "Use sampler to find all places where authentication is checked. Start with semantic search for 'auth' or 'authentication', then use callers and usages on the main functions."

**Another good one**:
> "Before editing the payment flow, use sampler callers on the main payment functions to understand the call graph."

**Avoid**:
- Asking sampler to read full file content (use native read instead).
- Over-relying on it for very simple lookups.

## Configuration Tips

- Run `sampler config embeddings` to switch between local (bge-small, ollama) and cloud providers.
- Environment variables for API keys (OpenAI, etc.).
- Projects are stored in `~/.config/sampler-cli/` or similar.

## Limitations & Fallbacks

- Semantic search requires running `sampler embed` first.
- Falls back gracefully: provider vectors → TF-IDF → simple hash.
- For very large projects, use `--limit` and specific `--project`.
- Ambiguous symbols → always provide `--file` or use selector syntax.

## Installation (for the user)

Make sure `sampler-cli` is installed:

```bash
pip install sampler-cli
# For embeddings support:
pip install 'sampler-cli[embeddings]'
# or ollama variant if preferred
```

Then configure your projects as shown above.

---

**This skill should be placed in** `~/.pi/agent/skills/sampler/SKILL.md` (or loaded via Pi's skill system).

Pi will automatically pick up the instructions when the skill is active.

You can enhance this skill later by adding more prompt templates or even a small TypeScript extension that registers custom high-level tools (e.g., `smart_code_search`).