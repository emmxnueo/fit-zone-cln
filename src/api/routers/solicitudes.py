from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio
from src.api.schemas import (
    DecisionIn,
    ErrorOut,
    EvaluacionOut,
    PagoIn,
    SolicitudIn,
    SolicitudOut,
    a_salida,
)
from src.application.servicio import ServicioDeMembresias
from src.domain.state_machine import EstadoMembresia

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes de membresía"])

Servicio = Annotated[ServicioDeMembresias, Depends(get_servicio)]

_404 = {404: {"model": ErrorOut, "description": "La solicitud, el socio o el plan no existe"}}
_409 = {409: {"model": ErrorOut, "description": "Conflicto de estado, cupo o membresía activa"}}
_422 = {422: {"model": ErrorOut, "description": "Regla de negocio violada (RN-xx)"}}
_400 = {400: {"model": ErrorOut, "description": "Formato de la solicitud inválido"}}


@router.post(
    "",
    response_model=SolicitudOut,
    status_code=201,
    summary="Crear una solicitud de membresía",
    description="Crea la solicitud en estado SOLICITADA. Total = Σ precio × cantidad (RN-38).",
    responses={**_400, **_404, **_422},
)
def crear_solicitud(datos: SolicitudIn, svc: Servicio):
    solicitud = svc.crear(
        datos.socio_id,
        [(l.plan_id, l.cantidad) for l in datos.lineas],
        validada=datos.validada,
        cortesia_activa=datos.cortesia_activa,
        referencia=datos.referencia,
    )
    return a_salida(solicitud)


@router.get("", response_model=list[SolicitudOut], summary="Listar solicitudes",
            responses={**_400})
def listar_solicitudes(svc: Servicio, estado: EstadoMembresia | None = None):
    return [a_salida(s) for s in svc.listar(estado)]


@router.get("/{solicitud_id}", response_model=SolicitudOut,
            summary="Consultar una solicitud", responses={**_404})
def obtener_solicitud(solicitud_id: str, svc: Servicio):
    return a_salida(svc.obtener(solicitud_id))


@router.get("/{solicitud_id}/procesable", response_model=EvaluacionOut,
            summary="¿Es procesable? (RN-37)", responses={**_404})
def es_procesable(solicitud_id: str, svc: Servicio):
    r = svc.evaluar_procesable(solicitud_id)
    return EvaluacionOut(cumple=r.cumple, motivos=r.motivos)


@router.get("/{solicitud_id}/beneficio-referencia", response_model=EvaluacionOut,
            summary="¿Aplica el beneficio de referencia? (RN-40)", responses={**_404})
def beneficio_de_referencia(solicitud_id: str, svc: Servicio):
    r = svc.evaluar_beneficio(solicitud_id)
    return EvaluacionOut(cumple=r.cumple, motivos=r.motivos)


@router.post("/{solicitud_id}/activar", response_model=SolicitudOut,
             summary="Activar (SOLICITADA → ACTIVA)",
             description="Exige RN-03 (una sola membresía activa), RN-37 (procesable), "
                         "RN-38 (plan habilitado) y RN-39 (cupo).",
             responses={**_404, **_409, **_422})
def activar(solicitud_id: str, svc: Servicio):
    return a_salida(svc.activar(solicitud_id))


@router.post("/{solicitud_id}/cancelar", response_model=SolicitudOut,
             summary="Cancelar (SOLICITADA → CANCELADA)", responses={**_404, **_409})
def cancelar(solicitud_id: str, svc: Servicio):
    return a_salida(svc.cancelar(solicitud_id))


@router.post("/{solicitud_id}/congelar", response_model=SolicitudOut,
             summary="Congelar (ACTIVA → SUSPENDIDA)",
             description="Solo con solicitud aprobada por el Administrador (RN-09).",
             responses={**_400, **_404, **_409, **_422})
def congelar(solicitud_id: str, decision: DecisionIn, svc: Servicio):
    return a_salida(svc.congelar(solicitud_id, decision.aprobada))


@router.post("/{solicitud_id}/descongelar", response_model=SolicitudOut,
             summary="Descongelar (SUSPENDIDA → ACTIVA)", responses={**_404, **_409})
def descongelar(solicitud_id: str, svc: Servicio):
    return a_salida(svc.descongelar(solicitud_id))


@router.post("/{solicitud_id}/vencer", response_model=SolicitudOut,
             summary="Vencer (ACTIVA o SUSPENDIDA → VENCIDA)",
             description="Lo dispara el reloj del sistema al llegar la fecha de vencimiento (RN-04).",
             responses={**_404, **_409})
def vencer(solicitud_id: str, svc: Servicio):
    return a_salida(svc.vencer(solicitud_id))


@router.post("/{solicitud_id}/renovar", response_model=SolicitudOut,
             summary="Renovar (VENCIDA → ACTIVA)",
             description="Exige el pago confirmado (RN-08).",
             responses={**_400, **_404, **_409, **_422})
def renovar(solicitud_id: str, pago: PagoIn, svc: Servicio):
    return a_salida(svc.renovar(solicitud_id, pago.pago_confirmado))


@router.post("/{solicitud_id}/dar-de-baja", response_model=SolicitudOut,
             summary="Dar de baja (ACTIVA o SUSPENDIDA → CANCELADA)",
             description="Solo con solicitud aprobada por el Administrador (RN-10).",
             responses={**_400, **_404, **_409, **_422})
def dar_de_baja(solicitud_id: str, decision: DecisionIn, svc: Servicio):
    return a_salida(svc.dar_de_baja(solicitud_id, decision.aprobada))
