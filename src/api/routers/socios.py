from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio_clases
from src.api.schemas import ErrorOut, IngresoOut, SocioOut, socio_a_salida
from src.application.clases import ServicioDeClases

router = APIRouter(prefix="/socios", tags=["Socios"])

Servicio = Annotated[ServicioDeClases, Depends(get_servicio_clases)]

_404 = {404: {"model": ErrorOut, "description": "El socio no existe"}}
_422 = {422: {"model": ErrorOut, "description": "Regla de negocio violada (RN-xx)"}}


@router.get("/{socio_id}", response_model=SocioOut, summary="Consultar faltas y sanción",
            responses={**_404})
def obtener_socio(socio_id: str, svc: Servicio):
    return socio_a_salida(svc.obtener_socio(socio_id))


@router.post("/{socio_id}/ingresos", response_model=IngresoOut, status_code=201,
             summary="Registrar un ingreso",
             description="Solo con membresía vigente (RN-05). Cuenta como presente (RN-18).",
             responses={**_404, **_422})
def registrar_ingreso(socio_id: str, svc: Servicio):
    return IngresoOut(socio_id=socio_id, momento=svc.registrar_ingreso(socio_id))
