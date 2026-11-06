from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio_clases
from src.api.schemas import (
    ClaseIn,
    ClaseOut,
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
_409 = {409: {"model": ErrorOut, "description": "Clase iniciada, reserva repetida u oferta inválida"}}
_422 = {422: {"model": ErrorOut, "description": "Regla de negocio violada (RN-xx)"}}
_400 = {400: {"model": ErrorOut, "description": "Formato de la solicitud inválido"}}


def _con_etiqueta(svc: ServicioDeClases, clase, socio_id: str | None) -> ClaseOut:
    return clase_a_salida(clase, svc.etiqueta(clase, socio_id) if socio_id else None)


@router.post("", response_model=ClaseOut, status_code=201, summary="Crear una clase",
             responses={**_400, **_422})
def crear_clase(datos: ClaseIn, svc: Servicio):
    return clase_a_salida(svc.crear_clase(
        datos.nombre, datos.categoria, datos.inicio, datos.capacidad,
        instructor=datos.instructor, salon=datos.salon,
    ))


@router.get("", response_model=list[ClaseOut], summary="Catálogo de clases",
            description="Con `socio_id` agrega la etiqueta de cada clase para ese socio (RN-14).",
            responses={**_404})
def listar_clases(svc: Servicio, socio_id: str | None = None):
    return [_con_etiqueta(svc, c, socio_id) for c in svc.listar()]


@router.post("/procesar-reloj", response_model=ResumenRelojOut,
             summary="Ejecutar el reloj del sistema",
             description="Expira ofertas (RN-20) y aplica la tolerancia de retraso (RN-17, RN-21). "
                         "Lo dispara una tarea programada; no hay un proceso interno que lo llame.",
             responses={**_400})
def procesar_reloj(svc: Servicio, datos: RelojIn | None = None):
    r = svc.procesar_reloj(datos.ahora if datos else None)
    return ResumenRelojOut(
        ofertas_expiradas=r.ofertas_expiradas, lugares_ofrecidos=r.lugares_ofrecidos,
        no_shows=r.no_shows, lugares_asignados=r.lugares_asignados,
    )


@router.get("/{clase_id}", response_model=ClaseOut, summary="Consultar una clase",
            responses={**_404})
def obtener_clase(clase_id: str, svc: Servicio, socio_id: str | None = None):
    return _con_etiqueta(svc, svc.obtener(clase_id), socio_id)


@router.post("/{clase_id}/reservas", response_model=ResultadoReservaOut, status_code=201,
             summary="Reservar un lugar",
             description="Exige RN-13. Si no hay lugar, el socio entra a la lista de espera.",
             responses={**_400, **_404, **_409, **_422})
def reservar(clase_id: str, datos: SocioIn, svc: Servicio):
    resultado = svc.reservar(clase_id, datos.socio_id)
    tipo = "RESERVA_CONFIRMADA" if isinstance(resultado, Reserva) else "EN_LISTA_DE_ESPERA"
    return ResultadoReservaOut(
        resultado=tipo, id=resultado.id, clase=clase_a_salida(svc.obtener(clase_id))
    )


@router.post("/{clase_id}/reservas/{reserva_id}/cancelar", response_model=ClaseOut,
             summary="Cancelar una reserva",
             description="Con menos de 1 h cuenta como falta (RN-15, RN-16).",
             responses={**_404, **_409})
def cancelar_reserva(clase_id: str, reserva_id: str, svc: Servicio):
    return clase_a_salida(svc.cancelar_reserva(clase_id, reserva_id))


@router.post("/{clase_id}/oferta/confirmar", response_model=ReservaOut,
             summary="Confirmar la oferta de lugar",
             description="Se acepta hasta los 15 minutos exactos (RN-20).",
             responses={**_400, **_404, **_409, **_422})
def confirmar_oferta(clase_id: str, datos: SocioIn, svc: Servicio):
    r = svc.confirmar_oferta(clase_id, datos.socio_id)
    return ReservaOut(id=r.id, socio_id=r.socio_id, creada_en=r.creada_en, estado=r.estado.value)
