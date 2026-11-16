from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencias import get_servicio_clases
from src.api.parametros import SocioId
from src.api.schemas import AltaSocioIn, ErrorOut, IngresoOut, SocioOut, socio_a_salida
from src.application.clases import ServicioDeClases
from src.domain.value_objects import FichaDeAlta

router = APIRouter(prefix="/socios", tags=["Socios"])

Servicio = Annotated[ServicioDeClases, Depends(get_servicio_clases)]

_404 = {404: {"model": ErrorOut, "description": "El socio no existe"}}
_400 = {400: {"model": ErrorOut, "description": "Faltan datos o tienen un formato incorrecto"}}
_422 = {422: {"model": ErrorOut, "description": "No se cumple una regla del negocio"}}


@router.get("", response_model=list[SocioOut], summary="Ver los socios")
def listar_socios(svc: Servicio):
    return [socio_a_salida(s) for s in svc.listar_socios()]


@router.post("", response_model=SocioOut, status_code=201, summary="Dar de alta a un socio",
             description="Recepción captura los datos del socio. Los menores de 16 años se "
                         "rechazan; con 16 o 17 se exigen el deslinde y el cuestionario de "
                         "salud. Después se crea su solicitud de membresía. Reglas: RN-01, RN-02.",
             responses={**_400, **_422})
def dar_de_alta(datos: AltaSocioIn, svc: Servicio):
    ficha = FichaDeAlta(
        datos.fecha_nacimiento, datos.correo, datos.telefono,
        datos.deslinde_firmado, datos.cuestionario_salud,
    )
    return socio_a_salida(svc.dar_de_alta_socio(datos.nombre, ficha, ciudad=datos.ciudad or ""))


@router.get("/{socio_id}", response_model=SocioOut, summary="Consultar las faltas y la sanción de un socio",
            description="Con 3 faltas en el mes, el socio no puede reservar por 7 días. "
                        "Reglas: RN-25 a RN-28.",
            responses={**_404})
def obtener_socio(socio_id: SocioId, svc: Servicio):
    return socio_a_salida(svc.obtener_socio(socio_id))


@router.post("/{socio_id}/ingresos", response_model=IngresoOut, status_code=201,
             summary="Registrar la entrada al gimnasio",
             description="Solo con membresía activa. Ese día el socio cuenta como presente. "
                         "Reglas: RN-05, RN-18.",
             responses={**_404, **_422})
def registrar_ingreso(socio_id: SocioId, svc: Servicio):
    return IngresoOut(socio_id=socio_id, momento=svc.registrar_ingreso(socio_id))
