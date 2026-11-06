# FitZone - Componentes de Lógica de Negocio (PIA)

Equipo 11 · FIME UANL · Python + FastAPI + PostgreSQL

| Integrante | Matrícula |
|---|---|
| Josue Rodrigo Silva Fraga | 2153436 |
| Jesús Emmanuel Camacho Moreno | 2153842 |
| Valentín Monsivais Martínez | 2157656 |

Materia: Componentes de Lógica de Negocio · Profesor: Miguel Ángel Gómez Marroquín

## Enlaces

- Repositorio: https://github.com/emmxnueo/fit-zone-cln
- Sistema desplegado (Render): https://fit-zone-cln.onrender.com
- Swagger UI: https://fit-zone-cln.onrender.com/docs
- OpenAPI: https://fit-zone-cln.onrender.com/openapi.json (copia en `docs/api/openapi.json`)

> El servicio usa el plan gratuito de Render: se duerme con inactividad y la
> primera petición puede tardar hasta un minuto. Abrir `/docs` unos minutos
> antes de la demostración.

## ¿Qué hace el sistema?

FitZone es un gimnasio que vende membresías y ofrece clases grupales. Este
repositorio implementa dos módulos:

- **Clases y reservas:** catálogo, reservas, lista de espera FIFO con oferta de
  15 minutos, tolerancia de retraso, no-shows y sanción automática.
- **Contratación de membresías:** una *solicitud de membresía* nace en
  `SOLICITADA` y avanza por una máquina de estados (RN-41). Una membresía
  `ACTIVA` es lo que permite ingresar y reservar.

```
SOLICITADA ──activar──▶ ACTIVA ──congelar──▶ SUSPENDIDA
    │                    │  ▲                   │  │
 cancelar             vencer │renovar        descongelar│
    ▼                    ▼  │                   ▼  │vencer
CANCELADA            VENCIDA ◀──────────────────────┘
                     (ACTIVA o SUSPENDIDA --dar de baja--▶ CANCELADA)
```

Reglas implementadas (numeración del BRD): RN-03 una sola membresía activa,
RN-08 renovar con pago confirmado, RN-09 congelar con aprobación del
Administrador, RN-10 baja con aprobación del Administrador, RN-37 solicitud
procesable, RN-38 total = Σ precio × cantidad con `Decimal`, RN-39 cupo del
plan, RN-40 beneficio de referencia y RN-41 transiciones válidas.

En reservas: RN-05 ingreso, RN-11 capacidad, RN-13 elegibilidad, RN-14 categorías
(sin cobro del costo adicional), RN-15 a RN-18 cancelación y no-show, RN-19 a
RN-24 lista de espera, y RN-25 a RN-28 faltas y sanción.

## Arquitectura

```
src/
├── domain/          entidades, Value Objects, agregado SolicitudDeMembresia,
│                    Specifications, máquina de estados y Domain Events
├── application/     casos de uso (ServicioDeMembresias) y puertos (interfaces)
├── infrastructure/  repositorios en memoria y SQL (SQLAlchemy), carga de CSV,
│                    composición de dependencias
└── api/             endpoints REST (FastAPI) y esquemas de entrada/salida
```

- **DDD:** el agregado `SolicitudDeMembresia` protege sus invariantes; cada
  cambio de estado registra un Domain Event.
- **Specification:** condiciones del negocio combinables con AND / OR / NOT
  (`SocioActivo`, `SolicitudConLineas`, `SolicitudValidada`, `PlanesHabilitados`,
  `CupoDisponible`, `SinMembresiaActiva`, `SolicitudProcesable`,
  `BeneficioDeReferencia`, `MembresiaVigente`, `PlanIncluyeCategoria`,
  `SinSancionActiva`, `ElegibleParaReservar`).
- **State Machine:** tablas de transiciones de la membresía y de la reserva en
  `src/domain/state_machine.py`; cualquier transición fuera de la tabla responde 409.
- **Puertos y adaptadores (DIP):** el dominio y la aplicación no conocen la base
  de datos. Con `DATABASE_URL` se usa PostgreSQL; sin ella, memoria.

La documentación de análisis y arquitectura está en `docs/`
(BRD, ADRs, diagramas y OpenAPI).

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/solicitudes` | Crear solicitud (201) |
| GET | `/solicitudes` | Listar; filtro opcional `?estado=SOLICITADA` |
| GET | `/solicitudes/{id}` | Consultar una solicitud |
| GET | `/solicitudes/{id}/procesable` | ¿Es procesable? (RN-37) |
| GET | `/solicitudes/{id}/beneficio-referencia` | ¿Aplica el beneficio? (RN-40) |
| POST | `/solicitudes/{id}/activar` | SOLICITADA → ACTIVA |
| POST | `/solicitudes/{id}/cancelar` | SOLICITADA → CANCELADA |
| POST | `/solicitudes/{id}/congelar` | ACTIVA → SUSPENDIDA (aprobada por el Administrador) |
| POST | `/solicitudes/{id}/descongelar` | SUSPENDIDA → ACTIVA |
| POST | `/solicitudes/{id}/vencer` | ACTIVA o SUSPENDIDA → VENCIDA |
| POST | `/solicitudes/{id}/renovar` | VENCIDA → ACTIVA (pago confirmado) |
| POST | `/solicitudes/{id}/dar-de-baja` | ACTIVA o SUSPENDIDA → CANCELADA (aprobada) |
| POST | `/clases` | Crear clase (201) |
| GET | `/clases`, `/clases/{id}` | Catálogo y consulta; con `?socio_id=` agrega la etiqueta (RN-14) |
| POST | `/clases/{id}/reservas` | Reservar o entrar a la lista de espera (201) |
| POST | `/clases/{id}/reservas/{reserva_id}/cancelar` | Cancelar; con menos de 1 h cuenta como falta |
| POST | `/clases/{id}/oferta/confirmar` | Confirmar la oferta de lugar (15 min) |
| POST | `/clases/procesar-reloj` | Expira ofertas y aplica la tolerancia; acepta `ahora` para la demostración |
| GET | `/socios/{id}` | Faltas y sanción |
| POST | `/socios/{id}/ingresos` | Registrar ingreso (RN-05) |
| GET | `/planes` | Catálogo de planes |
| GET | `/eventos` | Domain Events publicados |
| GET | `/health` | Estado del servicio |

Códigos HTTP: **201** al crear · **200** lecturas y cambios · **400** formato
inválido · **404** no existe · **409** conflicto de estado, cupo o membresía
activa · **422** regla de negocio violada.

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores (sin secretos en el repo):

| Variable | Uso |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credenciales de la base en Docker Compose |
| `DATABASE_URL` | Conexión que usa la app. Si no existe, se usa memoria |
| `APP_PORT` | Puerto publicado por Docker Compose (por defecto 8000) |

## Ejecución con Docker Compose

```bash
cp .env.example .env        # ajusta la contraseña (también dentro de DATABASE_URL)
docker compose up --build   # DB + App en http://localhost:8000/docs
docker compose --profile tests run --rm tests   # pruebas con cobertura
```

La primera petición a la API crea las tablas y carga los datos del paquete
(40 socios, 20 planes y 60 solicitudes) y 3 clases de demostración para el día
siguiente, que no vienen del paquete. Para empezar de cero:
`docker compose down -v`.

## Ejecución local (sin Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
uvicorn src.api.main:app --reload     # sin DATABASE_URL usa memoria
```

## Pruebas y CI/CD

- Pruebas unitarias (`tests/unit`) e integración (`tests/integration`) con
  `pytest`; los repositorios SQL se prueban sobre SQLite en memoria y el flujo de
  reservas también sobre PostgreSQL cuando `DATABASE_URL` apunta a uno.
- GitHub Actions (`.github/workflows/ci.yml`) corre las pruebas contra un
  PostgreSQL 16 y **falla si la cobertura baja de 80%**.
- Evidencia de los datos del paquete del PIA: `docs/evidencia/`
  (`resultados_casos.csv` y `resultados_transiciones.csv`).
- Regenerar la evidencia: `python -m src.infrastructure.ejecutar_paquete`.

## Despliegue

El sistema se despliega en Render con el `Dockerfile` del repositorio y una base
PostgreSQL de Render. Variables configuradas en el servicio: `DATABASE_URL`
(la URL interna de la base) y `PORT=8000`. Health check: `/health`. Cada `push`
a `main` redespliega automáticamente.

## Demostración

1. Abrir https://fit-zone-cln.onrender.com/docs
2. `GET /solicitudes`: se listan las 60 solicitudes del paquete (todas en `SOLICITADA`).
3. `POST /solicitudes` con:
   ```json
   {
     "socio_id": "FIT-C005",
     "lineas": [{"plan_id": "FIT-P001", "cantidad": 3}, {"plan_id": "FIT-P002", "cantidad": 1}],
     "validada": true,
     "cortesia_activa": false
   }
   ```
   Responde 201, estado `SOLICITADA`, total `1967.00` MXN.
4. `GET /solicitudes/{id}/procesable` y `/beneficio-referencia` con el id devuelto.
5. `POST /solicitudes/{id}/activar`: pasa a `ACTIVA`; `GET /solicitudes?estado=ACTIVA` la lista.
6. Errores esperados: `activar` otra vez, 409 · `cantidad: 0`, 422 ·
   `cantidad: "tres"`, 400 · `socio_id` inexistente, 404.
7. `GET /eventos`: se ven los Domain Events publicados.

Reservas (después de activar una membresía a cada socio, con los pasos 3 y 5):

8. `POST /clases` con capacidad 1 y un `inicio` futuro, en hora local y sin zona.
9. `POST /clases/{id}/reservas` con dos socios: el primero queda confirmado y el
   segundo en la lista de espera.
10. Cancelar la reserva del primero: `GET /clases/{id}` muestra la entrada `OFERTADA`.
11. `POST /clases/{id}/oferta/confirmar` con el segundo socio, o
    `POST /clases/procesar-reloj` con un `ahora` 16 minutos después para expirarla.
12. Para ver un no-show, llamar `procesar-reloj` con un `ahora` 11 minutos después del
    inicio; `GET /socios/{id}` muestra la falta y, a la tercera del mes, la sanción.

## Alcance y relación con el análisis

El BRD completo de FitZone vive en `docs/BRD.md`. El código implementa la
**contratación de membresías** (BN-09 y BN-10), que es lo que usa el paquete de
datos del PIA, y **clases, reservas, lista de espera y sanciones** (BN-01 y
BN-02). Las diferencias entre el paquete y el BRD están documentadas en el
Anexo B del reporte, y el estado de cada regla en
`docs/architecture/trazabilidad.md`.

Quedan solo diseñados los reportes, la cancelación de clases, las excepciones,
el alta con edad y deslinde, y el cambio de plan. Las notificaciones se publican
como eventos, sin canal real, y `POST /clases/procesar-reloj` necesita una tarea
programada externa que lo llame.
