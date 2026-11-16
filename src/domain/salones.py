"""Catálogo de salones (RN-11): la capacidad de una clase es fija por salón y
equipamiento, independiente del instructor y del horario."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import ReglaDeNegocioViolada


@dataclass(frozen=True)
class Salon:
    nombre: str
    capacidad: int


SALONES: dict[str, Salon] = {
    s.nombre: s for s in (Salon("Salón 1", 1), Salon("Salón 2", 5), Salon("Salón 3", 10))
}


def salon(nombre: str) -> Salon:
    """El salón del catálogo; si no existe, la clase no tiene capacidad definida."""
    try:
        return SALONES[nombre]
    except KeyError:
        raise ReglaDeNegocioViolada(f"El salón {nombre} no existe", "RN-11") from None
