# Sampler TODO

## Estado

Version actual: 0.4.0

## Hecho

- Estructura base del proyecto y empaquetado Python.
- CLI base y flujo end-to-end funcional.
- Config global en ~/.sampler/config.yaml.
- CRUD de proyectos en config:
  - add_project
  - update_project
  - remove_project
  - get_project
  - list_projects
- Base de datos SQLite con schema principal:
  - projects
  - files
  - symbols
  - relationships
  - project_dependencies
  - embeddings
- Discovery/index incremental con hash de archivos.
- Soporte de .gitignore + ignores por defecto.
- Parser Python con AST (estable).
- Parser Go real (tree-sitter-go).
- Parser TypeScript/JavaScript real (tree-sitter-typescript).
- Soporte monorepo/multilenguaje con --language auto.
- Relaciones en grafo: CONTAINS y CALLS.
- Query engine:
  - search
  - search-all
  - symbols
  - overview
  - callers
  - usages
  - related
- Vista de salida compacta (token-efficient) + modo --style bars.
- Semantic backend local:
  - TF-IDF como backend primario (on-the-fly)
  - Capa de embeddings como adaptador pluggable (EmbeddingProvider)
  - Implementado: BGEProvider (default) + HashProvider (offline). Ollama/Nomic/OpenAI/FastEmbed en segunda etapa (como pedido)
  - Config en ~/.sampler/config.yaml bajo embeddings: {provider, model, base_url}
  - Fallback automático a TF-IDF / hash en entornos sin internet o sin extras
- Embeddings/fingerprints por simbolo persistidos en DB (model + dim por proveedor).
- Comando embed con progress bar (Rich) y soporte de proveedor configurado.
- Nuevo subcomando: sampler config embeddings / show (gestión de proveedor sin tocar yaml directamente).
- Salidas de comandos mucho más limpias: markup Rich (paths dim, nombres bold, tipos coloreados), tablas para project list, mensajes con ✓ y provider details.
- Ranking hibrido semantic/texto/grafo/modificacion.
- Deteccion de stale code (test-only callers).
- Comando project deps para dependencias cross-project heuristicas por imports.
- CI basica en GitHub Actions (pytest).
- Suite de tests en verde.
- Capa de embeddings como adaptador + providers + config + salidas limpias (0.4).
- README, CHANGELOG y RELEASE alineados (actualizado con providers y comandos config).

## Pendiente P0 (alta prioridad)

- Mejorar resolucion de relaciones cross-file (scope/import alias y casos borde) para aumentar precision de callers/usages.
- Reducir falsos positivos de stale-code con reglas adicionales por framework y entrypoints.
- Endurecer validaciones de release:
  - limpiar warnings de setuptools sobre metadata de license/classifiers
  - agregar check de build en CI para wheel+sdist

## Pendiente P1 (media prioridad)

- Re-index awareness:
  - registrar last_reindex_at por proyecto
  - exponer aviso en CLI cuando el indice este posiblemente stale
- Mejorar dependencias cross-project:
  - pasar de heuristica regex a resolucion mas semantica por parser/lenguaje
- Mejoras visuales del modo bars:
  - soporte de flechas ASCII para relaciones
  - mejores leyendas por tipo de relacion

## Pendiente P2 (siguiente fase)

- Context generation para agentes IA.
- MCP server expansion (mas herramientas/queries).
- Reportes de analisis (salud de codigo, hotspots, etc.).

## Comandos utiles

- Instalar deps dev:
  - /opt/homebrew/bin/python3.11 -m pip install -e '.[dev]'
- Instalar extras semantic:
  - /opt/homebrew/bin/python3.11 -m pip install -e '.[semantic]'
- Ver version:
  - sampler version
- Inicializar config:
  - sampler init
- Agregar proyecto:
  - sampler project add myproj /ruta/absoluta --language auto
- Actualizar proyecto:
  - sampler project update myproj --path /ruta/nueva --language python
- Listar proyectos:
  - sampler project list
- Ver dependencias de proyecto:
  - sampler project deps myproj
- Indexar proyecto:
  - sampler index myproj
- Buscar simbolo:
  - sampler search retry --project myproj
- Buscar semantico:
  - sampler search "where retries are handled" --project myproj --semantic
- Generar fingerprints / embeddings (usa proveedor actual de config):
  - sampler embed myproj --batch-size 32
- Configurar proveedor de embeddings:
  - sampler config embeddings --provider bge-small
  - sampler config embeddings --provider ollama --model nomic-embed-text
  - sampler config embeddings --provider hash   # offline
  - sampler config show
- Listar simbolos:
  - sampler symbols myproj --type function --limit 20
- Overview por archivo:
  - sampler overview /ruta/absoluta/al/archivo.py --style bars
- Relaciones:
  - sampler callers retry_request --project myproj
  - sampler usages retry_request --project myproj
  - sampler related retry_request --project myproj --style bars
- Detectar stale code:
  - sampler stale-code myproj --limit 50
- Ejecutar tests:
  - pytest -q
