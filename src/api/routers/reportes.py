from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio_reportes
from src.api.schemas import (
    AfluenciaOut,
    DemandaOut,
    ErrorOut,
    IngresosPorDiaOut,
    IngresosPorHoraOut,
)
from src.application.reportes import ServicioDeReportes

router = APIRouter(prefix="/reportes", tags=["Reportes"])

Servicio = Annotated[ServicioDeReportes, Depends(get_servicio_reportes)]

_400 = {400: {"model": ErrorOut, "description": "Formato de la solicitud inválido"}}
_422 = {422: {"model": ErrorOut, "description": "Fecha final anterior a la inicial (RN-35)"}}


@router.get("/afluencia", response_model=AfluenciaOut, summary="Afluencia por hora y día",
            description="Total de ingresos entre `desde` y `hasta`, ambos inclusive (RN-35).",
            responses={**_400, **_422})
def afluencia(desde: date, hasta: date, svc: Servicio):
    r = svc.afluencia(desde, hasta)
    return AfluenciaOut(
        desde=r.desde,
        hasta=r.hasta,
        total=r.total,
        por_hora=[IngresosPorHoraOut(hora=h, ingresos=n) for h, n in r.por_hora.items()],
        por_dia=[IngresosPorDiaOut(dia=d, ingresos=n) for d, n in r.por_dia.items()],
    )


@router.get("/demanda", response_model=list[DemandaOut], summary="Demanda por clase",
            description="Ocupación y lista de espera de cada clase, de mayor a menor (RN-36).")
def demanda(svc: Servicio):
    return [
        DemandaOut(
            clase_id=d.clase_id, nombre=d.nombre, inicio=d.inicio, capacidad=d.capacidad,
            reservas_confirmadas=d.reservas_confirmadas, ocupacion_pct=str(d.ocupacion_pct),
            en_lista_de_espera=d.en_lista_de_espera,
        )
        for d in svc.demanda()
    ]
