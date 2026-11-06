"""Composición de dependencias: arma el servicio de aplicación con adaptadores.

Si hay DATABASE_URL se usa PostgreSQL; si no, memoria (pruebas y desarrollo
rápido). El dominio y la aplicación no cambian en ninguno de los dos casos (DIP).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.application.servicio import ServicioDeMembresias

from .csv_loader import DATA_DIR, cargar_paquete
from .db import PlanRow, SocioRow, crear_fabrica_sesiones, crear_motor
from .memoria import (
    PublicadorEnMemoria,
    RepositorioPlanesMemoria,
    RepositorioSociosMemoria,
    RepositorioSolicitudesMemoria,
)
from .repositorios_sql import (
    RepositorioPlanesSQL,
    RepositorioSociosSQL,
    RepositorioSolicitudesSQL,
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


def sembrar_si_vacia(
    sesiones: sessionmaker[Session], directorio: Path = DATA_DIR, con_solicitudes: bool = True
) -> None:
    """Carga el paquete CSV solo la primera vez (si la tabla de socios está vacía)."""
    with sesiones() as s:
        hay_datos = (s.scalar(select(func.count()).select_from(SocioRow)) or 0) > 0
    if hay_datos:
        return
    p = cargar_paquete(directorio)
    with sesiones.begin() as s:
        s.add_all(
            SocioRow(id=x.id, nombre=x.nombre, es_premium=x.es_premium,
                     activo=x.activo, ciudad=x.ciudad)
            for x in p.socios.values()
        )
        s.add_all(
            PlanRow(id=x.id, descripcion=x.descripcion, precio=x.precio.monto,
                    cupo=x.cupo, habilitado=x.habilitado, duracion_meses=x.duracion_meses)
            for x in p.planes.values()
        )
    if con_solicitudes:
        repo = RepositorioSolicitudesSQL(sesiones)
        for solicitud in p.solicitudes.values():
            repo.guardar(solicitud)


def crear_servicio_sql(
    url: str, directorio: Path = DATA_DIR, con_solicitudes: bool = True
) -> ServicioDeMembresias:
    sesiones = crear_fabrica_sesiones(crear_motor(url))
    sembrar_si_vacia(sesiones, directorio, con_solicitudes)
    return ServicioDeMembresias(
        RepositorioSociosSQL(sesiones),
        RepositorioPlanesSQL(sesiones),
        RepositorioSolicitudesSQL(sesiones),
        PublicadorEnMemoria(),
    )


def crear_servicio(con_solicitudes: bool = True) -> ServicioDeMembresias:
    """Punto de entrada de la API: PostgreSQL si hay DATABASE_URL, memoria si no."""
    url = os.getenv("DATABASE_URL")
    if url:
        return crear_servicio_sql(url, con_solicitudes=con_solicitudes)
    return crear_servicio_en_memoria(con_solicitudes=con_solicitudes)
