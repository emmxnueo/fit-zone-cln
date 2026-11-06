"""Composición de dependencias: arma el servicio de aplicación con adaptadores.
Aquí se cambiará memoria por PostgreSQL sin tocar dominio ni aplicación (DIP)."""
from __future__ import annotations

from pathlib import Path

from src.application.servicio import ServicioDeMembresias

from .csv_loader import DATA_DIR, cargar_paquete
from .memoria import (
    PublicadorEnMemoria,
    RepositorioPlanesMemoria,
    RepositorioSociosMemoria,
    RepositorioSolicitudesMemoria,
)


def crear_servicio_en_memoria(
    directorio: Path = DATA_DIR, con_solicitudes: bool = True
) -> ServicioDeMembresias:
    """Socios y planes siempre vienen del paquete; las 60 solicitudes de
    ejemplo solo si `con_solicitudes` (datos de demostración)."""
    p = cargar_paquete(directorio)
    return ServicioDeMembresias(
        RepositorioSociosMemoria(p.socios),
        RepositorioPlanesMemoria(p.planes),
        RepositorioSolicitudesMemoria(p.solicitudes if con_solicitudes else {}),
        PublicadorEnMemoria(),
    )
