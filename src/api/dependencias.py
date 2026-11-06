"""Inyección de dependencias de FastAPI. Para pruebas se reemplaza con
`app.dependency_overrides` con `get_servicio`, `get_servicio_clases` y
`get_servicio_reportes`."""
from functools import lru_cache

from src.application.clases import ServicioDeClases
from src.application.reportes import ServicioDeReportes
from src.application.servicio import ServicioDeMembresias
from src.infrastructure.composicion import Servicios, crear_servicios


@lru_cache
def _servicios_globales() -> Servicios:
    return crear_servicios()  # PostgreSQL si hay DATABASE_URL; memoria si no


def get_servicio() -> ServicioDeMembresias:
    return _servicios_globales().membresias


def get_servicio_clases() -> ServicioDeClases:
    return _servicios_globales().clases


def get_servicio_reportes() -> ServicioDeReportes:
    return _servicios_globales().reportes
