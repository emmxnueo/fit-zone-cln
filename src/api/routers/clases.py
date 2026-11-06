from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio_clases
from src.api.parametros import ClaseId, ReservaId, SocioOpcional
from src.api.schemas import (
    CancelacionClaseIn,
    ClaseIn,
    ClaseOut,
    DecisionIn,
    ErrorOut,
    RelojIn,
    ReservaOut,
    ResultadoReservaOut,
    ResumenRelojOut,
    SocioIn,
    clase_a_salida,
)
from src.application.clases import ServicioDeClases
from src.domain.clase import Reserva

router = APIRouter(prefix="/clases", tags=["Clases y reservas"])

Servicio = Annotated[ServicioDeClases, Depends(get_servicio_clases)]

_404 = {404: {"model": ErrorOut, "description": "La clase, la reserva o el socio no existe"}}
_409 = {409: {"model": ErrorOut, "description": "La acción no se puede hacer en este momento"}}
_422 = {422: {"model": ErrorOut, "description": "No se cumple una regla del negocio"}}
_400 = {400: {"model": ErrorOut, "description": "Faltan datos o tienen un formato incorrecto"}}


def _con_etiqueta(svc: ServicioDeClases, clase, socio_id: str | None) -> ClaseOut:
    return clase_a_salida(clase, svc.etiqueta(clase, socio_id) if socio_id else None)


@router.post("", response_model=ClaseOut, status_code=201, summary="Crear una clase",
             description="La capacidad debe ser de al menos 1 lugar. Regla: RN-11.",
             responses={**_400, **_422})
def crear_clase(datos: ClaseIn, svc: Servicio):
    return clase_a_salida(svc.crear_clase(
        datos.nombre, datos.categoria, datos.inicio, datos.capacidad,
        instructor=datos.instructor, salon=datos.salon,
    ))


@router.get("", response_model=list[ClaseOut], summary="Ver el catálogo de clases",
            description="Con un socio, indica si cada clase va incluida en su plan. Regla: RN-14.",
            responses={**_404})
def listar_clases(svc: Servicio, socio_id: SocioOpcional = None):
    return [_con_etiqueta(svc, c, socio_id) for c in svc.listar()]


@router.post("/procesar-reloj", response_model=ResumenRelojOut,
             summary="Revisar ofertas vencidas y retrasos",
             description="Vence las ofertas sin confirmar y marca como no-show a quien lleva "
                         "más de 10 minutos de retraso. Puedes indicar una fecha y hora para "
                         "simularlo. Reglas: RN-17, RN-20, RN-21.",
             responses={**_400})
def procesar_reloj(svc: Servicio, datos: RelojIn | None = None):
    r = svc.procesar_reloj(datos.ahora if datos else None)
    return ResumenRelojOut(
        ofertas_expiradas=r.ofertas_expiradas, lugares_ofrecidos=r.lugares_ofrecidos,
        no_shows=r.no_shows, lugares_asignados=r.lugares_asignados,
    )


@router.get("/{clase_id}", response_model=ClaseOut, summary="Consultar una clase",
            responses={**_404})
def obtener_clase(clase_id: ClaseId, svc: Servicio, socio_id: SocioOpcional = None):
    return _con_etiqueta(svc, svc.obtener(clase_id), socio_id)


@router.post("/{clase_id}/cancelacion", response_model=ClaseOut,
             summary="Pedir que se cancele una clase (Instructor)",
             description="Solo el instructor asignado y con 2 horas o más de aviso. Regla: RN-29.",
             responses={**_400, **_404, **_409, **_422})
def solicitar_cancelacion(clase_id: ClaseId, datos: CancelacionClaseIn, svc: Servicio):
    return clase_a_salida(svc.solicitar_cancelacion(clase_id, datos.instructor))


@router.post("/{clase_id}/cancelacion/resolver", response_model=ClaseOut,
             summary="Aprobar o rechazar la cancelación (Administrador)",
             description="Si se aprueba, las reservas se cancelan sin falta y se borra la lista "
                         "de espera. Si se rechaza, la clase sigue igual. Reglas: RN-30, RN-31.",
             responses={**_400, **_404, **_409})
def resolver_cancelacion(clase_id: ClaseId, decision: DecisionIn, svc: Servicio):
    return clase_a_salida(svc.resolver_cancelacion(clase_id, decision.aprobada))


@router.post("/{clase_id}/reservas", response_model=ResultadoReservaOut, status_code=201,
             summary="Reservar un lugar",
             description="El socio necesita membresía activa, un plan que incluya la clase y "
                         "no tener sanción. Si no hay lugar, entra a la lista de espera. "
                         "Reglas: RN-11, RN-13, RN-19, RN-24, RN-26.",
             responses={**_400, **_404, **_409, **_422})
def reservar(clase_id: ClaseId, datos: SocioIn, svc: Servicio):
    resultado = svc.reservar(clase_id, datos.socio_id)
    tipo = "RESERVA_CONFIRMADA" if isinstance(resultado, Reserva) else "EN_LISTA_DE_ESPERA"
    return ResultadoReservaOut(
        resultado=tipo, id=resultado.id, clase=clase_a_salida(svc.obtener(clase_id))
    )


@router.post("/{clase_id}/reservas/{reserva_id}/cancelar", response_model=ClaseOut,
             summary="Cancelar una reserva",
             description="Con menos de 1 hora de anticipación cuenta como falta. "
                         "Reglas: RN-15, RN-16.",
             responses={**_404, **_409})
def cancelar_reserva(clase_id: ClaseId, reserva_id: ReservaId, svc: Servicio):
    return clase_a_salida(svc.cancelar_reserva(clase_id, reserva_id))


@router.post("/{clase_id}/oferta/confirmar", response_model=ReservaOut,
             summary="Confirmar un lugar ofrecido",
             description="Quien recibe la oferta tiene 15 minutos para confirmar. Regla: RN-20.",
             responses={**_400, **_404, **_409, **_422})
def confirmar_oferta(clase_id: ClaseId, datos: SocioIn, svc: Servicio):
    r = svc.confirmar_oferta(clase_id, datos.socio_id)
    return ReservaOut(id=r.id, socio_id=r.socio_id, creada_en=r.creada_en, estado=r.estado.value)
