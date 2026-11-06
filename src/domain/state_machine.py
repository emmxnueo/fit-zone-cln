"""Máquina de estados de la membresía / solicitud de membresía (RN-41).

Cualquier par (estado, acción) que no esté en TRANSICIONES se rechaza (409).
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
        raise TransicionInvalida(
            f"No se puede '{accion.value}' desde {estado.value}", "RN-41"
        ) from None


def acciones_permitidas(estado: EstadoMembresia) -> list[AccionMembresia]:
    return [a for (e, a) in TRANSICIONES if e == estado]
