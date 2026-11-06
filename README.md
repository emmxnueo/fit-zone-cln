# FitZone - Componentes de Lógica de Negocio (PIA)

Equipo 11 · FIME UANL · Python + FastAPI + PostgreSQL

- Repositorio: _(URL pendiente)_
- Sistema desplegado: _(URL pendiente)_
- Swagger UI: `/docs` · OpenAPI: `/openapi.json`

## Estructura
- `docs/` BRD, arquitectura (ADRs, diagramas) y especificación OpenAPI
- `src/domain` entidades, Value Objects, agregados, eventos, Specifications, máquina de estados
- `src/application` servicios y casos de uso
- `src/infrastructure` repositorios, base de datos, carga de CSV
- `src/api` endpoints REST
- `tests/` unitarias e integración · `data/` CSV del paquete del PIA

## Ejecución con Docker Compose
```bash
cp .env.example .env        # ajusta la contraseña
docker compose up --build   # DB + App en http://localhost:8000/docs
docker compose --profile tests run --rm tests   # pruebas con cobertura
```

## Ejecución local (sin Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
uvicorn src.api.main:app --reload
```

## Demostración
_(pendiente)_
