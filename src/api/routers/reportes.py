from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio_reportes
from src.api.parametros import Desde, Hasta
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

_400 = {400: {"model": ErrorOut, "description": "Faltan datos o tienen un formato incorrecto"}}
_422 = {422: {"model": ErrorOut, "description": "La fecha final es anterior a la inicial"}}


@router.get("/afluencia", response_model=AfluenciaOut, summary="Ver cuánta gente entra por hora y por día",
            description="Cuenta las entradas al gimnasio en un rango de fechas. Regla: RN-35.",
            responses={**_400, **_422})
def afluencia(desde: Desde, hasta: Hasta, svc: Servicio):
    r = svc.afluencia(desde, hasta)
    return AfluenciaOut(
        desde=r.desde,
        hasta=r.hasta,
        total=r.total,
        por_hora=[IngresosPorHoraOut(hora=h, ingresos=n) for h, n in r.por_hora.items()],
        por_dia=[IngresosPorDiaOut(dia=d, ingresos=n) for d, n in r.por_dia.items()],
    )


@router.get("/demanda", response_model=list[DemandaOut], summary="Ver la demanda de cada clase",
            description="Muestra la ocupación y la lista de espera, de mayor a menor. Regla: RN-36.")
def demanda(svc: Servicio):
    return [
        DemandaOut(
            clase_id=d.clase_id, nombre=d.nombre, inicio=d.inicio, capacidad=d.capacidad,
            reservas_confirmadas=d.reservas_confirmadas, ocupacion_pct=str(d.ocupacion_pct),
            en_lista_de_espera=d.en_lista_de_espera,
        )
        for d in svc.demanda()
    ]
