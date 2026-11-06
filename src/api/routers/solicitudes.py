from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencias import get_servicio
from src.api.mensajes import MOTIVOS
from src.api.parametros import SolicitudId
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

router = APIRouter(prefix="/solicitudes", tags=["Membresías"])

Servicio = Annotated[ServicioDeMembresias, Depends(get_servicio)]

_404 = {404: {"model": ErrorOut, "description": "La solicitud, el socio o el plan no existe"}}
_409 = {409: {"model": ErrorOut, "description": "La acción no se puede hacer en el estado actual"}}
_422 = {422: {"model": ErrorOut, "description": "No se cumple una regla del negocio"}}
_400 = {400: {"model": ErrorOut, "description": "Faltan datos o tienen un formato incorrecto"}}


def _evaluacion(resultado) -> EvaluacionOut:
    return EvaluacionOut(
        cumple=resultado.cumple, motivos=[MOTIVOS[m] for m in resultado.motivos]
    )


@router.post(
    "",
    response_model=SolicitudOut,
    status_code=201,
    summary="Crear una solicitud de membresía",
    description="Registra los planes que el socio quiere contratar y calcula el total. "
                "La membresía empieza a contar hasta que se activa. Regla: RN-38.",
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


@router.get("", response_model=list[SolicitudOut], summary="Ver las solicitudes y membresías",
            description="Puedes filtrar por estado, por ejemplo ACTIVA.", responses={**_400})
def listar_solicitudes(
    svc: Servicio,
    estado: Annotated[EstadoMembresia | None, Query(description="Opcional. Estado a mostrar.")] = None,
):
    return [a_salida(s) for s in svc.listar(estado)]


@router.get("/{solicitud_id}", response_model=SolicitudOut,
            summary="Consultar una solicitud", responses={**_404})
def obtener_solicitud(solicitud_id: SolicitudId, svc: Servicio):
    return a_salida(svc.obtener(solicitud_id))


@router.get("/{solicitud_id}/procesable", response_model=EvaluacionOut,
            summary="Saber si una solicitud se puede activar",
            description="Revisa que el socio esté activo, que tenga planes y que esté "
                        "validada, y explica qué falta. Regla: RN-37.",
            responses={**_404})
def es_procesable(solicitud_id: SolicitudId, svc: Servicio):
    return _evaluacion(svc.evaluar_procesable(solicitud_id))


@router.get("/{solicitud_id}/beneficio-referencia", response_model=EvaluacionOut,
            summary="Saber si aplica el beneficio de referencia",
            description="Aplica a socios Premium con un total de 1500 MXN o más y sin "
                        "cortesía activa. Regla: RN-40.",
            responses={**_404})
def beneficio_de_referencia(solicitud_id: SolicitudId, svc: Servicio):
    return _evaluacion(svc.evaluar_beneficio(solicitud_id))


@router.post("/{solicitud_id}/activar", response_model=SolicitudOut,
             summary="Activar una membresía",
             description="El socio no debe tener otra membresía activa, la solicitud debe "
                         "estar completa y el plan debe tener cupo. "
                         "Reglas: RN-03, RN-37, RN-38, RN-39, RN-41.",
             responses={**_404, **_409, **_422})
def activar(solicitud_id: SolicitudId, svc: Servicio):
    return a_salida(svc.activar(solicitud_id))


@router.post("/{solicitud_id}/cancelar", response_model=SolicitudOut,
             summary="Cancelar una solicitud",
             description="Solo mientras no se haya activado. Regla: RN-41.",
             responses={**_404, **_409})
def cancelar(solicitud_id: SolicitudId, svc: Servicio):
    return a_salida(svc.cancelar(solicitud_id))


@router.post("/{solicitud_id}/congelar", response_model=SolicitudOut,
             summary="Congelar una membresía",
             description="Pausa una membresía activa. Necesita la aprobación del "
                         "Administrador. Regla: RN-09.",
             responses={**_400, **_404, **_409, **_422})
def congelar(solicitud_id: SolicitudId, decision: DecisionIn, svc: Servicio):
    return a_salida(svc.congelar(solicitud_id, decision.aprobada))


@router.post("/{solicitud_id}/descongelar", response_model=SolicitudOut,
             summary="Descongelar una membresía",
             description="La membresía vuelve a estar activa. Regla: RN-41.",
             responses={**_404, **_409})
def descongelar(solicitud_id: SolicitudId, svc: Servicio):
    return a_salida(svc.descongelar(solicitud_id))


@router.post("/{solicitud_id}/vencer", response_model=SolicitudOut,
             summary="Marcar una membresía como vencida",
             description="Se usa al llegar la fecha de vencimiento. Regla: RN-04.",
             responses={**_404, **_409})
def vencer(solicitud_id: SolicitudId, svc: Servicio):
    return a_salida(svc.vencer(solicitud_id))


@router.post("/{solicitud_id}/renovar", response_model=SolicitudOut,
             summary="Renovar una membresía vencida",
             description="Necesita el pago confirmado. Regla: RN-08.",
             responses={**_400, **_404, **_409, **_422})
def renovar(solicitud_id: SolicitudId, pago: PagoIn, svc: Servicio):
    return a_salida(svc.renovar(solicitud_id, pago.pago_confirmado))


@router.post("/{solicitud_id}/dar-de-baja", response_model=SolicitudOut,
             summary="Dar de baja una membresía",
             description="Es definitivo y necesita la aprobación del Administrador. Regla: RN-10.",
             responses={**_400, **_404, **_409, **_422})
def dar_de_baja(solicitud_id: SolicitudId, decision: DecisionIn, svc: Servicio):
    return a_salida(svc.dar_de_baja(solicitud_id, decision.aprobada))
