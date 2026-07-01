# Sampler TODO

## Estado

Versión actual: 0.2.1

## Hecho

- Estructura base de proyecto creada.
- CLI base implementada con comandos iniciales.
- Config global implementada en ~/.sampler/config.yaml.
- CRUD de proyectos en config:
  - add_project
  - remove_project
  - get_project
  - list_projects
- Base de datos SQLite inicial implementada con schema core:
  - projects
  - files
  - symbols
  - relationships
  - project_dependencies
- Discovery de archivos implementado con:
  - filtros por lenguaje
  - ignores por defecto
  - soporte de .gitignore
- CI básica en GitHub Actions (pytest).
- Tests implementados y pasando:
  - smoke
  - config
  - db
  - discover
  - cli
  - python_parser
  - index_query
- Go instalado en entorno local (brew install go).
- Parser Python implementado con AST (estable).
- Indexer builder/store implementados y funcionales.
- Query engine implementado: search + overview.
- CLI conectada a flujo real:
  - sampler index <project>
  - sampler search <query> [--project]
  - sampler overview <filepath>
- Fix de crash en indexación (se removió uso runtime de tree-sitter en parser Python).
- Compact default output for search/overview + short paths in project list (min tokens for LLM use). Removed noisy module/import symbols.
- `symbols <project>` command (with --type/--limit) to list all symbols of a project.
- Improved `overview` with "No symbols found" message + tips, and smart relative path support (resolves from cwd + project roots).
- Better error messages with command examples and tips.
- Full English README with examples, "project add" explanation, etc.
- RELEASE.md with publishing guide.
- Added `symbols <project>` command (with filters/limit) to list all symbols of a project.
- Improved `overview`: clear "not found" message + tips, smart relative path support (resolves from cwd + tries project roots).
- Better error messages with actionable command suggestions and tips.
- README fully in English with examples, project add explanation, etc.
- Added RELEASE.md with publishing instructions.
- Full clean `pip install` + demo flow test passed (verified with 0.2.0/0.2.1 wheels).

## Release / Demo priorities (to launch on PyPI + showcase)

- [x] LICENSE + pyproject metadata polish, version 0.2.1, CHANGELOG
- [x] PyPI publish workflow (trusted publishers)
- [x] README demo/install instructions + token-efficient highlights (now fully English + examples)
- [x] CI build check
- [x] Test clean `pip install` + full demo flow (including new `symbols` command)
- [x] Added `symbols` command, improved `overview` UX (not found + relative paths), better errors
- [ ] (low) Improve store cross-file name resolution for reliable relations in demo

## Restante (prioridad alta)

- Mejorar store/index para relaciones cross-file avanzadas. (name-based resolution in place; advanced scope/import tracking later)
- (done) Mejorar parser Python AST: AsyncFunctionDef, decorators/annotations in sig+meta, basic calls.
- (done) Mejorar QueryEngine: type filters (w/ async expand), limit/offset, search-all command.
- (done in 0.2.1) `symbols <project>` command, better overview UX (not found + relative paths), improved errors, full English README + examples.

## Restante (prioridad media)
- (done) verificar soporte index projectos multilenguaje o monolitos: `project add --language auto` detecta el lenguaje por archivo (discover_files_multi + IndexBuilder).
- (done) Parser Go real (tree-sitter-go): structs/interfaces, funcs/methods (con receiver → CONTAINS), CALLS, docstrings via comentarios.
- (done) Parser TypeScript/JavaScript real (tree-sitter-typescript): functions, classes+methods, interfaces, const arrow-functions, CALLS/CONTAINS.
- (done) Comandos `callers`, `usages`, `related` (con resolución de símbolo ambigua y `--style bars`).
- (done) Cross-project dependencies reales: extracción heurística de imports (regex) + tabla `project_dependencies` poblada en `sampler index`; comando `project deps <name>`.
- (done) Comando `project update` (evita remove/add al cambiar lenguaje/path).

- (done) start_line/end_line ya se guardaban en symbols; ahora también se exponen en `overview`/`symbols` output.
- (done) Modo `bars` (`--style bars` en `search`/`overview`/`related`): colorea grupos de símbolos conectados (CONTAINS/CALLS) y anota relaciones con flechas ascii (→ ⊃ ⇒), estilo rima coloreada.
- (done) Semantic search y Hybrid Search:
  - Texto estructurado por símbolo (`indexer/embedder.py::build_embedding_text`, formato Function/File/Arguments/Docstring).
  - Embeddings locales vía `sentence-transformers` (extra opcional `semantic`), comando `sampler embed <project>`.
  - Búsqueda por similitud coseno (`query/semantic.py::SemanticEngine.semantic_search`, numpy brute-force sobre BLOBs en SQLite).
  - Ranking híbrido implementado: `0.5*semantic_similarity + 0.2*exact_match + 0.2*centrality + 0.1*recently_modified`, expuesto via `sampler search --semantic`.
  - Pendiente futuro: enriquecer con IMPORTS/USES reales en el ranking de centralidad (hoy solo CALLS in-degree).

## Restante (Fase 2)
- Re-index project on demand / have a last_reindex_date or something to make the agent or user aware (or plan a reindex worker that executes on background)
- Context generation para agentes IA.
- MCP server.
- Reportes de análisis.

## Comandos útiles ahora

- Instalar deps dev:
  - /opt/homebrew/bin/python3.11 -m pip install -e '.[dev]'
- Ver versión:
  - sampler version
- Inicializar config:
  - sampler init
- Agregar proyecto:
  - sampler project add myproj /ruta/absoluta --language python
- Indexar proyecto:
  - sampler index myproj
- Buscar símbolo:
  - sampler search add --project myproj
- Listar símbolos de un proyecto:
  - sampler symbols myproj
  - sampler symbols myproj --type function --limit 20
- Overview por archivo:
  - sampler overview /ruta/absoluta/al/archivo.py
- Flujo mínimo:
  - sampler init
  - sampler project add myproj /ruta/absoluta --language python
  - sampler index myproj
  - sampler search Nombre --project myproj
  - sampler symbols myproj
- Listar proyectos:
  - sampler project list
- Eliminar proyecto:
  - sampler project remove myproj
- Ejecutar tests:
  - pytest -q
