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
- verificar soporte index projectos multilenguaje o monolitos Parser Real GO/React/Vue/
- Parser Go real.
- Parser TypeScript/JavaScript real.
- Comandos callers, usages, related.
- Cross-project dependencies reales.
- Comando `project update` (evitar remove/add al cambiar lenguaje/path).

- Guardar para los simbolos funciones clases y bloques / start_line/end_line.
- tengo algunas idea para como desplegar la salida de la busqueda, quiero un modo 'bars' que subraye con colores las distintas relaciones de los simbolos, algo a como se muestran las rimas en el rap/hip-hop este proyecto es fuertemente inspirado en MF Doom.
- Tambien podemos usar flechas →  ascii para marcar las relaciones
- Semantic search y Hybrid Search (Prioridad)
- Generar un embedding por símbolo usando un modelo local (por ejemplo, uno de la familia bge o nomic-embed)
- No el código entero
def retry_request():
    ...
Documento
"""
Function:
retry_request

File:
network.py

Arguments:
url
retries

Docstring:
Retries failed HTTP requests using exponential backoff.
"""
Ese texto genera embeddings mucho mejores.

- Guardar esos embeddings junto al symbol_id
- Implementar una búsqueda por similitud coseno que devuelva el Top K de resultados.
- Enriquecer esos resultados con el grafo (CALLERS, USES, IMPORTS, CONTAINS).
- Añadir un sistema de ranking híbrido que combine similitud semántica, coincidencias de texto y señales del grafo.
- ranking score formula => 0.5 * semantic_similarity + 0.2 * exact_match + 0.2 * centrality + 0.1 * recently_modified
- Lo interesante es que puedes unir tres mundos en una sola herramienta
           Usuario
               │
        "¿Dónde se manejan los reintentos?"
               │
               ▼
      Búsqueda semántica
               │
     Encuentra `retry_request()`
               │
               ▼
        Grafo de relaciones
               │
    CALLERS · IMPORTS · CONTAINS
               │
               ▼
   Contexto completo del codebase

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
