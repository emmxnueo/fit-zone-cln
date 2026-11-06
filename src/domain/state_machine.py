"""Máquinas de estados de la membresía (RN-41), la reserva (RN-15 a RN-17) y la
clase (RN-29, RN-30).

Cualquier par (estado, acción) que no esté en su tabla se rechaza (409).
"""
from __future__ import annotations

from enum import Enum

from .errors import TransicionInvalida


class EstadoMembresia(str, Enum):
    SOLICITADA = "SOLICITADA"
    ACTIVA = "ACTIVA"
    SUSPENDIDA = "SUSPENDIDA"
    VENCIDA = "VENCIDA"
    CANCELADA = "CANCELADA"  # estado final


class AccionMembresia(str, Enum):
    ACTIVAR = "activar"
    CANCELAR = "cancelar"
    CONGELAR = "congelar"
    DESCONGELAR = "descongelar"
    VENCER = "vencer"
    RENOVAR = "renovar"
    DAR_DE_BAJA = "dar_de_baja"


E, A = EstadoMembresia, AccionMembresia

TRANSICIONES: dict[tuple[EstadoMembresia, AccionMembresia], EstadoMembresia] = {
    (E.SOLICITADA, A.ACTIVAR): E.ACTIVA,
    (E.SOLICITADA, A.CANCELAR): E.CANCELADA,
    (E.ACTIVA, A.CONGELAR): E.SUSPENDIDA,
    (E.SUSPENDIDA, A.DESCONGELAR): E.ACTIVA,
    (E.ACTIVA, A.VENCER): E.VENCIDA,
    (E.SUSPENDIDA, A.VENCER): E.VENCIDA,
    (E.VENCIDA, A.RENOVAR): E.ACTIVA,
    (E.ACTIVA, A.DAR_DE_BAJA): E.CANCELADA,
    (E.SUSPENDIDA, A.DAR_DE_BAJA): E.CANCELADA,
}


def siguiente_estado(estado: EstadoMembresia, accion: AccionMembresia) -> EstadoMembresia:
    try:
        return TRANSICIONES[(estado, accion)]
    except KeyError:
        verbo = accion.value.replace("_", " ")
        raise TransicionInvalida(
            f"No se puede {verbo} una membresía {estado.value.lower()}", "RN-41"
        ) from None


def acciones_permitidas(estado: EstadoMembresia) -> list[AccionMembresia]:
    return [a for (e, a) in TRANSICIONES if e == estado]


class EstadoReserva(str, Enum):
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"  # estados finales: CANCELADA, CANCELADA_TARDE, NO_SHOW
    CANCELADA_TARDE = "CANCELADA_TARDE"
    NO_SHOW = "NO_SHOW"


class AccionReserva(str, Enum):
    CANCELAR = "cancelar"
    CANCELAR_TARDE = "cancelar_tarde"
    MARCAR_NO_SHOW = "marcar_no_show"


TRANSICIONES_RESERVA: dict[tuple[EstadoReserva, AccionReserva], EstadoReserva] = {
    (EstadoReserva.CONFIRMADA, AccionReserva.CANCELAR): EstadoReserva.CANCELADA,
    (EstadoReserva.CONFIRMADA, AccionReserva.CANCELAR_TARDE): EstadoReserva.CANCELADA_TARDE,
    (EstadoReserva.CONFIRMADA, AccionReserva.MARCAR_NO_SHOW): EstadoReserva.NO_SHOW,
}


def siguiente_estado_reserva(estado: EstadoReserva, accion: AccionReserva) -> EstadoReserva:
    try:
        return TRANSICIONES_RESERVA[(estado, accion)]
    except KeyError:
        raise TransicionInvalida("Esta reserva ya no está confirmada", "RN-15") from None


class EstadoClase(str, Enum):
    PROGRAMADA = "PROGRAMADA"
    CANCELACION_SOLICITADA = "CANCELACION_SOLICITADA"
    CANCELADA = "CANCELADA"  # estado final


class AccionClase(str, Enum):
    SOLICITAR_CANCELACION = "solicitar_cancelacion"
    APROBAR_CANCELACION = "aprobar_cancelacion"
    RECHAZAR_CANCELACION = "rechazar_cancelacion"


TRANSICIONES_CLASE: dict[tuple[EstadoClase, AccionClase], EstadoClase] = {
    (EstadoClase.PROGRAMADA, AccionClase.SOLICITAR_CANCELACION): EstadoClase.CANCELACION_SOLICITADA,
    (EstadoClase.CANCELACION_SOLICITADA, AccionClase.APROBAR_CANCELACION): EstadoClase.CANCELADA,
    (EstadoClase.CANCELACION_SOLICITADA, AccionClase.RECHAZAR_CANCELACION): EstadoClase.PROGRAMADA,
}


def siguiente_estado_clase(estado: EstadoClase, accion: AccionClase) -> EstadoClase:
    try:
        return TRANSICIONES_CLASE[(estado, accion)]
    except KeyError:
        if accion == AccionClase.SOLICITAR_CANCELACION:
            raise TransicionInvalida(
                "La clase ya tiene una solicitud de cancelación o ya fue cancelada", "RN-29"
            ) from None
        raise TransicionInvalida(
            "La clase no tiene una solicitud de cancelación pendiente", "RN-30"
        ) from None
