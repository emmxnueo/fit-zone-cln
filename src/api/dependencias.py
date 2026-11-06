"""Inyección de dependencias de FastAPI. Para pruebas se reemplaza con
`app.dependency_overrides[get_servicio]`."""
from functools import lru_cache

from src.application.servicio import ServicioDeMembresias
from src.infrastructure.composicion import crear_servicio


@lru_cache
def _servicio_global() -> ServicioDeMembresias:
    return crear_servicio()  # PostgreSQL si hay DATABASE_URL; memoria si no


def get_servicio() -> ServicioDeMembresias:
    return _servicio_global()
