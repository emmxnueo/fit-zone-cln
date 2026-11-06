"""Entidades de referencia usadas por la solicitud de membresía."""
from __future__ import annotations

from dataclasses import dataclass

from .value_objects import Dinero


@dataclass
class Socio:
    id: str
    nombre: str
    es_premium: bool = False  # equivale a es_preferente del paquete (Anexo B)
    activo: bool = True
    ciudad: str = ""


@dataclass
class Plan:
    id: str
    descripcion: str
    precio: Dinero
    cupo: int  # cupo de contratación (capacidad_o_stock del paquete, RN-39)
    habilitado: bool = True
    duracion_meses: int = 1  # la duración es un dato, no un tipo (supuesto del BRD)
