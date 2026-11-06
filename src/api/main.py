from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from src.domain.errors import ErrorDeDominio

from .mensajes import explicar_formato
from .routers import catalogo, clases, reportes, socios, solicitudes

_INTERFAZ = Path(__file__).parent / "web" / "index.html"

_DESCRIPCION = """
API de FitZone (Equipo 11, FIME-UANL): membresías, clases, reservas, lista de espera,
sanciones y reportes.

**Cómo probarla**

1. Crea una solicitud en `POST /solicitudes`.
2. Actívala en `POST /solicitudes/{solicitud_id}/activar`.
3. Consulta las clases en `GET /clases` y reserva en `POST /clases/{clase_id}/reservas`.

**Qué significa cada respuesta**

| Código | Significado |
|---|---|
| 200 | Todo salió bien |
| 201 | Se creó correctamente |
| 400 | Faltan datos o tienen un formato incorrecto |
| 404 | Lo que buscas no existe |
| 409 | La acción no se puede hacer en este momento |
| 422 | No se cumple una regla del negocio |

Los errores explican qué pasó e indican la regla del BRD, por ejemplo `RN-13`.
"""

_SECCIONES = [
    {"name": "Membresías", "description": "Solicitudes y ciclo de vida de la membresía."},
    {"name": "Clases y reservas", "description": "Catálogo, reservas y lista de espera."},
    {"name": "Socios", "description": "Faltas, sanciones y entradas al gimnasio."},
    {"name": "Reportes", "description": "Afluencia y demanda de clases."},
    {"name": "Planes y eventos", "description": "Planes disponibles y eventos del sistema."},
    {"name": "Sistema", "description": "Estado del servicio."},
]

app = FastAPI(
    title="FitZone",
    description=_DESCRIPCION,
    version="0.7.0",
    openapi_tags=_SECCIONES,
    docs_url=None,
)


def _esquema_openapi() -> dict:
    """Quita lo que FastAPI agrega por defecto y no aplica a esta API: su 422 de
    validación (aquí el formato inválido es 400) y los textos en inglés."""
    if app.openapi_schema:
        return app.openapi_schema
    esquema = get_openapi(
        title=app.title, version=app.version, description=app.description,
        routes=app.routes, tags=app.openapi_tags,
    )
    for ruta in esquema["paths"].values():
        for operacion in ruta.values():
            respuestas = operacion["responses"]
            if respuestas.get("422", {}).get("description") == "Validation Error":
                del respuestas["422"]
            for codigo in ("200", "201"):
                if codigo in respuestas:
                    respuestas[codigo]["description"] = "Operación correcta"
    for nombre in ("HTTPValidationError", "ValidationError"):
        esquema["components"]["schemas"].pop(nombre, None)
    app.openapi_schema = esquema
    return esquema


app.openapi = _esquema_openapi


@app.exception_handler(ErrorDeDominio)
async def manejar_error_de_dominio(request: Request, exc: ErrorDeDominio):
    """Traduce los errores del dominio a su código HTTP (409, 422, 404)."""
    return JSONResponse(
        status_code=exc.codigo_http, content={"detail": exc.mensaje, "regla": exc.regla}
    )


@app.exception_handler(RequestValidationError)
async def manejar_formato_invalido(request: Request, exc: RequestValidationError):
    """Formato inválido (tipos, campos faltantes) = 400, no el 422 por defecto de FastAPI."""
    return JSONResponse(
        status_code=400, content={"detail": explicar_formato(exc.errors()), "regla": None}
    )


@app.get("/docs", include_in_schema=False)
def swagger() -> HTMLResponse:
    """Swagger UI sin el bloque de curl, que no le sirve a quien usa la página."""
    pagina = get_swagger_ui_html(
        openapi_url=app.openapi_url, title="FitZone - Swagger UI",
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    )
    html = pagina.body.decode().replace("</head>", "<style>.curl-command{display:none}</style></head>", 1)
    return HTMLResponse(html)


@app.get("/", include_in_schema=False)
def interfaz() -> FileResponse:
    """Interfaz de demostración. El rol solo cambia lo que se ve: no es autenticación."""
    return FileResponse(_INTERFAZ)


@app.get("/health", tags=["Sistema"], summary="Comprobar que el sistema está activo")
def health() -> dict:
    return {"status": "ok"}


app.include_router(solicitudes.router)
app.include_router(clases.router)
app.include_router(socios.router)
app.include_router(reportes.router)
app.include_router(catalogo.router)
