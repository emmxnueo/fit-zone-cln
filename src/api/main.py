from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from src.domain.errors import ErrorDeDominio

from .routers import catalogo, clases, reportes, socios, solicitudes

_INTERFAZ = Path(__file__).parent / "web" / "index.html"

app = FastAPI(
    title="FitZone - Componentes de Lógica de Negocio",
    description=(
        "API del PIA (Equipo 11, FIME-UANL): membresías, clases, reservas, lista de "
        "espera, sanciones y reportes de FitZone.\n\n"
        "Códigos HTTP: **201** al crear · **200** lecturas y cambios · **400** formato "
        "inválido · **404** no existe · **409** conflicto de estado, cupo o membresía "
        "activa · **422** regla de negocio violada."
    ),
    version="0.6.0",
)


@app.exception_handler(ErrorDeDominio)
async def manejar_error_de_dominio(request: Request, exc: ErrorDeDominio):
    """Traduce los errores del dominio a su código HTTP (409, 422, 404)."""
    return JSONResponse(
        status_code=exc.codigo_http,
        content={"detail": exc.mensaje, "regla": exc.regla, "error": type(exc).__name__},
    )


@app.exception_handler(RequestValidationError)
async def manejar_formato_invalido(request: Request, exc: RequestValidationError):
    """Formato inválido (tipos, campos faltantes) = 400, no el 422 por defecto de FastAPI."""
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Formato de la solicitud inválido",
            "regla": None,
            "error": "FormatoInvalido",
            "errores": jsonable_encoder(exc.errors()),
        },
    )


@app.get("/", include_in_schema=False)
def interfaz() -> FileResponse:
    """Interfaz de demostración. El rol solo cambia lo que se ve: no es autenticación."""
    return FileResponse(_INTERFAZ)


@app.get("/health", tags=["sistema"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(solicitudes.router)
app.include_router(clases.router)
app.include_router(socios.router)
app.include_router(reportes.router)
app.include_router(catalogo.router)
