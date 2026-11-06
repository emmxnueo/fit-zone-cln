"""Parámetros de ruta y consulta, con la descripción y el ejemplo que ve el usuario."""
from datetime import date
from typing import Annotated

from fastapi import Path, Query

SolicitudId = Annotated[str, Path(description="Identificador de la solicitud.", examples=["FIT-O001"])]
ClaseId = Annotated[str, Path(description="Identificador de la clase.", examples=["FIT-K001"])]
ReservaId = Annotated[str, Path(description="Identificador de la reserva.", examples=["RES-1A2B3C4D"])]
SocioId = Annotated[str, Path(description="Número de socio.", examples=["FIT-C005"])]
SocioOpcional = Annotated[
    str | None,
    Query(description="Opcional. Muestra si cada clase está incluida en el plan de este socio."),
]
Desde = Annotated[date, Query(description="Primer día del reporte.", examples=["2026-11-01"])]
Hasta = Annotated[date, Query(description="Último día del reporte, incluido.", examples=["2026-11-30"])]
