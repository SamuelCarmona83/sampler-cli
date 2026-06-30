# Sampler Handoff Report

Fecha: 2026-06-30
Versión: 0.1.2

## Resumen ejecutivo

- CLI funcional para flujo base Python.
- Se puede registrar proyecto, indexar, buscar símbolos y obtener overview por archivo.
- Indexación incremental activa (hash de archivo, skip si no cambió).
- Tests en verde.

## Estado implementado

### CLI

- `sampler version`
- `sampler init`
- `sampler project add <name> <path> --language <language>`
- `sampler project list`
- `sampler project remove <name>`
- `sampler index <project>`
- `sampler search <query> [--project <name>]`
- `sampler overview <filepath>`

### Config

Archivo global: `~/.sampler/config.yaml`

Modelos y manager en `src/sampler/config.py`.

### Base de datos

DB: `~/.sampler/graph.db`

Tablas:
- `projects`
- `files`
- `symbols`
- `relationships`
- `project_dependencies`

Core en `src/sampler/db.py`.

### Indexación

Pipeline:
1. Discover archivos por lenguaje en `src/sampler/indexer/discover.py`
2. Parse Python en `src/sampler/indexer/parsers/python.py`
3. Persistencia en `src/sampler/indexer/store.py`
4. Orquestación en `src/sampler/indexer/builder.py`

### Query

Motor en `src/sampler/query/engine.py`.

Soporta:
- búsqueda por nombre/qualified_name
- overview por filepath

## Decisión técnica crítica (estabilidad)

### Problema detectado

- `sampler index <project>` provocaba `BUS/SEGV` en macOS ARM.
- Trazas apuntaron a uso profundo de `tree-sitter-python` durante recorridos de nodos.

### Mitigación aplicada

- Parser Python pasó a AST puro (`ast` stdlib) para extracción de símbolos/relaciones.
- Se eliminó uso runtime de tree-sitter en parser Python.

### Impacto

- Se priorizó estabilidad sobre precisión avanzada de parser.
- Flujo de index/search quedó estable para uso diario.

## Tests

Ejecutar:

```bash
pytest -q
```

Estado actual: 7 tests pasando.

## Cómo validar manualmente

```bash
sampler init
sampler project add demo /ruta/proyecto --language python
sampler index demo
sampler search nombre --project demo
sampler overview /ruta/proyecto/file.py
```

## Backlog recomendado (siguiente agente)

1. `project update` command
- Evitar remove/add para corregir lenguaje/path.

2. Query avanzada
- `callers`, `usages`, `related` usando tabla `relationships`.

3. Parsers Fase 1
- Go parser real.
- TypeScript parser real.

4. Búsqueda
- Filtros por tipo y paginación.

5. Publicación
- Workflow release/tag para PyPI/TestPyPI.

## Riesgos abiertos

- Volver a tree-sitter Python puede reintroducir crash nativo.
- Si se reintenta, hacerlo detrás de feature flag y en subprocess aislado.

## Archivos clave modificados en esta sesión

- `src/sampler/__init__.py`
- `pyproject.toml`
- `src/sampler/config.py`
- `src/sampler/db.py`
- `src/sampler/indexer/discover.py`
- `src/sampler/indexer/parsers/python.py`
- `src/sampler/indexer/builder.py`
- `src/sampler/indexer/store.py`
- `src/sampler/query/engine.py`
- `src/sampler/cli/main.py`
- `README.md`
- `TODO.md`
- `tests/test_config.py`
- `tests/test_db.py`
- `tests/test_discover.py`
- `tests/test_cli.py`
- `tests/test_python_parser.py`
- `tests/test_index_query.py`
