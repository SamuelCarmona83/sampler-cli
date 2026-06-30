# 📋 Sampler Roadmap Detallado

> **Proyecto**: Sampler - CLI indexador de código multiproyecto
> **Propósito**: Hub central para navegar integraciones y dependencias entre proyectos
> **Stack**: Python 3.11+ (uv), SQLite, Typer, Rich, Tree-sitter
> **Objetivo Final Fase 2**: Tool productiva para agilizar desarrollo en entornos con múltiples proyectos integrados

---

## 📊 Estructura de Fases

| Fase | Duración | Foco | Entregables |
|------|----------|------|-------------|
| **0** | 1-2 semanas | MVP core + project registry | CLI base + search local/cross-project |
| **1** | 2-3 semanas | Integraciones y análisis | Endpoints, connections, reports |
| **2** | 3-4 semanas | Análisis avanzado + Pi integration | Impact analysis, context generation, semantic search |

---

---

# 🎯 FASE 0: MVP & Core Infrastructure

**Objetivo**: Tener un CLI funcional que pueda indexar múltiples proyectos y hacer búsquedas básicas.

**Definición de "Done"**: 
- ✅ Puedo agregar 4+ proyectos a `sampler`
- ✅ Indexar cada proyecto en ~30 segundos (codebase pequeño)
- ✅ Buscar dentro de un proyecto
- ✅ Buscar en TODOS los proyectos
- ✅ Ver listado de proyectos con stats

---

## Tarea 0.1: Setup Inicial del Proyecto

**Descripción**: Scaffolding, estructura de carpetas, dependencias, CI básico

**Subtareas**:
- [ ] Crear repo en GitHub: `sampler`
- [ ] Setup `pyproject.toml` con uv
  - Python 3.11+
  - Dependencies: `typer[all]`, `rich`, `sqlalchemy`, `tree-sitter`, `pydantic`
  - Dev deps: `pytest`, `pytest-cov`, `ruff`, `mypy`
- [ ] Crear estructura de carpetas:
  ```
  sampler/
  ├── pyproject.toml
  ├── README.md
  ├── LICENSE
  ├── .gitignore
  ├── uv.lock
  ├── src/sampler/
  │   ├── __init__.py
  │   ├── __main__.py
  │   ├── config.py
  │   ├── models.py
  │   ├── db.py
  │   ├── indexer/
  │   │   ├── __init__.py
  │   │   ├── discover.py
  │   │   ├── parsers/
  │   │   │   ├── __init__.py
  │   │   │   ├── base.py
  │   │   │   ├── python.py
  │   │   │   ├── go.py
  │   │   │   └── typescript.py
  │   │   ├── builder.py
  │   │   └── store.py
  │   ├── query/
  │   │   ├── __init__.py
  │   │   ├── engine.py
  │   │   └── semantic.py
  │   ├── cli/
  │   │   ├── __init__.py
  │   │   ├── main.py
  │   │   ├── commands/
  │   │   │   ├── project.py
  │   │   │   ├── search.py
  │   │   │   └── utils.py
  │   └── mcp/
  │       ├── __init__.py
  │       └── server.py (stub)
  ├── tests/
  │   ├── conftest.py
  │   ├── test_config.py
  │   ├── test_db.py
  │   ├── test_indexer.py
  │   └── test_query.py
  └── docs/
      ├── ARCHITECTURE.md
      └── CLI_REFERENCE.md
  ```
- [ ] README con descripción + quick start
- [ ] `.gitignore` (Python + IDE)
- [ ] GitHub Actions workflow para tests (básico)

**Estimación**: 3-4 horas
**Bloqueante**: No
**Notas**: 
- Usar `uv` para gestionar dependencias (es lo más rápido)
- No instalar tree-sitter bindings aún, solo documentar

---

## Tarea 0.2: Config System Global

**Descripción**: Sistema de configuración para gestionar el registry de proyectos

**Subtareas**:
- [ ] Crear `config.py`:
  - Clase `Config` que maneja `~/.sampler/config.yaml`
  - Métodos: `load()`, `save()`, `add_project()`, `remove_project()`, `get_project()`
  - Validación con Pydantic
  - Manejo de paths (expandir `~`, crear dirs si no existen)
  
- [ ] Crear schema de `config.yaml`:
  ```yaml
  version: 1
  cache_dir: ~/.sampler
  projects:
    backend-go:
      path: /absolute/path/to/backend-go
      language: go
      type: service
      enabled: true
  ```
  
- [ ] Modelos Pydantic:
  ```python
  class ProjectConfig(BaseModel):
      name: str
      path: Path
      language: str  # go, python, typescript, etc.
      type: str      # service, connector, reporting
      enabled: bool = True
  
  class GlobalConfig(BaseModel):
      version: int
      cache_dir: Path
      projects: dict[str, ProjectConfig]
  ```

- [ ] Tests unitarios:
  - Crear config nuevo
  - Agregar/remover proyectos
  - Validar paths inválidos
  - Migración de config versiones

**Estimación**: 4-5 horas
**Bloqueante**: Para 0.3
**Notas**:
- Config global en `~/.sampler/config.yaml` (standard Unix)
- Cada proyecto puede tener también `.sampler.yaml` local (para Fase 1)
- Error handling claro (proyecto no existe, path inválido, etc.)

---

## Tarea 0.3: Database Schema & Layer

**Descripción**: Setup de SQLite, schema, y layer de abstracción

**Subtareas**:
- [ ] Crear `db.py`:
  - Clase `Database` con SQLAlchemy
  - Métodos para inicializar schema
  - Context manager para conexiones
  
- [ ] Schema global (`~/.sampler/graph.db`):
  ```sql
  CREATE TABLE projects (
      id INTEGER PRIMARY KEY,
      name TEXT UNIQUE NOT NULL,
      indexed_at TIMESTAMP,
      symbol_count INTEGER DEFAULT 0,
      file_count INTEGER DEFAULT 0
  );
  
  CREATE TABLE project_dependencies (
      id INTEGER PRIMARY KEY,
      source_project_id INTEGER NOT NULL,
      target_project_id INTEGER NOT NULL,
      type TEXT,  -- imports, api_calls, data_flow
      metadata TEXT,  -- JSON
      FOREIGN KEY(source_project_id) REFERENCES projects(id),
      FOREIGN KEY(target_project_id) REFERENCES projects(id),
      UNIQUE(source_project_id, target_project_id, type)
  );
  ```

- [ ] Schema per-project (`~/.sampler/projects/{name}/index.db`):
  ```sql
  CREATE TABLE files (
      id INTEGER PRIMARY KEY,
      path TEXT UNIQUE NOT NULL,
      language TEXT NOT NULL,
      hash TEXT,
      indexed_at TIMESTAMP
  );
  
  CREATE TABLE symbols (
      id INTEGER PRIMARY KEY,
      file_id INTEGER NOT NULL,
      type TEXT NOT NULL,  -- function, class, component, etc.
      name TEXT NOT NULL,
      qualified_name TEXT,
      signature TEXT,
      docstring TEXT,
      start_line INTEGER,
      end_line INTEGER,
      metadata TEXT,  -- JSON
      FOREIGN KEY(file_id) REFERENCES files(id)
  );
  
  CREATE TABLE relationships (
      id INTEGER PRIMARY KEY,
      source_id INTEGER NOT NULL,
      target_id INTEGER NOT NULL,
      type TEXT NOT NULL,  -- CALLS, IMPORTS, RENDERS, USES
      metadata TEXT,  -- JSON
      FOREIGN KEY(source_id) REFERENCES symbols(id),
      FOREIGN KEY(target_id) REFERENCES symbols(id)
  );
  
  CREATE INDEX idx_symbols_name ON symbols(name);
  CREATE INDEX idx_symbols_qualified ON symbols(qualified_name);
  CREATE INDEX idx_rel_source ON relationships(source_id);
  CREATE INDEX idx_rel_target ON relationships(target_id);
  ```

- [ ] Migraciones simple (crear tablas en init)
- [ ] Tests:
  - Crear DB
  - Insertar/consultar símbolos
  - Validar índices

**Estimación**: 5-6 horas
**Bloqueante**: Para 0.4, 0.5, 0.6
**Notas**:
- Usar SQLAlchemy ORM para modelos
- Path de DB: `~/.sampler/projects/{project_name}/index.db`
- Manejo transaccional (rollback en errores)

---

## Tarea 0.4: Parsers Base (Python, Go, TypeScript)

**Descripción**: Extractores de símbolos usando tree-sitter

**Subtareas**:
- [ ] Crear `indexer/parsers/base.py`:
  ```python
  class BaseParser(ABC):
      language: str
      
      @abstractmethod
      def parse(self, content: str, filepath: str) -> list[Symbol]: pass
  ```

- [ ] Crear `indexer/parsers/python.py`:
  - Detectar: funciones, clases, métodos, imports
  - Extraer: nombre, linea inicio/fin, docstring, decoradores
  - Relaciones: calls a funciones, imports
  - Tree-sitter para Python

- [ ] Crear `indexer/parsers/go.py`:
  - Detectar: funciones, structs, interfaces, métodos, packages
  - Extraer: nombre, líneas, comment
  - Relaciones: imports, method receivers
  - Tree-sitter para Go

- [ ] Crear `indexer/parsers/typescript.py`:
  - Detectar: funciones, clases, interfaces, componentes React (heurística)
  - Extraer: nombre, líneas, JSDoc
  - Relaciones: imports, exports, component calls
  - Tree-sitter para TypeScript

- [ ] Tests para cada parser:
  ```python
  def test_python_parser_extracts_functions():
      code = """
      def hello(name: str) -> str:
          '''Greet someone.'''
          return f"Hello {name}"
      """
      symbols = PythonParser().parse(code, "test.py")
      assert len(symbols) == 1
      assert symbols[0].name == "hello"
      assert symbols[0].type == "function"
  ```

**Estimación**: 8-10 horas
**Bloqueante**: Para 0.5
**Notas**:
- Instalar tree-sitter languages: `tree-sitter-python`, `tree-sitter-go`, `tree-sitter-typescript`
- Parsers simples pero robustos (no need perfection en Fase 0)
- Agregar metadata a los símbolos (decorators, visibility, etc.)
- Manejar errores de parsing gracefully (log + skip)

---

## Tarea 0.5: Indexer & Store

**Descripción**: Lógica para descubrir archivos, parsear y guardar en DB

**Subtareas**:
- [ ] Crear `indexer/discover.py`:
  - Función `discover_files(project_path, language)` que devuelve archivos válidos
  - Ignorar: `.git`, `node_modules`, `venv`, etc. (ver `.gitignore`)
  - Filtrar por extensión según language
  - Devolver lista de paths

- [ ] Crear `indexer/builder.py`:
  ```python
  class IndexBuilder:
      def index_project(self, project_name: str, force: bool = False):
          # 1. Cargar config del proyecto
          # 2. Descubrir archivos
          # 3. Parsear cada archivo
          # 4. Guardar en DB
          # 5. Retornar stats (files, symbols, time)
  ```

- [ ] Crear `indexer/store.py`:
  ```python
  class SymbolStore:
      def save_symbols(self, project_id: int, filepath: str, symbols: list[Symbol]):
          # Insertar files + symbols + relationships en DB
          
      def save_relationships(self, project_id: int, relationships: list[Relationship]):
          # Insertar relationships entre símbolos
  ```

- [ ] Detectar cambios (hash de archivo):
  - Solo re-indexar si cambió
  - Opción `--force` para force re-index

- [ ] Tests:
  - Indexar proyecto ejemplo (pequeño)
  - Verificar símbolos guardados
  - Performance (indexar 100+ archivos)

**Estimación**: 7-8 horas
**Bloqueante**: Para 0.6, 0.7
**Notas**:
- Parsear en paralelo (ThreadPoolExecutor) para speed
- Mostrar progress bar con Rich
- Manejo robusto de errores (1 archivo bad no rompe todo)

---

## Tarea 0.6: Query Engine (Local)

**Descripción**: Motor de búsqueda dentro de un proyecto

**Subtareas**:
- [ ] Crear `query/engine.py`:
  ```python
  class QueryEngine:
      def search(self, project_name: str, query: str) -> list[Symbol]:
          # Búsqueda por nombre (LIKE, case-insensitive)
          
      def usages(self, project_name: str, symbol_name: str) -> list[Relationship]:
          # Dónde se usa X en este proyecto
          
      def callers(self, project_name: str, symbol_name: str) -> list[Symbol]:
          # Qué llama a X
  ```

- [ ] Tests:
  - Buscar función existente
  - Buscar componente React
  - Encontrar usages
  - Manejo de símbolos no encontrados

**Estimación**: 5-6 horas
**Bloqueante**: Para 0.7
**Notas**:
- Búsqueda simple por nombre (LIKE) en Fase 0
- Performance: índices en DB (ya están listos)

---

## Tarea 0.7: CLI - Project Commands

**Descripción**: Comandos para gestionar proyectos

**Subtareas**:
- [ ] Crear `cli/commands/project.py`:
  ```bash
  sampler project add <name> <path> --language <lang> --type <type>
  sampler project list [--detailed]
  sampler project show <name>
  sampler project remove <name>
  sampler project index <name> [--force]
  sampler project index-all [--force]
  ```

- [ ] Implementar en Typer:
  - `project_app = Typer()`
  - Subcomandos con help text
  - Validación de inputs
  - Pretty output con Rich (tables, colors)

- [ ] Output examples:
  ```
  $ sampler project list --detailed
  
  📦 Projects (4 total)
  
  ┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
  ┃ Name             ┃ Language ┃ Type     ┃ Status ┃
  ┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
  │ backend-go       │ go       │ service  │ ✅ 248s ago │
  │ frontend-react   │ ts       │ service  │ ✅ 3h ago   │
  │ integration-layer│ go       │ connector│ ⚠️  stale   │
  │ dashboards-pbi   │ dax      │ reporting│ ❌ never   │
  └──────────────────┴──────────┴──────────┴────────┘
  ```

- [ ] Tests:
  - Agregar proyecto
  - Listar proyectos
  - Index proyecto (mock DB)

**Estimación**: 6-7 horas
**Bloqueante**: Para 0.8, 0.9
**Notas**:
- Typer para CLI (muy clean + autocomplete)
- Rich para output (tablas, colores, spinners)
- Validación: path exists, language supported, nombre único

---

## Tarea 0.8: CLI - Search Commands (Local)

**Descripción**: Comandos de búsqueda dentro de un proyecto

**Subtareas**:
- [ ] Crear `cli/commands/search.py`:
  ```bash
  sampler search <query> --project <name>
  sampler usages <symbol> --project <name>
  sampler callers <symbol> --project <name>
  ```

- [ ] Output con Rich:
  ```
  $ sampler search "GetUser" --project backend-go
  
  🔍 Results for "GetUser" in backend-go
  
  📄 handlers/user.go:42-65
    ├─ GetUser (function)
    ├─ Called by: GetUserRoute (1x), tests/user_test.go (3x)
    └─ Calls: ValidateToken, FetchUserDB
  
  📄 models/user.go:10-25
    ├─ GetUserDTO (type)
    └─ Used by: handlers/user.go, serializers.go
  
  Found 2 results in 125ms
  ```

- [ ] Tests:
  - Search existing symbol
  - No results
  - Multiple results
  - Case-insensitive

**Estimación**: 5-6 horas
**Bloqueante**: Para 0.9
**Notas**:
- Output legible y navegable (no abrumar)

---

## Tarea 0.9: CLI - Cross-Project Search

**Descripción**: Búsqueda en TODOS los proyectos a la vez

**Subtareas**:
- [ ] Implementar en `query/engine.py`:
  ```python
  def search_all(self, query: str) -> dict[str, list[Symbol]]:
      # Buscar en todos los proyectos
      # Retornar dict: {project_name: [symbols]}
  ```

- [ ] Comando CLI:
  ```bash
  sampler search-all <query>
  ```

- [ ] Output:
  ```
  $ sampler search-all "UserDTO"
  
  🔍 Search "UserDTO" across all projects
  
  backend-go (2 matches)
    ├─ UserDTO (type) at models/dto.go:15
    └─ UserDTOBuilder (function) at builders.go:42
  
  frontend-react (1 match)
    └─ UserDTOAdapter (interface) at types/user.ts:8
  
  integration-layer (0 matches)
  
  Total: 3 results in 89ms
  ```

- [ ] Tests:
  - Search con múltiples proyectos
  - Proyectos sin matches

**Estimación**: 4-5 horas
**Bloqueante**: Ninguno importante
**Notas**:
- Ejecutar búsquedas en paralelo (ThreadPoolExecutor)
- Agrupar por proyecto en output

---

## Tarea 0.10: Documentation & Polish

**Descripción**: Docs, error handling, edge cases

**Subtareas**:
- [ ] Crear `docs/ARCHITECTURE.md`:
  - Overview de componentes
  - Diagrama de flujo indexing
  - Schema DB visual
  
- [ ] Crear `docs/CLI_REFERENCE.md`:
  - Todos los comandos de Fase 0
  - Ejemplos
  - Troubleshooting

- [ ] Update `README.md`:
  - Quick start
  - Installation
  - Examples
  - Roadmap

- [ ] Error handling robusto:
  - Project not found
  - Path invalid
  - Database corrupted
  - Parser errors
  - Network errors (future)

- [ ] Polish:
  - Mensajes de error claros
  - Help text en cada comando (`--help`)
  - Autocomplete setup (Typer lo maneja)
  - Version command (`sampler --version`)

**Estimación**: 4-5 horas
**Bloqueante**: No
**Notas**:
- Docs claras para que otros (y Pi) entiendan cómo usarlo

---

## Tarea 0.11: Testing & QA

**Descripción**: Tests exhaustivos, coverage, integration tests

**Subtareas**:
- [ ] Unit tests:
  - Config: load, save, validate
  - DB: schema, CRUD
  - Parsers: Python, Go, TS
  - Query engine: search, usages, callers
  - Cada test debe estar en `tests/test_*.py`

- [ ] Integration tests:
  - Setup proyecto pequeño
  - Index proyecto
  - Search
  - Verificar resultados

- [ ] Coverage:
  - Target: 80%+
  - Runnable: `pytest --cov=sampler`

- [ ] Manual testing:
  - Indexar 3-4 proyectos reales (pequeños)
  - Búsquedas típicas
  - Edge cases

**Estimación**: 6-8 horas
**Bloqueante**: Antes de release
**Notas**:
- Usar `pytest` + `pytest-cov`
- Fixtures para test data (proyecto ejemplo)

---

## 🎯 Checklist Fase 0

- [ ] 0.1: Setup + scaffolding
- [ ] 0.2: Config system
- [ ] 0.3: Database
- [ ] 0.4: Parsers (Python, Go, TS)
- [ ] 0.5: Indexer
- [ ] 0.6: Query engine (local)
- [ ] 0.7: CLI project commands
- [ ] 0.8: CLI search commands
- [ ] 0.9: Cross-project search
- [ ] 0.10: Documentation
- [ ] 0.11: Testing & QA

**Total Estimado**: 53-63 horas de trabajo

---

---

# 🎵 FASE 1: Integrations & Analysis

**Objetivo**: Entender cómo se conectan los proyectos y generar reportes útiles.

**Prerequisitos**: Fase 0 completada

**Definición de "Done"**:
- ✅ Puedo ver qué endpoints expone un servicio
- ✅ Puedo ver qué conecta A con B
- ✅ Puedo generar un mapa de integraciones
- ✅ Puedo listar símbolos "huérfanos" (no usados)
- ✅ Generar report de dependencias (Mermaid/ASCII)

---

## Tarea 1.1: Project Metadata & Exports

**Descripción**: Configuración local de cada proyecto (`.sampler.yaml`) y declaración de "exports"

**Subtareas**:
- [ ] Crear `.sampler.yaml` schema (per-project):
  ```yaml
  name: backend-go
  type: service
  
  exports:
    endpoints:
      - path: /api/v1/users
        methods: [GET, POST, PUT, DELETE]
        handler: handlers.GetUser
        auth: required
      - path: /api/v1/products
        methods: [GET]
        handler: handlers.ListProducts
    
    models:
      - User
      - Product
      - Order
    
    services:
      - UserService
      - ProductService
  
  imports_from:
    - dashboards-powerbi:
      - UserDTO
      - ProductDTO
  ```

- [ ] Parser de `.sampler.yaml`:
  ```python
  class ProjectMetadata:
      name: str
      type: str  # service, connector, reporting, library
      exports: ExportConfig
      imports_from: dict[str, list[str]]
  ```

- [ ] Integrar en indexer:
  - Leer `.sampler.yaml` al indexar
  - Validar que exports existen en el código
  - Guardar en metadata de símbolos

- [ ] CLI para generar template:
  ```bash
  sampler project init <name> --type service
  # Crea .sampler.yaml template
  ```

**Estimación**: 5-6 horas
**Bloqueante**: Para 1.2, 1.3
**Notas**:
- `.sampler.yaml` es optional (graceful fallback)
- Si no existe, inference heurística (endpoints que empiezan con `/api`, etc.)

---

## Tarea 1.2: Endpoint Extraction (Go + React)

**Descripción**: Extraer endpoints REST/GraphQL del código

**Subtareas**:
- [ ] Parser Go (`indexer/parsers/go.py` mejorado):
  - Detectar routes Gin: `router.GET("/path", handler)`
  - Extraer: método, path, handler, middleware
  - Relacionar con handler function
  ```go
  // Detectar esto:
  router.POST("/api/v1/users", auth.Required, handlers.CreateUser)
  ```

- [ ] Parser TypeScript (React):
  - Detectar rutas Next.js/React Router
  - Endpoints en `/api/route.ts` (Next.js)
  - `export async function POST(req) { ... }`
  - Componentes React que son "páginas"

- [ ] Guardar en DB:
  ```sql
  ALTER TABLE symbols ADD COLUMN is_endpoint BOOLEAN;
  ALTER TABLE symbols ADD COLUMN endpoint_metadata JSON;
  -- endpoint_metadata: {method, path, auth, response_type, ...}
  ```

- [ ] Tests:
  - Extraer endpoints de código Go real
  - Extraer rutas de Next.js
  - Validar paths, métodos

**Estimación**: 7-8 horas
**Bloqueante**: Para 1.3
**Notas**:
- Buscar patrones específicos (Gin, Express, Next.js)
- Heurísticas para detectar handlers

---

## Tarea 1.3: Cross-Project Relationships

**Descripción**: Detectar cómo se conectan proyectos (imports, API calls, etc.)

**Subtareas**:
- [ ] Analizar imports entre proyectos:
  ```go
  // backend-go/handlers/user.go
  import "github.com/vates/shared-models"  // <- integration-layer
  ```
  
  Detectar que `backend-go` imports de `integration-layer`

- [ ] Analizar API calls en código:
  ```typescript
  // frontend-react
  const response = await fetch('/api/v1/users');  // Calls backend-go
  ```

- [ ] HTTP client calls:
  ```go
  // dashboards-powerbi client
  resp, _ := http.Get("http://backend:8080/api/v1/products")
  ```

- [ ] Crear grafo en `graph.db`:
  ```python
  class RelationshipDetector:
      def detect_cross_project_relationships(self):
          # 1. Escanear imports en cada proyecto
          # 2. Matchear con otros proyectos
          # 3. Guardar en project_dependencies
  ```

- [ ] Store en DB (`~/.sampler/graph.db`):
  ```sql
  INSERT INTO project_dependencies 
  (source_project_id, target_project_id, type, metadata)
  VALUES (2, 1, 'imports', '{"module": "github.com/vates/shared-models"}')
  ```

- [ ] Tests:
  - Detectar imports entre proyectos
  - Detectar API calls
  - Grafo correctamente poblado

**Estimación**: 8-10 horas
**Bloqueante**: Para 1.4, 1.5
**Notas**:
- Heurísticas de detección (path patterns, host patterns)
- Posibles false positives (OK en Fase 1, mejorar después)

---

## Tarea 1.4: CLI - Endpoints & Connections

**Descripción**: Comandos para visualizar endpoints e integraciones

**Subtareas**:
- [ ] Comandos:
  ```bash
  sampler endpoints <project>
  sampler endpoints <project> --filter "GET /api/users"
  sampler connections <project1> <project2>
  sampler connections --from <project>
  sampler integrations <project>
  ```

- [ ] Output `endpoints`:
  ```
  $ sampler endpoints backend-go
  
  🔌 Endpoints in backend-go
  
  GET /api/v1/users
    ├─ Handler: handlers.ListUsers
    ├─ Auth: required
    └─ Used by: frontend-react (3 calls), dashboards-pbi (2 calls)
  
  POST /api/v1/users
    ├─ Handler: handlers.CreateUser
    ├─ Auth: required
    └─ Used by: frontend-react
  
  Total: 24 endpoints
  ```

- [ ] Output `connections`:
  ```
  $ sampler connections backend-go dashboards-powerbi
  
  📊 Connection: backend-go → dashboards-powerbi
  
  Type: API Calls (2)
    ├─ GET /api/v1/products (8 queries)
    └─ GET /api/v1/analytics (dashboard sync)
  
  Type: Shared Models (3)
    ├─ ProductDTO
    ├─ AnalyticsDTO
    └─ MetadataDTO
  ```

- [ ] Output `integrations`:
  ```
  $ sampler integrations backend-go
  
  🔗 Integration Map for backend-go
  
  backend-go connects to:
    ├─ frontend-react (API calls, shared types)
    ├─ dashboards-powerbi (data export)
    └─ external-api (webhooks)
  
  backend-go imports from:
    └─ integration-layer (shared-models)
  ```

**Estimación**: 6-7 horas
**Bloqueante**: Para 1.6
**Notas**:
- Usar datos de `project_dependencies` y symbol relationships
- Colorear output (Rich)

---

## Tarea 1.5: Mejorar Parsers (Go + React specifics)

**Descripción**: Mejorar extracción de símbolos específicos para Go y React

**Subtareas**:
- [ ] Go parser improvements:
  - Structs + fields
  - Métodos (receivers)
  - Interfaces
  - Type aliases
  - Error handling (defer, error returns)

- [ ] TypeScript/React parser improvements:
  - React components (function vs class)
  - Props interface
  - Hooks (useState, useEffect, etc.)
  - Custom hooks
  - Context providers
  - Redux/Zustand stores

- [ ] Metadata enriquecida:
  ```python
  class GoStruct(Symbol):
      fields: list[Field]
      methods: list[MethodRef]
  
  class ReactComponent(Symbol):
      props_interface: str
      hooks_used: list[str]
      is_export: bool
  ```

- [ ] Tests:
  - Extraer struct y sus métodos
  - Extraer React component con hooks
  - Relaciones correctas

**Estimación**: 8-10 horas
**Bloqueante**: Para 1.6
**Notas**:
- Tree-sitter queries específicas por language
- Validación con código real de proyectos

---

## Tarea 1.6: Reports Generation

**Descripción**: Reportes automáticos sobre el estado del codebase

**Subtareas**:
- [ ] Crear `query/reports.py`:
  ```python
  class ReportGenerator:
      def dead_code(self, project_name: str) -> Report
      def unused_exports(self, project_name: str) -> Report
      def orphaned_endpoints(self, project_name: str) -> Report
      def dependency_graph(self, format: str = 'ascii') -> Report
  ```

- [ ] Reportes:
  1. **Dead Code**:
     - Símbolos no referenciados desde otros
     - Exportados pero no usados
     ```
     $ sampler report dead-code --project backend-go
     
     ⚠️  Dead Code Report for backend-go
     
     internal.DeprecatedHandler (function)
       └─ No usages found
     
     LegacyLogger (type)
       └─ No usages found
     
     Total: 2 symbols (0.8% of codebase)
     ```

  2. **Unused Exports**:
     - Algo exportado que no se usa en otros proyectos
     ```
     $ sampler report unused-exports --project backend-go
     
     ✨ Exports not used in other projects:
     
     UserService (service)
       └─ Defined in backend-go, not used anywhere
     ```

  3. **Orphaned Endpoints**:
     - Endpoints que no se llaman desde ningún lado
     ```
     $ sampler report orphaned-endpoints
     
     🚫 Orphaned Endpoints (not called from any project):
     
     GET /api/v1/legacy-users (backend-go)
       └─ No callers found
     ```

  4. **Dependency Graph**:
     - Formato Mermaid o ASCII
     ```
     $ sampler report dependency-graph --format mermaid
     
     graph LR
       A[backend-go] -->|API| B[frontend-react]
       A -->|Data| C[dashboards-pbi]
       D[integration-layer] -->|imports| A
     ```

- [ ] Tests:
  - Detectar dead code
  - Generar reportes en múltiples formatos

**Estimación**: 8-9 horas
**Bloqueante**: Ninguno crítico
**Notas**:
- Usar Mermaid para graphs (muy visual)
- ASCII fallback para terminal

---

## Tarea 1.7: CLI - Report Commands

**Descripción**: Exponer reportes en CLI

**Subtareas**:
- [ ] Comandos:
  ```bash
  sampler report dead-code --project <name> [--export json/csv]
  sampler report unused-exports --project <name>
  sampler report orphaned-endpoints [--export mermaid]
  sampler report dependency-graph [--format ascii/mermaid/dot]
  ```

- [ ] Integrar con CLI:
  - Crear `cli/commands/report.py`
  - Typer subcommands
  - Export options (JSON, CSV, Mermaid)

**Estimación**: 4-5 horas
**Bloqueante**: Ninguno crítico
**Notas**:
- Pretty tables y output
- Export a archivo (`--output file.md`)

---

## Tarea 1.8: Documentation Update

**Descripción**: Actualizar docs con Fase 1 features

**Subtareas**:
- [ ] Update `CLI_REFERENCE.md`:
  - Nuevos comandos
  - Ejemplos de outputs
  - `.sampler.yaml` schema

- [ ] Update `ARCHITECTURE.md`:
  - Cross-project relationships
  - Report generation flow

- [ ] Tutorial: "Finding Integration Points"
  ```markdown
  # Finding Integration Points with Sampler
  
  1. `sampler connections backend-go frontend-react`
  2. `sampler endpoints backend-go`
  3. Identify affected endpoints
  4. Use `sampler search-all` to track usage
  ```

**Estimación**: 3-4 horas
**Bloqueante**: Ninguno

---

## Tarea 1.9: Testing & QA

**Subtareas**:
- [ ] Unit tests para nuevos módulos
  - Metadata parsing
  - Endpoint extraction
  - Cross-project detection
  - Report generation

- [ ] Integration tests:
  - Setup 3 proyectos conectados
  - Detectar relaciones correctamente
  - Generar reportes

- [ ] Performance testing:
  - Indexar 1000+ archivos
  - Cross-project search performance
  - Report generation time

- [ ] Manual QA:
  - Probar con tus proyectos reales
  - Verificar endpoints detectados
  - Conexiones correctas

**Estimación**: 6-8 horas

---

## 🎯 Checklist Fase 1

- [ ] 1.1: Project metadata & exports
- [ ] 1.2: Endpoint extraction (Go + React)
- [ ] 1.3: Cross-project relationships
- [ ] 1.4: CLI endpoints & connections
- [ ] 1.5: Mejorar parsers
- [ ] 1.6: Reports generation
- [ ] 1.7: CLI report commands
- [ ] 1.8: Documentation
- [ ] 1.9: Testing & QA

**Total Estimado**: 55-67 horas de trabajo

---

---

# 🚀 FASE 2: Advanced Analysis & Pi Integration

**Objetivo**: Análisis de impacto, generación de contexto para Pi, búsqueda semántica.

**Prerequisitos**: Fase 0 + Fase 1 completadas

**Definición de "Done"**:
- ✅ Puedo ver impacto de un cambio en múltiples proyectos
- ✅ Generar contexto estructurado para Pi
- ✅ Búsqueda semántica (básica)
- ✅ Command que devuelve "flujo completo" de un símbolo
- ✅ Reportes de arquitectura

---

## Tarea 2.1: Impact Analysis Engine

**Descripción**: Analizar impacto de cambios en un símbolo/archivo

**Subtareas**:
- [ ] Crear `query/impact.py`:
  ```python
  class ImpactAnalyzer:
      def impact(self, project: str, symbol: str) -> ImpactReport:
          # Qué se ve afectado si cambio X?
          # - Direct usages
          # - Dependent symbols
          # - Tests
          # - Endpoints affected
          # - Cross-project impact
          
      def diff_impact(self, project: str, from_ref: str, to_ref: str) -> DiffImpactReport:
          # Dado un diff, qué se ve afectado?
  ```

- [ ] Lógica de impact:
  1. Encontrar símbolo
  2. Buscar usages directas
  3. Buscar usages indirectas (cadena de llamadas)
  4. Buscar tests que lo usan
  5. Buscar endpoints que lo usan
  6. Buscar referencias en otros proyectos
  7. Compilar reporte

- [ ] Data structures:
  ```python
  @dataclass
  class ImpactReport:
      symbol: Symbol
      direct_usages: list[Usage]
      indirect_usages: list[Usage]  # Through other functions
      tests_affected: list[TestFile]
      endpoints_affected: list[Endpoint]
      cross_project_impact: list[CrossProjectImpact]
      severity: str  # low, medium, high, critical
  ```

- [ ] Tests:
  - Cambiar función, ver impacto
  - Cambiar tipo, ver impacto
  - Cambiar endpoint, ver endpoints afectados

**Estimación**: 8-10 horas
**Bloqueante**: Para 2.2, 2.3
**Notas**:
- Detectar "severity" por número de referencias
- Transitive dependencies (A calls B, B calls C)

---

## Tarea 2.2: Diff Analysis (Git Integration)

**Descripción**: Analizar cambios en una rama y calcular impacto

**Subtareas**:
- [ ] Crear `query/diff_analyzer.py`:
  ```python
  class DiffAnalyzer:
      def analyze_diff(self, project: str, from_ref: str, to_ref: str) -> DiffAnalysisReport:
          # 1. Git diff entre refs
          # 2. Para cada file changed, re-index
          # 3. Comparar símbolos old vs new
          # 4. Detectar: added, removed, modified
          # 5. Calculate impact de cada cambio
  ```

- [ ] Integración con Git:
  - Ejecutar `git diff` (si no es "stash")
  - Parsear changed files
  - Para cada file, obtener content old y new
  - Comparar ASTs

- [ ] Report:
  ```
  Changed Symbols:
    ├─ Added: 2 functions, 1 type
    ├─ Removed: 1 function
    └─ Modified: 5 functions (3 signature changes)
  
  Impact:
    ├─ Tests affected: 8
    ├─ Endpoints affected: 2
    ├─ Cross-project impact: 1 (dashboards-pbi)
  ```

- [ ] Tests:
  - Mock git diff
  - Parse changes
  - Calculate impact

**Estimación**: 7-8 horas
**Bloqueante**: Para 2.3
**Notas**:
- Usar `GitPython` para interacción con git
- Manejar merge conflicts, stashes, etc.

---

## Taska 2.3: CLI - Impact Commands

**Descripción**: Exponer impact analysis en CLI

**Subtareas**:
- [ ] Comandos:
  ```bash
  sampler impact <project> <symbol>
  sampler impact <project> <symbol> --downstream  # Solo referencias
  sampler impact <project> <symbol> --upstream    # Solo dependencias
  sampler diff-impact <project> --from <ref> --to <ref>
  ```

- [ ] Output:
  ```
  $ sampler impact backend-go GetUser --downstream
  
  💥 Impact Analysis: GetUser in backend-go
  
  Direct Usages (4)
    ├─ ListUsersHandler (handlers.go:45)
    ├─ GetUserByIDHandler (handlers.go:78)
    ├─ test_user.go (2 tests)
    └─ integration_layer/user_client.go
  
  Indirect Usages (2)
    ├─ Called through: UserService.Fetch
    └─ Called through: DTO transformation
  
  Endpoints Affected (2)
    ├─ GET /api/v1/users/{id}
    └─ GET /api/v1/me (auth-protected)
  
  Cross-Project Impact
    └─ frontend-react: 3 components call these endpoints
  
  Severity: HIGH (7 direct + 2 indirect references)
  ```

**Estimación**: 5-6 horas
**Bloqueante**: Ninguno crítico
**Notas**:
- Colorear severidad (red/yellow/green)

---

## Tarea 2.4: Semantic Search (Embeddings)

**Descripción**: Búsqueda semántica usando embeddings locales

**Subtareas**:
- [ ] Mejorar `query/semantic.py`:
  - Opción 1: Usar `sentence-transformers` (pequeño, rápido)
  - Opción 2: Usar `ollama` con `nomic-embed-text` (local)
  - Opción 3: TF-IDF simple (Fase 2, v1)

- [ ] Para Fase 2:
  - Embeddings básicos (TF-IDF o simples palabra vectors)
  - Cache de embeddings en DB
  - Búsqueda semántica por proyecto

  ```python
  class SemanticEngine:
      def embed_symbol(self, symbol: Symbol) -> np.ndarray:
          # Crear embedding de: nombre + docstring + contexto
          
      def semantic_search(self, project: str, query: str, top_k: int = 5) -> list[Symbol]:
          # Buscar símbolos similares semánticamente
  ```

- [ ] Tests:
  - Buscar "user authentication"
  - Encontrar funciones de auth relevantes
  - Búsqueda cross-project

**Estimación**: 6-8 horas
**Bloqueante**: Ninguno crítico (nice to have)
**Notas**:
- Empezar simple (TF-IDF), mejorar después
- Si quieres full embeddings, usar `sentence-transformers` (es muy bueno)

---

## Tarea 2.5: Context Generation for Pi

**Descripción**: Generar contexto estructurado para pasar a Pi

**Subtareas**:
- [ ] Crear `cli/commands/context.py`:
  ```bash
  sampler context <project> <symbol>
  sampler context <project> <file>
  sampler context --integration <proj1> <proj2>
  sampler context --for-pr <project> --from main --to feature-x
  ```

- [ ] Generar contexto "copy-paste ready":
  ```python
  class ContextGenerator:
      def generate_symbol_context(self, project: str, symbol_name: str) -> str:
          # Retornar Markdown/Text con:
          # - Definición del símbolo
          # - Signature
          # - Docstring
          # - Usages (top 5)
          # - Relaciones (qué llama, quién lo llama)
          # - Tests relevantes
          # - Formato: fácil copy-paste a Pi
      
      def generate_integration_context(self, proj1: str, proj2: str) -> str:
          # Contexto sobre cómo se integran dos proyectos
          # - Endpoints usados
          # - DTOs compartidas
          # - Flujo de datos
      
      def generate_pr_context(self, project: str, from_ref: str, to_ref: str) -> str:
          # Contexto sobre cambios en una PR
          # - Qué cambió
          # - Impacto
          # - Tests affected
          # - Recomendaciones
  ```

- [ ] Output format:
  ```
  $ sampler context backend-go GetUser
  
  # Symbol Context: GetUser (backend-go)
  
  ## Definition
  File: handlers/user.go:42-65
  
  ```go
  func GetUser(c *gin.Context) error {
      // ... implementation
  }
  ```
  
  ## Signature
  Input: gin.Context
  Output: (*User, error)
  
  ## Docstring
  Retrieves a single user by ID. Requires authentication.
  
  ## Usages (5 total)
  1. ListUsersHandler (handlers.go:45)
  2. test_user.go:TestGetUser (line 120)
  ... (3 more)
  
  ## Related Symbols
  - Calls: ValidateToken, FetchUserDB
  - Called by: ListUsersHandler, GetUserByIDHandler
  
  ## Tests
  - test_user.go (2 tests)
  - integration_test.go (1 test)
  
  ## Cross-Project Impact
  - frontend-react: UserService calls this endpoint
  ```

- [ ] Integración con Pi:
  - Comando que devuelve markdown listo para pegar en Pi prompt
  - Incluir "formatted for AI" option

**Estimación**: 7-8 horas
**Bloqueante**: Ninguno crítico
**Notas**:
- Pensado para copy-paste directo a Pi
- Markdown bien formateado
- Incluir "tl;dr" section

---

## Tarea 2.6: Flow Tracing

**Descripción**: Seguir el flujo completo de un dato o llamada

**Subtareas**:
- [ ] Crear `query/flow_tracer.py`:
  ```python
  class FlowTracer:
      def trace_call_flow(self, start_symbol: str, project: str) -> CallFlow:
          # Dado un símbolo, mostrar toda la cadena de llamadas
          # A -> B -> C -> D (endpoint)
          # Mostrar paso a paso
          
      def trace_data_flow(self, start_symbol: str, project: str) -> DataFlow:
          # Seguir un dato a través del código
          # x = GetUser() -> x.name -> response.json -> API response
  ```

- [ ] Data structures:
  ```python
  @dataclass
  class CallNode:
      symbol: Symbol
      depth: int
      file: str
      line: int
      next_calls: list['CallNode']
      
  class CallFlow:
      start: Symbol
      chain: list[CallNode]
      endpoint: Optional[Endpoint]
  ```

- [ ] Visualización:
  ```
  $ sampler flow GetUser --start backend-go
  
  📍 Call Flow: GetUser in backend-go
  
  GetUser (handlers/user.go:42)
    ↓ calls
  FetchUserDB (db/user.go:100)
    ↓ calls
  QueryBuilder.Where (orm/builder.go:50)
    ↓ returns
  *User (models/user.go)
    ↓ serialized to
  UserDTO (dto/user.go)
    ↓ returned by endpoint
  GET /api/v1/users/{id}
    ↓ used by
  frontend-react: UserService.fetchUser()
  
  Total depth: 6 steps
  ```

- [ ] Tests:
  - Tracer simple call flow
  - Detectar ciclos
  - Llegar a endpoint

**Estimación**: 7-9 horas
**Bloqueante**: Ninguno crítico
**Notas**:
- Detectar ciclos (A -> B -> A)
- Max depth para evitar infinitos

---

## Tarea 2.7: Architecture Analysis

**Descripción**: Análisis de patrones y arquitectura del codebase

**Subtareas**:
- [ ] Detectar patrones:
  - Layered architecture (api -> service -> data)
  - Circular dependencies
  - God objects (clases con muchas responsabilidades)
  - Orphaned modules

- [ ] Generar reporte:
  ```
  $ sampler report architecture
  
  🏗️  Architecture Analysis
  
  Layers Detected:
    ├─ API Layer (handlers) - 12 handlers
    ├─ Service Layer - 8 services
    ├─ Data Layer (db) - 4 data sources
    └─ Models - 15 types
  
  Circular Dependencies: 0 ✅
  
  God Objects (>500 LOC):
    └─ UserService (890 LOC) ⚠️
  
  Orphaned Modules:
    ├─ legacy/deprecated (0 usages)
    └─ experimental/feature-x (1 usage)
  
  Recommendations:
    1. Split UserService into smaller services
    2. Consider archiving legacy/ folder
  ```

- [ ] Crear `query/architecture.py`:
  ```python
  class ArchitectureAnalyzer:
      def detect_layers(self, project: str) -> LayerAnalysis
      def detect_circular_deps(self, project: str) -> list[Cycle]
      def detect_god_objects(self, project: str, threshold: int = 500) -> list[GodObject]
      def generate_architecture_report(self, project: str) -> ArchReport
  ```

**Estimación**: 6-8 horas
**Bloqueante**: Ninguno crítico
**Notas**:
- Usar heurísticas (folder structure, naming patterns)
- LOC counting

---

## Tarea 2.8: CLI - Advanced Commands

**Descripción**: Exponer todas las nuevas features en CLI

**Subtareas**:
- [ ] Actualizar CLI con:
  ```bash
  sampler flow <symbol> --start <project>
  sampler flow <symbol> --start <project> --end <project>
  sampler semantic-search <query> [--project <name>]
  sampler context <symbol> --project <project>
  sampler report architecture --project <project>
  sampler report flow <symbol> --project <project>
  ```

- [ ] Update `cli/main.py`:
  - Agregar nuevos subcommands
  - Help text completo
  - Examples

**Estimación**: 4-5 horas

---

## Tarea 2.9: MCP Server (Optional but valuable)

**Descripción**: Exposición via Model Context Protocol para uso directo con Claude

**Subtareas**:
- [ ] Crear `mcp/server.py`:
  - FastMCP o similar
  - Exponer herramientas:
    - `search_project`
    - `search_all`
    - `get_impact`
    - `get_context`
    - `get_flow`
    - `get_architecture`

- [ ] Permitir a Pi acceso directo:
  ```bash
  sampler mcp-server start --port 3000
  # Luego configurar Pi para usar este MCP server
  ```

- [ ] Tools definitions:
  ```python
  @server.tool()
  def search_project(project: str, query: str) -> list[Symbol]:
      """Search in a single project"""
      
  @server.tool()
  def get_context(project: str, symbol: str) -> str:
      """Get context for a symbol (formatted for Claude)"""
  ```

**Estimación**: 6-8 horas
**Bloqueante**: No (nice to have)
**Notas**:
- Permite a Pi usar `sampler` sin CLI
- Very powerful para agentic workflows

---

## Tarea 2.10: Performance Optimization

**Descripción**: Optimizaciones para speed y memory

**Subtareas**:
- [ ] Profiling:
  - Medir indexing time
  - Medir query time
  - Medir memory usage

- [ ] Optimizaciones:
  - Caching de queries frecuentes
  - Índices adicionales en DB
  - Parallelización de parsers
  - Lazy loading de metadata

- [ ] Benchmarks:
  - Indexar 10000+ archivos
  - Cross-project search performance
  - Report generation time

**Estimación**: 5-7 horas

---

## Tarea 2.11: Documentation & Examples

**Subtareas**:
- [ ] Update docs:
  - Advanced usage guide
  - Impact analysis tutorial
  - Context generation for Pi
  - Architecture analysis guide

- [ ] Example projects:
  - Sample multi-project setup
  - Common workflows
  - Troubleshooting guide

- [ ] Video/walkthrough:
  - Cómo usar sampler en un workflow real
  - Integration con Pi

**Estimación**: 4-6 horas

---

## Tarea 2.12: Testing & QA

**Subtareas**:
- [ ] Unit tests para nuevos módulos
- [ ] Integration tests
- [ ] Performance tests
- [ ] Manual testing con proyectos reales

**Estimación**: 6-8 horas

---

## 🎯 Checklist Fase 2

- [ ] 2.1: Impact analysis engine
- [ ] 2.2: Diff analysis (Git)
- [ ] 2.3: CLI impact commands
- [ ] 2.4: Semantic search
- [ ] 2.5: Context generation for Pi
- [ ] 2.6: Flow tracing
- [ ] 2.7: Architecture analysis
- [ ] 2.8: CLI advanced commands
- [ ] 2.9: MCP server (optional)
- [ ] 2.10: Performance optimization
- [ ] 2.11: Documentation
- [ ] 2.12: Testing & QA

**Total Estimado**: 62-81 horas de trabajo

---

---

## 📈 Resumen Ejecutivo

| Fase | Duración | Horas | Features | Estado |
|------|----------|-------|----------|--------|
| **0** | 1-2 weeks | 53-63h | Core CLI, search, indexing | MVP |
| **1** | 2-3 weeks | 55-67h | Integrations, analysis, reports | Production |
| **2** | 3-4 weeks | 62-81h | Advanced analysis, Pi integration | Mature |
| **TOTAL** | 6-9 weeks | **170-211h** | Full-featured tool | ✨ |

---

## 🛣️ Recomendación de Prioridades

### Para empezar ASAP (Week 1):
1. **0.1-0.3**: Setup + config + DB
2. **0.4-0.5**: Parsers + indexer
3. **0.7-0.8**: CLI básica

### Para tener MVP funcional (Week 2-3):
4. **0.6, 0.9, 0.10, 0.11**: Query + polish
5. **1.1-1.4**: Integraciones básicas

### Para maximizar impacto con Pi (Week 4-6):
6. **1.5-1.9**: Reportes
7. **2.5**: Context generation (critical para Pi)
8. **2.1-2.3**: Impact analysis

---

## 🎯 Success Metrics

**Fase 0**: 
- Indexar 4+ proyectos en <2 minutos total
- Buscar símbolo en <100ms

**Fase 1**:
- Mostrar connections entre proyectos con 100% accuracy
- Generar reports en <1 segundo

**Fase 2**:
- Context generation < 500ms
- Impact analysis < 1 segundo
- MCP server latency < 200ms

---

**Next Step**: ¿Empezamos con la Tarea 0.1? 🚀