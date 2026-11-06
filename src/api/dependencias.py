"""Inyección de dependencias de FastAPI. Para pruebas se reemplaza con
`app.dependency_overrides[get_servicio]`."""
from functools import lru_cache

from src.application.servicio import ServicioDeMembresias
from src.infrastructure.composicion import crear_servicio_en_memoria


@lru_cache
def _servicio_global() -> ServicioDeMembresias:
    return crear_servicio_en_memoria()


def get_servicio() -> ServicioDeMembresias:
    return _servicio_global()
