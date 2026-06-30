# Plan de Implementación Detallado - cbm-lite
## Codebase Memory Lite para Agentes de IA (Compatible con Pi Coding Agent)

**Fecha**: 30 de junio de 2026  
**Versión del plan**: 1.0  
**Objetivo principal**: Crear una herramienta **ligera, CLI-first y extensible a MCP** que construya un grafo de conocimiento del codebase. Esto permite a agentes como **Pi Coding Agent** (y futuros MCP) obtener contexto estructural y semántico de forma eficiente, similar a las capacidades de Copilot pero de forma local y minimalista.

**Stack prioritario del usuario**: Python, Go, React, Vue (y librerías relacionadas).  
**Enfoque**: Iterativo, rápido de implementar, con valor entregado en cada fase. CLI como interfaz principal para máxima compatibilidad con Pi.

---

## 1. Objetivos y Alcance (Lo Esencial)

### Objetivos
- Proporcionar **búsqueda estructural** (callers, usages, referencias) y **búsqueda semántica básica**.
- Reducir tokens y mejorar precisión de agentes de IA al trabajar con el codebase.
- Ser **fácil de usar desde Pi Coding Agent** vía comandos shell.
- Ser **extensible** a MCP sin grandes refactorizaciones.
- Soporte inicial: **Python + TypeScript/JavaScript + Go**.
- Mantenerlo **minimalista** pero escalable.

### Fuera de alcance (MVP)
- Hybrid LSP completo (resolución avanzada de tipos).
- Watcher/auto-index en tiempo real (se puede agregar después).
- UI gráfica o 3D.
- Soporte para 158 lenguajes (empezamos con 3).
- Búsqueda semántica avanzada con múltiples señales (versión básica primero).

### Métricas de éxito
- CLI funcional en < 2 semanas de trabajo dedicado.
- Soporte básico para los 3 lenguajes principales.
- Comandos útiles que Pi pueda invocar fácilmente.
- Posibilidad de exponer como MCP en Fase 3.

---

## 2. Arquitectura General

**Diseño modular** para iteración rápida:

```
cbm-lite/
├── src/cbm_lite/
│   ├── config.py              # Configuración central (cache, ignores, idiomas)
│   ├── models.py              # Dataclasses: Symbol, Relationship, File
│   ├── db.py                  # SQLite + schema + queries básicas
│   ├── indexer/
│   │   ├── discover.py        # Recorrido de archivos + .gitignore
│   │   ├── parsers/           # parser_python.py, parser_go.py, parser_ts.py
│   │   ├── builder.py         # Construcción del grafo
│   │   └── store.py
│   ├── query/
│   │   ├── engine.py          # Motor de consultas (search, callers, usages)
│   │   └── semantic.py        # Búsqueda semántica básica (fácil de mejorar)
│   ├── cli/
│   │   └── main.py            # Typer + Rich/gum (interfaz principal)
│   └── mcp/
│       └── server.py          # FastMCP (opcional, activable por flag)
├── tests/
├── pyproject.toml
└── README.md
```

**Principios de diseño**:
- **CLI-first**: Todo el core usable desde línea de comandos.
- **Core compartido**: CLI y MCP usan las mismas clases de `query.engine`.
- **Parsers independientes**: Fácil agregar nuevos lenguajes.
- **SQLite simple**: Persistencia ligera y portable.
- **Extensibilidad**: El grafo y queries están diseñados para crecer.

---

## 3. Fases de Implementación (Iterativo)

### Fase 0: MVP CLI Básico (1-2 semanas)
**Entregable**: Herramienta instalable que indexa y permite búsquedas básicas.

- Estructura de proyecto + `pyproject.toml` con `uv`.
- `indexer/discover.py` + soporte básico `.gitignore`.
- Parser mínimo para **Python** (tree-sitter-python).
- Schema SQLite + `db.py`.
- CLI con Typer:
  - `cbm-lite index <path>` → Indexa el proyecto.
  - `cbm-lite search <query>` → Búsqueda por nombre.
  - `cbm-lite overview <file>` → Resumen de un archivo.
- Output bonito con Rich.
- Tests básicos del indexer.

**Criterio de done**: Se puede indexar un proyecto Python y buscar funciones/clases.

### Fase 1: Soporte Multi-lenguaje + Queries Estructurales (1-2 semanas)
- Parsers para **Go** y **TypeScript/JavaScript** (tree-sitter-go, tree-sitter-typescript).
- Extracción de relaciones básicas: `CALLS`, `IMPORTS`, `CONTAINS`.
- Queries estructurales:
  - `cbm-lite callers <symbol>`
  - `cbm-lite usages <symbol>`
  - `cbm-lite related <symbol>` (básico)
- Soporte metadata específica (structs Go, componentes React).
- Mejora del CLI con subcomandos claros y ayuda.

**Criterio de done**: Soporte usable para Python + Go + TS/JS. Comandos que Pi puede llamar fácilmente.

### Fase 2: Búsqueda Semántica Básica + Valor para el Equipo (1 semana)
- Módulo `query/semantic.py`:
  - Opción simple: embeddings locales con `sentence-transformers` o embeddings de Ollama.
  - Fallback a fuzzy matching + TF-IDF si no hay modelo.
- Comando `cbm-lite semantic-search "retry logic"`.
- Integración ligera con metadata del grafo.
- Documentación de uso con Pi (ejemplos de prompts/skills).

**Criterio de done**: Búsqueda semántica básica funcional. El usuario puede usarlo con Pi para enriquecer contexto.

### Fase 3: Extensibilidad a MCP + Pulido (1 semana+)
- `mcp/server.py` con FastMCP exponiendo las mismas queries como tools.
- Flag `--mcp` o comando separado para correr como servidor MCP.
- Documentación de cómo agregar como skill/extension en Pi.
- Mejoras de UX: autocompletado, configuración por proyecto (`cbm-lite.toml`).
- Tests de integración CLI + MCP.
- README completo + ejemplos.

**Criterio de done**: El proyecto es usable tanto por CLI (Pi) como por agentes MCP.

---

## 4. Tecnologías y Dependencias Esenciales

**Core**:
- Python 3.11+
- `tree-sitter` + `tree-sitter-python`, `tree-sitter-go`, `tree-sitter-typescript`
- `typer` + `rich` (o `gum` para menús interactivos)
- `sqlite3` (stdlib)
- `pathlib`, `gitignore_parser` (o implementación simple)

**Opcionales (Fase 2+)**:
- `sentence-transformers` o embeddings vía Ollama (para semántica)
- `fastmcp` (para MCP server)

**Herramientas de desarrollo**:
- `uv` para gestión de dependencias y scripts.
- `pytest` + `pytest-cov`.
- `ruff` o `black` + `mypy` para calidad.

**Por qué estas tecnologías**:
- Rápidas de aprender y usar.
- Tree-sitter es el estándar para parsing multi-lenguaje.
- CLI con Typer es muy productivo y Pi-friendly.
- SQLite es suficiente y portable.

---

## 5. Estructura de Proyecto Recomendada

(Ver sección 2)

**Archivos clave a crear primero**:
1. `pyproject.toml`
2. `src/cbm_lite/models.py`
3. `src/cbm_lite/db.py` + schema
4. `src/cbm_lite/indexer/discover.py`
5. `src/cbm_lite/cli/main.py`
6. Parser básico de Python

---

## 6. Schema de Base de Datos (Esencial)

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    language TEXT,
    hash TEXT,
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(id),
    type TEXT NOT NULL,              -- function, class, method, struct, component, etc.
    name TEXT NOT NULL,
    qualified_name TEXT,
    signature TEXT,
    docstring TEXT,
    start_line INTEGER,
    end_line INTEGER,
    metadata JSON                    -- tags React, Go fields, decorators, etc.
);

CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES symbols(id),
    target_id INTEGER REFERENCES symbols(id),
    type TEXT NOT NULL,              -- CALLS, IMPORTS, CONTAINS, RENDERS, USES
    metadata JSON
);

-- Índices recomendados
CREATE INDEX idx_symbols_name ON symbols(name);
CREATE INDEX idx_symbols_qualified ON symbols(qualified_name);
CREATE INDEX idx_relations_source ON relationships(source_id);
CREATE INDEX idx_relations_target ON relationships(target_id);
```

---

## 7. Componentes Clave y Enfoque de Implementación

### Indexer
- **discover.py**: Recorre el árbol respetando `.gitignore` y patrones configurables.
- **parsers/**: Un archivo por lenguaje. Usar tree-sitter para extraer definiciones y llamadas básicas.
- **builder.py**: Crea nodos y relaciones a partir del AST.
- **store.py**: Inserta en SQLite de forma transaccional.

### Query Engine
- Métodos principales:
  - `search_symbols(name, type=None, language=None)`
  - `get_callers(symbol_id)`
  - `get_usages(symbol_id)`
  - `semantic_search(query)` (Fase 2)
- Debe ser independiente del CLI/MCP.

### CLI (Typer)
Ejemplos de comandos:
```bash
cbm-lite index .
cbm-lite search "UserService"
cbm-lite callers "process_payment"
cbm-lite semantic-search "manejo de errores en pagos"
cbm-lite overview src/services/user.go
```

Usar `rich` para tablas bonitas y `gum` si se quieren menús interactivos.

### MCP (Fase 3)
Usar `@mcp.tool()` para exponer las mismas funciones del query engine.

---

## 8. Compatibilidad con Pi Coding Agent

**Estrategia principal**: CLI excelente.

- Pi puede invocar comandos vía su herramienta Bash.
- Crear un **skill/extension** simple para Pi que envuelva los comandos más usados.
- Ejemplos en el README de cómo usarlo dentro de prompts de Pi:
  > "Usa `cbm-lite callers PaymentService` para entender las llamadas."

**Ventajas**:
- No depende de MCP nativo de Pi (que es limitado).
- Funciona inmediatamente.
- MCP se agrega después como capa opcional.

---

## 9. Testing y Calidad

- **Tests unitarios**: Parsers, discover, query engine (fáciles de mockear).
- **Tests de integración**: Indexación completa de proyectos de prueba pequeños.
- **Cobertura**: Apuntar a >70% en el core.
- **Linting**: Ruff + mypy.
- **CI simple**: GitHub Actions básico (lint + tests).

---

## 10. Iteración, Escalabilidad y Mantenimiento

**Cómo escalar/iterar rápidamente**:
- Cada fase entrega valor usable.
- Parsers modulares → agregar Vue, Rust, etc. es sencillo.
- El grafo es extensible (agregar nuevos tipos de nodos/relaciones).
- Configuración por proyecto (`cbm-lite.toml`).
- Documentación clara + ejemplos con Pi.

**Roadmap posterior a MVP**:
- Watcher para cambios incrementales.
- Reportes (dead code, acoplamiento, componentes poco usados).
- Integración más profunda con Ollama (enriquecer prompts automáticamente).
- Export/import de grafos para compartir entre miembros del equipo.

---

## 11. Milestones y Estimaciones (Realistas)

| Milestone | Descripción | Tiempo estimado | Entregable |
|-----------|-------------|------------------|------------|
| M0 | Estructura + CLI básico Python | 3-5 días | `cbm-lite index` + `search` |
| M1 | Go + TS/JS + callers/usages | 5-7 días | Soporte multi-lenguaje + queries estructurales |
| M2 | Búsqueda semántica básica | 3-5 días | Comando semantic-search |
| M3 | MCP + documentación Pi | 3-5 días | Servidor MCP + guía de uso con Pi |
| **Total MVP** | - | **2-3 semanas** | Herramienta usable y extensible |

---

## 12. Riesgos y Mitigaciones

- **Parsing incompleto en Go/React**: Empezar con lo más común (funciones, structs, componentes). Mejorar iterativamente.
- **Rendimiento en repos grandes**: Usar SQLite indexes + paginación en queries. Indexación en background si es necesario.
- **Compatibilidad con Pi**: Validar temprano con comandos reales.
- **Alcance semántica**: Mantenerla básica al principio. Usar embeddings locales simples.

---

## Próximos Pasos Inmediatos

1. Crear el repositorio y la estructura base.
2. Implementar Fase 0 (MVP CLI + Python).
3. Probar con un proyecto real del usuario.
4. Iterar según feedback.

Este plan es **esencial pero completo**. Se puede empezar a codificar inmediatamente en Fase 0.

¿Querés que genere también un `README.md` inicial, el `pyproject.toml`, o que empecemos a crear los primeros archivos del proyecto? 

Puedo generar el archivo Markdown completo o ajustar cualquier sección.