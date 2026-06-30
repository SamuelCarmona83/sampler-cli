# 📋 Sampler: Plan de Implementación Unificado

> **Proyecto**: Sampler - CLI indexador y navegador de codebase multiproyecto  
> **Enfoque**: Iterativo, pragmático, CLI-first y extensible a MCP  
> **Stack**: Python 3.11+ (uv), SQLite, Typer, Rich, Tree-sitter  
> **Objetivo Final**: Herramienta productiva para navegar integraciones y generar contexto para agentes IA (Pi, etc.)

---

## 🎯 Visión General

**Sampler** es una herramienta que:
1. Indexa múltiples proyectos en un codebase compartido o individual
2. Proporciona búsqueda estructural (funciones, clases, endpoints) y semántica
3. Rastrea dependencias y relaciones entre símbolos
4. Genera contexto estructurado para agentes IA
5. Expone sus capacidades via CLI (inmediato) y MCP (extensible)

**Filosofía**: Entregar valor en cada fase. MVP funcional en 2-3 semanas.

---

## 📊 Estructura de Fases

| Fase | Duración | Foco | Entregables |
|------|----------|------|-------------|
| **0** | 1-2 semanas | MVP CLI core | Indexador funcional, búsqueda básica |
| **1** | 1-2 semanas | Multi-lenguaje + relaciones | 3 lenguajes, queries estructurales |
| **2** | 1-2 semanas | Semántica + MCP + valor IA | Búsqueda semántica, MCP, contexto para Pi |
| **TOTAL** | 3-6 semanas | - | Herramienta usable y extensible |

---

## 🏗️ Arquitectura (Modular)

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
│   ├── config.py                    # Configuración global
│   ├── models.py                    # Dataclasses: Symbol, Relationship, File
│   ├── db.py                        # SQLite + schema
│   ├── indexer/
│   │   ├── __init__.py
│   │   ├── discover.py              # File discovery + .gitignore
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseParser abstracto
│   │   │   ├── python.py            # Python parser
│   │   │   ├── go.py                # Go parser (Fase 1)
│   │   │   └── typescript.py        # TypeScript/JavaScript parser (Fase 1)
│   │   ├── builder.py               # Construcción del grafo
│   │   └── store.py                 # Persistencia en SQLite
│   ├── query/
│   │   ├── __init__.py
│   │   ├── engine.py                # Motor de búsqueda
│   │   └── semantic.py              # Búsqueda semántica (Fase 2)
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                  # Typer CLI
│   └── mcp/
│       ├── __init__.py
│       └── server.py                # FastMCP server (Fase 2, opcional)
├── tests/
│   ├── conftest.py
│   ├── test_discover.py
│   ├── test_parsers.py
│   ├── test_db.py
│   ├── test_query.py
│   └── test_cli.py
└── docs/
    ├── ARCHITECTURE.md
    ├── CLI_REFERENCE.md
    └── MCP_GUIDE.md
```

**Principios**:
- **CLI-first**: Todo el core usable desde línea de comandos
- **Core compartido**: CLI y MCP usan las mismas clases
- **Parsers modulares**: Fácil agregar nuevos lenguajes
- **SQLite simple**: Portable y eficiente
- **Extensible**: Diseñado para crecer sin refactorizar

---

## 🗄️ Schema de Base de Datos (Core)

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    language TEXT,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_count INTEGER DEFAULT 0
);

CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    path TEXT NOT NULL,
    language TEXT,
    hash TEXT,
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, path)
);

CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(id),
    type TEXT NOT NULL,              -- function, class, method, struct, component, enum, etc.
    name TEXT NOT NULL,
    qualified_name TEXT,
    signature TEXT,
    docstring TEXT,
    start_line INTEGER,
    end_line INTEGER,
    metadata JSON                    -- tags, decorators, visibility, etc.
);

CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES symbols(id),
    target_id INTEGER REFERENCES symbols(id),
    type TEXT NOT NULL,              -- CALLS, IMPORTS, CONTAINS, RENDERS, IMPLEMENTS, etc.
    line INTEGER,
    metadata JSON
);

CREATE TABLE project_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_project_id INTEGER REFERENCES projects(id),
    target_project_id INTEGER REFERENCES projects(id),
    type TEXT NOT NULL,              -- imports, api_calls, shared_models
    metadata JSON,
    UNIQUE(source_project_id, target_project_id, type)
);

-- Índices para performance
CREATE INDEX idx_symbols_name ON symbols(name);
CREATE INDEX idx_symbols_qualified ON symbols(qualified_name);
CREATE INDEX idx_relations_source ON relationships(source_id);
CREATE INDEX idx_relations_target ON relationships(target_id);
CREATE INDEX idx_files_project ON files(project_id);
```

---

# 🎯 FASE 0: MVP CLI Básico (1-2 semanas)

**Objetivo**: Tener un CLI funcional que pueda indexar un proyecto y hacer búsquedas básicas.

**Definición de "Done"**:
- ✅ Comando `sampler index <path>`
- ✅ Comando `sampler search <query>`
- ✅ Comando `sampler overview <file>`
- ✅ Instalable via pip
- ✅ Output bonito con Rich

---

## Tarea 0.1: Setup Inicial

**Descripción**: Scaffolding, pyproject.toml, estructura de carpetas

**Subtareas**:
- [ ] Crear repo con estructura de carpetas (ver arquitectura)
- [ ] `pyproject.toml`:
  ```toml
  [project]
  name = "sampler-cli"
  version = "0.1.0"
  description = "CLI indexer for code navigation"
  requires-python = ">=3.11"
  dependencies = [
      "typer[all]==0.12.0",
      "rich==13.7.0",
      "tree-sitter>=0.21.0",
      "gitignore-parser>=0.1.11",
      "pydantic>=2.6.0",
  ]
  
  [project.scripts]
  sampler = "sampler.cli.main:app"
  
  [project.optional-dependencies]
  dev = [
      "pytest>=7.4.0",
      "pytest-cov>=4.1.0",
      "ruff>=0.1.0",
      "mypy>=1.7.0",
  ]
  mcp = ["fastmcp>=0.1.0"]  # Fase 2
  semantic = ["sentence-transformers>=2.2.0"]  # Fase 2
  ```
- [ ] `.gitignore` (Python + IDE)
- [ ] `README.md` con quick start
- [ ] GitHub Actions workflow básico (lint + tests)

**Estimación**: 2-3 horas

---

## Tarea 0.2: Models & Database

**Descripción**: Dataclasses, SQLite schema, abstracción de DB

**Subtareas**:
- [ ] `models.py`:
  ```python
  @dataclass
  class Project:
      id: int | None
      name: str
      path: str
      language: str
      indexed_at: datetime | None
  
  @dataclass
  class Symbol:
      id: int | None
      file_id: int
      type: str  # function, class, method, etc.
      name: str
      qualified_name: str | None
      signature: str | None
      docstring: str | None
      start_line: int
      end_line: int
      metadata: dict | None
  
  @dataclass
  class Relationship:
      id: int | None
      source_id: int
      target_id: int
      type: str  # CALLS, IMPORTS, CONTAINS
      line: int | None
      metadata: dict | None
  ```
- [ ] `db.py`:
  - Clase `Database` con SQLAlchemy (o raw SQL)
  - Métodos: `init_schema()`, `add_symbol()`, `search()`, `get_relationships()`
  - Context manager para conexiones
  - Transaccionalidad básica
- [ ] Tests de DB (CRUD operations)

**Estimación**: 4-5 horas

---

## Tarea 0.3: File Discovery

**Descripción**: Recorrer proyecto respetando `.gitignore`

**Subtareas**:
- [ ] `indexer/discover.py`:
  ```python
  def discover_files(
      project_path: str,
      language: str,
      ignore_patterns: list[str] | None = None
  ) -> list[str]:
      """Devuelve lista de archivos a indexar."""
  ```
- [ ] Respetar `.gitignore` del proyecto
- [ ] Patrones por defecto: `.git/`, `node_modules/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.venv/`, etc.
- [ ] Filtrar por extensión según lenguaje
- [ ] Tests con proyecto de ejemplo

**Estimación**: 2-3 horas

---

## Tarea 0.4: Python Parser (Fase 0)

**Descripción**: Extraer símbolos de código Python usando tree-sitter

**Subtareas**:
- [ ] `indexer/parsers/base.py`:
  ```python
  class BaseParser(ABC):
      language: str
      
      @abstractmethod
      def parse(self, content: str, filepath: str) -> list[Symbol]:
          pass
  ```

- [ ] `indexer/parsers/python.py`:
  - Detectar: funciones, clases, métodos, imports, variables globales
  - Extraer: nombre, líneas, docstring, decoradores, signatura
  - Relaciones: CALLS (básico), IMPORTS, CONTAINS (métodos en clases)
  - Usar `tree-sitter-python`
  
  Ejemplo de salida:
  ```
  Symbol(name="get_user", type="function", line=10-20)
  Symbol(name="UserService", type="class", line=30-50)
  Symbol(name="__init__", type="method", line=31-35, qualname="UserService.__init__")
  Relationship(UserService.__init__ -> get_user, type=CALLS)
  ```

- [ ] Tests:
  - Parsear archivo Python simple
  - Verificar symbols extraídos
  - Verificar relaciones

**Estimación**: 6-8 horas

---

## Tarea 0.5: Indexer Builder & Store

**Descripción**: Orquestar indexación de proyecto completo

**Subtareas**:
- [ ] `indexer/builder.py`:
  ```python
  class IndexBuilder:
      def index_project(
          self,
          project_name: str,
          project_path: str,
          language: str,
          force: bool = False
      ) -> None:
          """Indexa proyecto completo."""
  ```
  - Descubrir archivos
  - Parsear cada archivo
  - Guardar en DB
  - Mostrar progress bar con Rich
  - Manejo de errores (1 archivo malo no rompe todo)

- [ ] `indexer/store.py`:
  ```python
  class SymbolStore:
      def save_symbols(
          self,
          project_id: int,
          filepath: str,
          symbols: list[Symbol],
          relationships: list[Relationship]
      ) -> None:
          """Guarda símbolos en DB."""
  ```

- [ ] Detección de cambios (hash de archivo):
  - Solo re-indexar si cambió (excepto `--force`)

- [ ] Tests de integración:
  - Indexar proyecto pequeño
  - Verificar DB
  - Performance (~30 archivos en <10s)

**Estimación**: 5-6 horas

---

## Tarea 0.6: Query Engine (Local)

**Descripción**: Motor de búsqueda básico

**Subtareas**:
- [ ] `query/engine.py`:
  ```python
  class QueryEngine:
      def search(
          self,
          query: str,
          project_name: str | None = None
      ) -> list[Symbol]:
          """Búsqueda por nombre (LIKE)."""
      
      def get_symbol_details(self, symbol_id: int) -> Symbol:
          """Obtiene detalles de un símbolo."""
      
      def get_file_symbols(self, file_id: int) -> list[Symbol]:
          """Todos los símbolos en un archivo."""
  ```

- [ ] Tests:
  - Buscar símbolo existente
  - Sin resultados
  - Case-insensitive
  - Multiple results

**Estimación**: 3-4 horas

---

## Tarea 0.7: CLI - Typer

**Descripción**: Interfaz de línea de comandos

**Subtareas**:
- [ ] `cli/main.py`:
  ```bash
  sampler init                    # Inicializar config global
  sampler project add <name> <path> --language python
  sampler project list
  sampler project remove <name>
  sampler index <project>         # Re-indexar proyecto
  sampler search <query>          # Buscar en todos los proyectos
  sampler search <query> --project <name>
  sampler overview <filepath>     # Ver símbolos en archivo
  sampler --version
  sampler --help
  ```

- [ ] Output con Rich:
  - Tablas para listar proyectos
  - Colores y emojis para claridad
  - Spinners para operaciones largas
  - Pretty format para resultados

- [ ] Validación:
  - Path existe
  - Proyecto no duplicado
  - Lenguaje soportado

- [ ] Tests:
  - Comando index
  - Comando search
  - Error handling

**Estimación**: 5-6 horas

---

## Tarea 0.8: Config System

**Descripción**: Configuración global en `~/.sampler/`

**Subtareas**:
- [ ] `config.py`:
  - Clase `Config` que maneja `~/.sampler/config.yaml`
  - Métodos: `load()`, `save()`, `add_project()`, `remove_project()`
  - Schema con Pydantic
  
  ```yaml
  version: 1
  cache_dir: ~/.sampler
  projects:
    my-project:
      path: /path/to/project
      language: python
      enabled: true
  ```

- [ ] Crear dirs automáticamente
- [ ] Tests de load/save/validate

**Estimación**: 3-4 horas

---

## Tarea 0.9: Documentation & Polish

**Descripción**: Docs, error handling, ejemplos

**Subtareas**:
- [ ] `README.md`:
  - Descripción clara
  - Installation (`pip install sampler-cli`)
  - Quick start (3-5 ejemplos)
  - Roadmap

- [ ] `docs/ARCHITECTURE.md`:
  - Overview de componentes
  - Flujo de indexación
  - Schema DB visual

- [ ] `docs/CLI_REFERENCE.md`:
  - Todos los comandos
  - Ejemplos
  - Troubleshooting

- [ ] Error handling robusto:
  - Project not found
  - Path invalid
  - Database corrupted
  - Parser errors

- [ ] Polish:
  - Mensajes de error claros
  - Help text (`--help`)
  - Version command

**Estimación**: 3-4 horas

---

## Tarea 0.10: Testing & QA

**Descripción**: Tests exhaustivos, coverage

**Subtareas**:
- [ ] Unit tests:
  - Config system
  - Discovery
  - Parser Python
  - Query engine
  
- [ ] Integration tests:
  - Indexar proyecto pequeño
  - Search funcional
  
- [ ] Coverage: Target 75%+
- [ ] Manual testing con proyecto real

**Estimación**: 4-5 horas

---

## 🎯 Checklist Fase 0

- [ ] 0.1: Setup inicial
- [ ] 0.2: Models & DB
- [ ] 0.3: File discovery
- [ ] 0.4: Python parser
- [ ] 0.5: Indexer builder
- [ ] 0.6: Query engine
- [ ] 0.7: CLI Typer
- [ ] 0.8: Config system
- [ ] 0.9: Documentation
- [ ] 0.10: Testing & QA

**Total Estimado**: 38-48 horas

---

---

# 🚀 FASE 1: Multi-Lenguaje + Queries Estructurales (1-2 semanas)

**Objetivo**: Soporte para Go y TypeScript/JavaScript con queries estructurales.

**Definición de "Done"**:
- ✅ Soporte para Python, Go, TypeScript/JavaScript
- ✅ Comandos `callers`, `usages`, `related`
- ✅ Relaciones: CALLS, IMPORTS, CONTAINS, IMPLEMENTS
- ✅ CLI robusto y fácil de usar

---

## Tarea 1.1: Go Parser

**Descripción**: Extraer símbolos de código Go

**Subtareas**:
- [ ] `indexer/parsers/go.py`:
  - Detectar: funciones, structs, interfaces, métodos, packages, enums
  - Extraer: nombre, líneas, comentarios, receiver (para métodos)
  - Relaciones: IMPORTS, CALLS (básico), CONTAINS
  - Usar `tree-sitter-go`
  
  Ejemplo:
  ```go
  type UserService struct {
      repo Repository
  }
  
  func (s *UserService) GetUser(id string) (*User, error) {
      return s.repo.FindById(id)
  }
  ```
  
  Símbolos esperados:
  - `UserService` (struct)
  - `UserService.GetUser` (method)
  - `Repository.FindById` (used in GetUser)

- [ ] Metadata enriquecida:
  ```python
  class GoStruct(Symbol):
      fields: list[tuple[str, str]]  # (name, type)
      methods: list[str]
  ```

- [ ] Tests con código Go real

**Estimación**: 7-8 horas

---

## Tarea 1.2: TypeScript/JavaScript Parser

**Descripción**: Extraer símbolos de TS/JS

**Subtareas**:
- [ ] `indexer/parsers/typescript.py`:
  - Detectar: funciones, clases, interfaces, métodos, componentes React (heurística)
  - Extraer: nombre, líneas, JSDoc, exports
  - Relaciones: IMPORTS, CALLS, RENDERS, IMPLEMENTS
  - Usar `tree-sitter-typescript`
  
  Ejemplo:
  ```typescript
  interface UserProps {
    id: string;
    onUpdate?: (user: User) => void;
  }
  
  export const UserComponent: React.FC<UserProps> = ({ id, onUpdate }) => {
    const [user, setUser] = useState<User | null>(null);
    
    useEffect(() => {
      fetchUser(id).then(u => {
        setUser(u);
        onUpdate?.(u);
      });
    }, [id, onUpdate]);
    
    return <div>{user?.name}</div>;
  };
  ```
  
  Símbolos esperados:
  - `UserProps` (interface)
  - `UserComponent` (component/function, marked as export)
  - Relaciones: `UserComponent` uses `fetchUser`, `useState`, `useEffect`

- [ ] Detectar React components (heurística):
  - Function que devuelve JSX
  - FC<Props>
  - Tiene hooks

- [ ] Tests con código React/TS real

**Estimación**: 7-8 horas

---

## Tarea 1.3: Relaciones Mejoradas

**Descripción**: Extraer relaciones CALLS, IMPORTS, CONTAINS, IMPLEMENTS

**Subtareas**:
- [ ] Mejorar parsers para detectar:
  - `IMPORTS`: `import X from 'module'` → Relationship(X, module, IMPORTS)
  - `CALLS`: `someFunc()` → Relationship(current_func, someFunc, CALLS)
  - `CONTAINS`: `method en class` → Relationship(class, method, CONTAINS)
  - `IMPLEMENTS`: `class X implements Y` → Relationship(X, Y, IMPLEMENTS)
  - `RENDERS`: React `<Component />` → Relationship(parent, Component, RENDERS)

- [ ] Actualizar DB schema (ya tiene campos)
- [ ] Tests: cada tipo de relación

**Estimación**: 5-6 horas

---

## Tarea 1.4: Query Engine Mejorado

**Descripción**: Queries estructurales

**Subtareas**:
- [ ] `query/engine.py` nuevos métodos:
  ```python
  def get_callers(self, symbol_id: int) -> list[Symbol]:
      """Qué símbolos llaman a este."""
  
  def get_usages(self, symbol_id: int) -> list[tuple[Symbol, int]]:
      """Dónde se usa este símbolo (Symbol, line)."""
  
  def get_related(self, symbol_id: int) -> list[Symbol]:
      """Símbolos relacionados."""
  
  def trace_imports(self, project_name: str, module: str) -> dict:
      """Rastrear imports entre proyectos."""
  ```

- [ ] Tests: callers, usages, related

**Estimación**: 4-5 horas

---

## Tarea 1.5: CLI - Queries Estructurales

**Descripción**: Nuevos comandos CLI

**Subtareas**:
- [ ] Comandos:
  ```bash
  sampler callers <symbol>                 # Qué llama a esto
  sampler usages <symbol>                  # Dónde se usa
  sampler related <symbol>                 # Símbolos relacionados
  sampler trace-imports <module>           # Rastrear imports (Fase 1.6)
  ```

- [ ] Output ejemplo:
  ```
  $ sampler callers "GetUser"
  
  🔍 Callers of GetUser (3 found)
  
  handlers.go:42
    └─ ListUsers (function) calls GetUser
  
  middleware.go:15
    └─ AuthMiddleware (function) calls GetUser
  
  tests/handlers_test.go:100
    └─ TestListUsers (function) calls GetUser
  ```

- [ ] Tests CLI

**Estimación**: 4-5 horas

---

## Tarea 1.6: Cross-Project Support

**Descripción**: Detectar y rastear dependencias entre proyectos

**Subtareas**:
- [ ] Mejorar DB para multi-proyecto:
  - Ya existe `project_dependencies` table
  - Agregar índices necesarios

- [ ] Detectar imports entre proyectos:
  ```go
  import "github.com/vates/shared-models"  // Detectar que es otro proyecto
  ```
  
  ```typescript
  import { UserDTO } from "@company/shared"  // Path alias a otro proyecto
  ```

- [ ] Actualizar queries para considerar múltiples proyectos:
  ```python
  def search_all(self, query: str) -> dict[str, list[Symbol]]:
      """Buscar en todos los proyectos."""
  ```

- [ ] Tests: multi-proyecto

**Estimación**: 4-5 horas

---

## Tarea 1.7: Documentation Update

**Descripción**: Actualizar docs

**Subtareas**:
- [ ] Update `CLI_REFERENCE.md`:
  - Nuevos comandos
  - Ejemplos de output

- [ ] Update `ARCHITECTURE.md`:
  - Parsers por lenguaje
  - Tipos de relaciones

- [ ] Ejemplos prácticos

**Estimación**: 2-3 horas

---

## Tarea 1.8: Testing & QA

**Subtareas**:
- [ ] Tests para nuevos parsers (Go, TS/JS)
- [ ] Tests de relaciones
- [ ] Integration tests multi-proyecto
- [ ] Performance testing
- [ ] Coverage 75%+

**Estimación**: 5-6 horas

---

## 🎯 Checklist Fase 1

- [ ] 1.1: Go parser
- [ ] 1.2: TypeScript/JavaScript parser
- [ ] 1.3: Relaciones mejoradas
- [ ] 1.4: Query engine mejorado
- [ ] 1.5: CLI queries estructurales
- [ ] 1.6: Cross-project support
- [ ] 1.7: Documentation
- [ ] 1.8: Testing & QA

**Total Estimado**: 38-48 horas

---

---

# 🎵 FASE 2: Búsqueda Semántica + MCP + Valor IA (1-2 semanas)

**Objetivo**: Búsqueda semántica, exposición como MCP, generación de contexto para agentes.

**Definición de "Done"**:
- ✅ Búsqueda semántica funcional
- ✅ MCP server expuesto
- ✅ Contexto estructurado para Pi/agentes IA
- ✅ Soporte de endpoints (Go, React)

---

## Tarea 2.1: Semantic Search (Básico)

**Descripción**: Búsqueda semántica usando embeddings locales

**Subtareas**:
- [ ] `query/semantic.py`:
  - Opción A: `sentence-transformers` (all-MiniLM-L6-v2, muy eficiente)
  - Opción B: `ollama` local (si el usuario tiene)
  - Fallback: TF-IDF simple

- [ ] Indexar docstrings + código:
  ```python
  def build_embeddings_index(self):
      """Para cada símbolo, crear embedding de docstring + nombre."""
  ```

- [ ] Query:
  ```python
  def semantic_search(self, query: str, project_name: str | None = None) -> list[Symbol]:
      """Búsqueda semántica similar a 'usuario validación'."""
  ```

- [ ] Ejemplos:
  ```
  $ sampler semantic-search "manejo de errores en pagos"
  
  Encontrados 5 resultados relevantes:
  1. handle_payment_error (handlers.py:120)
  2. validate_payment (utils.py:45)
  3. PaymentErrorHandler (exceptions.py:10)
  ...
  ```

- [ ] Tests con queries típicas

**Estimación**: 5-7 horas

---

## Tarea 2.2: Endpoint Extraction (Go, React)

**Descripción**: Detectar y extraer endpoints REST/GraphQL

**Subtareas**:
- [ ] Mejorar parsers Go y TypeScript:
  
  **Go**:
  ```go
  router.GET("/api/v1/users", handlers.ListUsers)
  router.POST("/api/v1/users", auth.Required, handlers.CreateUser)
  ```
  
  Detectar: método HTTP, path, handler, middleware
  
  **React (Next.js)**:
  ```typescript
  export async function POST(req: Request) {
      // POST /api/users
  }
  ```

- [ ] Guardar endpoints en metadata de Symbol:
  ```python
  endpoint_metadata: {
      method: "GET",
      path: "/api/v1/users",
      handler: "handlers.ListUsers",
      auth: ["Required"],
  }
  ```

- [ ] Comando CLI:
  ```bash
  sampler endpoints <project>     # Listar endpoints
  sampler endpoints <project> --filter "GET /api"
  ```

- [ ] Tests

**Estimación**: 4-5 horas

---

## Taska 2.3: Context Generation for AI

**Descripción**: Generar contexto estructurado para Pi/Claude

**Subtareas**:
- [ ] `cli/commands/context.py` (o integrado en CLI):
  ```bash
  sampler context <symbol> [--project <name>]     # Contexto de símbolo
  sampler context-impact <symbol>                 # Impacto de cambio
  sampler context-file <filepath>                 # Resumen de archivo
  sampler context-flow <symbol>                   # Flujo de ejecución
  ```

- [ ] Generar markdown "copy-paste ready":
  ```markdown
  # Context for PaymentService
  
  ## Definition
  - File: src/services/payment.go
  - Lines: 10-150
  - Type: struct
  
  ## Methods
  - ProcessPayment(tx Transaction) error
  - ValidateTransaction(tx Transaction) bool
  
  ## Callers (3)
  - handlers.CreateOrder (api.go:42)
  - webhooks.HandleStripe (webhooks.go:15)
  
  ## Usages (5)
  ...
  
  ## Related Endpoints
  - POST /api/v1/payments
  
  ## Dependencies
  - repository.TransactionRepo
  - external.StripeAPI
  ```

- [ ] Integrable en prompts de Pi:
  ```
  Usa `sampler context PaymentService` para obtener contexto estructurado.
  ```

- [ ] Tests

**Estimación**: 4-5 horas

---

## Tarea 2.4: Impact Analysis (Básico)

**Descripción**: Analizar impacto de cambios

**Subtareas**:
- [ ] `query/impact.py`:
  ```python
  class ImpactAnalyzer:
      def analyze_impact(self, symbol_id: int) -> ImpactReport:
          """Qué se afecta si cambio este símbolo."""
  ```

- [ ] Calcular:
  - Callers directos
  - Transitive callers (hasta profundidad 3)
  - Endpoints afectados
  - Proyectos afectados (si es cross-project)

- [ ] Output:
  ```
  $ sampler impact "UserService.GetUser"
  
  💥 Impact Analysis
  
  Direct impact: 8 symbols affected
  ├─ handlers.ListUsers (used in 2 endpoints)
  ├─ middleware.Auth (used in auth check)
  └─ ...
  
  Transitive impact: 25+ symbols
  
  Endpoints affected: 5
  - GET /api/v1/users
  - POST /api/v1/users/{id}
  - ...
  ```

- [ ] Tests

**Estimación**: 4-5 horas

---

## Tarea 2.5: MCP Server (FastMCP)

**Descripción**: Exponer como Model Context Protocol server

**Subtareas**:
- [ ] `mcp/server.py` usando `fastmcp`:
  ```python
  from fastmcp import Server
  
  server = Server("sampler")
  
  @server.tool()
  def search(query: str) -> str:
      """Buscar símbolo."""
      # Usar query engine
  
  @server.tool()
  def get_callers(symbol: str, project: str | None = None) -> str:
      """Obtener callers de un símbolo."""
  
  @server.tool()
  def semantic_search(query: str) -> str:
      """Búsqueda semántica."""
  
  @server.tool()
  def get_context(symbol: str) -> str:
      """Contexto estructurado para IA."""
  ```

- [ ] Comando para correr MCP:
  ```bash
  sampler mcp-server          # Inicia servidor MCP en puerto default
  sampler mcp-server --port 3000
  ```

- [ ] Documentación para configurar en Pi:
  - Archivo de configuración MCP
  - Cómo agregarlo como skill

- [ ] Tests

**Estimación**: 4-5 horas

---

## Tarea 2.6: Reportes Básicos

**Descripción**: Reportes útiles de análisis

**Subtareas**:
- [ ] Reportes:
  - **Dead Code**: Símbolos sin referencias
  - **Unused Exports**: Exports no usados en otros proyectos
  - **Dependency Graph**: Mermaid/ASCII
  - **Architecture**: Patrones detectados

- [ ] Comandos:
  ```bash
  sampler report dead-code [--project <name>]
  sampler report dependency-graph [--format mermaid]
  ```

- [ ] Tests

**Estimación**: 4-5 horas

---

## Tarea 2.7: CLI Unificada + Polish

**Descripción**: Consolidar CLI, mejorar UX

**Subtareas**:
- [ ] Reorganizar comandos con grupos lógicos:
  ```
  sampler project <subcommand>
  sampler search <query>
  sampler analyze <symbol>      # Agrupa callers, usages, impact
  sampler report <type>
  sampler context <symbol>
  ```

- [ ] Config por proyecto (`sampler.toml` en proyecto):
  ```toml
  [sampler]
  ignore_patterns = ["*.test.py", "**_mock.go"]
  endpoint_patterns = ["/api/v[0-9]+", "/graphql"]
  ```

- [ ] Help mejorado, ejemplos, autocompletado
- [ ] Colorear output según contexto

**Estimación**: 3-4 horas

---

## Tarea 2.8: Documentation & Guide

**Descripción**: Docs completas + guía de uso con Pi

**Subtareas**:
- [ ] `docs/COMPLETE_GUIDE.md`:
  - Todos los comandos
  - Ejemplos prácticos
  - Troubleshooting

- [ ] `docs/AI_INTEGRATION_GUIDE.md`:
  - Cómo usar con Pi Coding Agent
  - Ejemplos de prompts
  - Skill template para Pi
  - MCP configuration

- [ ] `docs/MCP_SETUP.md`:
  - Cómo configurar como MCP
  - JSON schema de tools
  - Testing

- [ ] Update README con roadmap

**Estimación**: 3-4 horas

---

## Tarea 2.9: Testing & Performance

**Subtareas**:
- [ ] Unit tests para nuevos módulos
- [ ] Integration tests completos
- [ ] Performance tests:
  - Semantic search speed
  - MCP server latency
  - Impact analysis con grafo grande
- [ ] Coverage 80%+
- [ ] Manual testing con proyectos reales

**Estimación**: 5-6 horas

---

## 🎯 Checklist Fase 2

- [ ] 2.1: Semantic search
- [ ] 2.2: Endpoint extraction
- [ ] 2.3: Context generation
- [ ] 2.4: Impact analysis
- [ ] 2.5: MCP server
- [ ] 2.6: Reportes básicos
- [ ] 2.7: CLI unificada + polish
- [ ] 2.8: Documentation
- [ ] 2.9: Testing & Performance

**Total Estimado**: 36-46 horas

---

---

## 📈 Resumen Ejecutivo

| Fase | Duración | Horas | Features | Estado |
|------|----------|-------|----------|--------|
| **0** | 1-2 weeks | 38-48h | CLI core, Python parser, search | MVP |
| **1** | 1-2 weeks | 38-48h | Go + TS/JS, queries estructurales, multi-proyecto | Production |
| **2** | 1-2 weeks | 36-46h | Semántica, MCP, context IA, reportes | Complete |
| **TOTAL** | 3-6 weeks | **112-142h** | Full-featured tool | ✨ |

---

## 🛣️ Recomendación de Prioridades

### Week 1-2 (Fase 0):
1. Setup + DB schema + Python parser → MVP funcional
2. CLI básica + search
3. Testing + documentation

### Week 3-4 (Fase 1):
4. Go + TS/JS parsers
5. Queries estructurales (callers, usages)
6. Cross-project support

### Week 5-6 (Fase 2):
7. Semantic search
8. Context generation (valor máximo para Pi)
9. MCP server
10. Reportes

---

## 🎯 Success Metrics

**Fase 0**: 
- Indexar proyecto Python en <5s
- Search usable
- MVP instalable

**Fase 1**:
- Soporte robusto para 3 lenguajes
- Queries rápidas (<100ms)
- Multi-proyecto funcional

**Fase 2**:
- Semantic search + MCP operativo
- Context generation < 500ms
- Documentación clara para Pi
- Tool productiva para equipo

---

## 🚀 Next Steps

1. **Crear repositorio** con estructura base
2. **Empezar Tarea 0.1-0.3** (setup, DB, discovery)
3. **Validar temprano** con proyecto real del usuario
4. **Iterar rápido** en parsers según feedback

**¿Qué tareas quieres que inicie primero?** 🎯
