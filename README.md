# Sampler

CLI indexer para navegar símbolos y relaciones en codebases multiproyecto.

Versión actual: 0.1.2

## Requisitos

- Python 3.11+
- `uv` (recomendado)
- Go (instalado para soporte parser Fase 1)

## Instalación de Go (macOS)

```bash
brew install go
go version
```

## Instalación (dev)

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

Alternativa con pip:

```bash
/opt/homebrew/bin/python3.11 -m pip install -e '.[dev]'
```

## Uso rápido

```bash
sampler --help
sampler version
sampler init
sampler project add myproj /absolute/path --language python
sampler project list
sampler index myproj
sampler search add --project myproj
sampler search add --project myproj --format table
sampler search add --project myproj --format json
sampler overview /absolute/path/file.py
sampler project remove myproj
```

## Estado actual

Implementado:

- Bootstrap inicial de Fase 0
- Configuración global con archivo `~/.sampler/config.yaml`
- CRUD de proyectos en config (`add`, `list`, `remove`)
- Esquema SQLite core + queries de index/search en `src/sampler/db.py`
- Discovery de archivos por lenguaje con soporte `.gitignore`
- Parser Python estable basado en AST
- Indexer real (hash incremental + persistencia)
- Query engine real (`search`, `overview`)
- CI básico con GitHub Actions (`pytest -q`)
- Tests: smoke, config, db, cli, discovery, python_parser, index_query

Nota de estabilidad:

- Se desactivó uso runtime de tree-sitter en parser Python por crash nativo (`BUS/SEGV`) en indexación real.
- Se mantiene estrategia AST para estabilidad en producción local.

Pendiente inmediato:

- Filtros y paginación en búsqueda (type filters started via clean defaults + --format)
- Comandos `callers`, `usages`, `related`
- Parsers Go y TypeScript/JavaScript

Nota de tokens/LLM:
- search y overview usan por defecto formato `compact` (caminos relativos/cortos, sin borders, sin símbolos ruidosos module/import).
- Usa `--format json` o default para mínimo consumo de tokens cuando el output se pasa a LLMs o agentes.
- Re-ejecuta `sampler index <proj>` en proyectos existentes para limpiar símbolos históricos ruidosos del índice.

## Estructura clave

```text
src/sampler/cli/main.py          # comandos CLI
src/sampler/config.py            # config global YAML
src/sampler/db.py                # capa SQLite
src/sampler/indexer/builder.py   # indexación de proyectos
src/sampler/indexer/store.py     # persistencia de símbolos/relaciones
src/sampler/indexer/parsers/python.py # parser python estable
src/sampler/query/engine.py      # search/overview
src/sampler/indexer/discover.py  # discovery y filtros
tests/                           # pruebas base
```

## Ejecutar pruebas

```bash
pytest -q
```
