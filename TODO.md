# Sampler TODO

## Estado

Versión actual: 0.2.0 (pre-release for demo)

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

## Release / Demo priorities (to launch on PyPI + showcase)

- [x] LICENSE + pyproject metadata polish, version 0.2.0, CHANGELOG
- [x] PyPI publish workflow (trusted publishers)
- [x] README demo/install instructions + token-efficient highlights
- [x] CI build check
- [ ] Test clean `pip install` + full demo flow (index real multi-file project, show compact search/ov/list)
- [ ] (low) Improve store cross-file name resolution for reliable relations in demo

## Restante (prioridad alta)

- Mejorar store/index para relaciones cross-file avanzadas. (name-based resolution in place; advanced scope/import tracking later)
- (done) Mejorar parser Python AST: AsyncFunctionDef, decorators/annotations in sig+meta, basic calls.
- (done) Mejorar QueryEngine: type filters (w/ async expand), limit/offset, search-all command.

## Restante (prioridad media)

- Parser Go real.
- Parser TypeScript/JavaScript real.
- Comandos callers, usages, related.
- Cross-project dependencies reales.
- Comando `project update` (evitar remove/add al cambiar lenguaje/path).

## Restante (Fase 2)

- Semantic search.
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
- Overview por archivo:
  - sampler overview /ruta/absoluta/al/archivo.py
- Flujo mínimo:
  - sampler init
  - sampler project add myproj /ruta/absoluta --language python
  - sampler index myproj
  - sampler search Nombre --project myproj
- Listar proyectos:
  - sampler project list
- Eliminar proyecto:
  - sampler project remove myproj
- Ejecutar tests:
  - pytest -q
