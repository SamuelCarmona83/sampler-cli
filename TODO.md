# Sampler TODO

## Estado

Versión actual: 0.1.2

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

## Restante (prioridad alta)

- Mejorar parser Python AST:
  - soportar AsyncFunctionDef
  - soportar decoradores/annotations completos
  - mejorar extracción de calls dinámicas
- Mejorar store/index para relaciones cross-file avanzadas.
- Mejorar QueryEngine:
  - filtros por tipo de símbolo
  - paginación
  - command `search-all`

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
