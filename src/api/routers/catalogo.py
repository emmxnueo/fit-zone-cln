from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio
from src.api.schemas import EventoOut, PlanOut, SalonOut
from src.application.servicio import ServicioDeMembresias
from src.domain.salones import SALONES

router = APIRouter(tags=["Planes y eventos"])

Servicio = Annotated[ServicioDeMembresias, Depends(get_servicio)]


@router.get("/salones", response_model=list[SalonOut], summary="Ver los salones y su capacidad",
            description="La capacidad de cada clase es la de su salón. Regla: RN-11.")
def listar_salones():
    return [SalonOut(nombre=s.nombre, capacidad=s.capacidad) for s in SALONES.values()]


@router.get("/planes", response_model=list[PlanOut], summary="Ver los planes de membresía")
def listar_planes(svc: Servicio):
    return [
        PlanOut(
            id=p.id, descripcion=p.descripcion, precio_mxn=str(p.precio.monto),
            cupo=p.cupo, habilitado=p.habilitado, duracion_meses=p.duracion_meses,
        )
        for p in svc.planes.todos().values()
    ]


@router.get("/eventos", response_model=list[EventoOut],
            summary="Ver lo que ha pasado en el sistema",
            description="Lista los eventos de dominio desde el último reinicio.")
def listar_eventos(svc: Servicio):
    return [
        EventoOut(evento=e.nombre, solicitud_id=e.solicitud_id, clase_id=e.clase_id,
                  socio_id=e.socio_id,
                  socios_a_notificar=list(getattr(e, "socios_a_notificar", ())),
                  ocurrido_en=e.ocurrido_en)
        for e in svc.eventos()
    ]
