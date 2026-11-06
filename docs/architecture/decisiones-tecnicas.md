# Decisiones técnicas

Resumen del stack y de cómo se configura, prueba y despliega el sistema. Las decisiones de diseño con alternativas y consecuencias están en los [ADR](adr/README.md).

## Stack

| Tema | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.12 | Lo conoce el equipo; `Decimal` nativo para dinero (RN-38) |
| API | FastAPI 0.115 | Genera OpenAPI y Swagger UI sin trabajo extra, que el PIA exige en producción; validación con Pydantic |
| Base de datos | PostgreSQL 16 | Persistencia real pedida por el PIA; disponible en Docker Compose y en Render |
| Acceso a datos | SQLAlchemy 2.0 con `psycopg` 3 | ORM por mapeo declarativo; el mismo código corre en PostgreSQL y en SQLite en memoria para pruebas |
| Pruebas | pytest, pytest-cov, httpx | Cobertura mínima de 80% exigida; `TestClient` para pruebas de integración |
| Contenedores | Docker y Docker Compose | Entorno reproducible con tres servicios: `db`, `app` y `tests` |
| CI/CD | GitHub Actions | Corre las pruebas contra PostgreSQL 16 y falla si la cobertura baja de 80% |
| Despliegue | Render con el `Dockerfile` del repo y una base PostgreSQL de Render | Plan gratuito y despliegue automático en cada `push` a `main` |

## Configuración (12-Factor App)

La configuración sale del entorno, sin secretos en el código. `.env` está en `.gitignore` y `.env.example` solo trae valores de ejemplo.

| Variable | Uso |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credenciales de la base en Docker Compose |
| `DATABASE_URL` | Conexión de la app. Sin ella, la app usa repositorios en memoria. `normalizar_url` acepta `postgres://` y `postgresql://` de Render y los convierte a `postgresql+psycopg://` |
| `APP_PORT` | Puerto publicado por Compose (por defecto 8000) |

## Entornos

| Entorno | Cómo corre | Base de datos |
|---|---|---|
| Local sin Docker | `uvicorn src.api.main:app --reload` | Memoria (sin `DATABASE_URL`) |
| Docker Compose | `docker compose up --build` | PostgreSQL 16 en el servicio `db` con volumen `pgdata` |
| Pruebas en Compose | `docker compose --profile tests run --rm tests` | PostgreSQL del servicio `db` |
| Pruebas unitarias | `pytest` | SQLite en memoria para los repositorios SQL |
| CI | GitHub Actions | PostgreSQL 16 como servicio del job |
| Producción | Render | PostgreSQL de Render |

## Datos iniciales

La primera petición crea las tablas y carga el paquete del profesor desde `data/*.csv`: 40 socios, 20 planes y 60 solicitudes (`sembrar_si_vacia`). Solo siembra si la base está vacía.

## Verificación del paquete

`src/application/ejecutor_paquete.py` ejecuta los 120 casos de `casos_prueba.csv` y las 20 transiciones de `transiciones_prueba.csv`, y `docs/evidencia/` guarda los resultados. La prueba `tests/integration/test_paquete_csv.py` los contrasta con un oráculo independiente, escrito a mano sobre los CSV, sin usar las Specifications.

## Limitaciones conocidas

- Los Domain Events se publican en memoria (`PublicadorEnMemoria`): `GET /eventos` se vacía si el servicio se reinicia.
- El vencimiento (`/vencer`) lo dispara una llamada explícita; no hay un reloj que lo ejecute solo al llegar la fecha (RN-04).
- El servicio de Render gratuito se duerme con inactividad; la primera petición puede tardar hasta un minuto.
