"""Composición de dependencias: arma los servicios de aplicación con adaptadores.

Si hay DATABASE_URL se usa PostgreSQL; si no, memoria (pruebas y desarrollo
rápido). El dominio y la aplicación no cambian en ninguno de los dos casos (DIP).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.application.clases import ServicioDeClases
from src.application.puertos import RepositorioClases, Reloj
from src.application.reportes import ServicioDeReportes
from src.application.servicio import ServicioDeMembresias
from src.domain.clase import Clase
from src.domain.specifications import CategoriaClase

from .csv_loader import DATA_DIR, cargar_paquete
from .db import PlanRow, SocioRow, crear_fabrica_sesiones, crear_motor
from .memoria import (
    PublicadorEnMemoria,
    RepositorioClasesMemoria,
    RepositorioIngresosMemoria,
    RepositorioPlanesMemoria,
    RepositorioSociosMemoria,
    RepositorioSolicitudesMemoria,
)
from .reloj import RelojDelSistema
from .repositorios_sql import (
    RepositorioClasesSQL,
    RepositorioIngresosSQL,
    RepositorioPlanesSQL,
    RepositorioSociosSQL,
    RepositorioSolicitudesSQL,
)


@dataclass(frozen=True)
class Servicios:
    """Los módulos comparten repositorios y publicador."""

    membresias: ServicioDeMembresias
    clases: ServicioDeClases
    reportes: ServicioDeReportes


def sembrar_clases_si_vacio(repo: RepositorioClases, reloj: Reloj) -> None:
    """El paquete del PIA no trae clases: estas son datos de demostración para
    mañana. La capacidad de 2 en Yoga permite ver la lista de espera."""
    if repo.listar():
        return
    manana = reloj.ahora().date() + timedelta(days=1)
    ejemplos = [
        ("FIT-K001", "Yoga", CategoriaClase.ESTANDAR, time(7), 2, "Ana Ruiz", "Salón 1"),
        ("FIT-K002", "Spinning", CategoriaClase.ESTANDAR, time(9), 15, "Luis Vega", "Salón 2"),
        ("FIT-K003", "HIIT Pro", CategoriaClase.PREMIUM, time(18), 10, "Sara Mena", "Salón 1"),
    ]
    for id_, nombre, categoria, hora, capacidad, instructor, salon in ejemplos:
        repo.guardar(Clase(
            id_, nombre, categoria, datetime.combine(manana, hora), capacidad,
            instructor=instructor, salon=salon,
        ))


def crear_servicios_en_memoria(
    directorio: Path = DATA_DIR, con_solicitudes: bool = True, reloj: Reloj | None = None
) -> Servicios:
    """Socios y planes siempre vienen del paquete; las 60 solicitudes de
    ejemplo y las clases solo si `con_solicitudes` (datos de demostración)."""
    p = cargar_paquete(directorio)
    reloj = reloj or RelojDelSistema()
    socios = RepositorioSociosMemoria(p.socios)
    solicitudes = RepositorioSolicitudesMemoria(p.solicitudes if con_solicitudes else {})
    clases = RepositorioClasesMemoria()
    ingresos = RepositorioIngresosMemoria()
    publicador = PublicadorEnMemoria()
    if con_solicitudes:
        sembrar_clases_si_vacio(clases, reloj)
    return Servicios(
        ServicioDeMembresias(socios, RepositorioPlanesMemoria(p.planes), solicitudes, publicador),
        ServicioDeClases(socios, solicitudes, clases, ingresos, publicador, reloj),
        ServicioDeReportes(clases, ingresos),
    )


def crear_servicio_en_memoria(
    directorio: Path = DATA_DIR, con_solicitudes: bool = True
) -> ServicioDeMembresias:
    return crear_servicios_en_memoria(directorio, con_solicitudes).membresias


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


def crear_servicios_sql(
    url: str, directorio: Path = DATA_DIR, con_solicitudes: bool = True,
    reloj: Reloj | None = None,
) -> Servicios:
    sesiones = crear_fabrica_sesiones(crear_motor(url))
    sembrar_si_vacia(sesiones, directorio, con_solicitudes)
    reloj = reloj or RelojDelSistema()
    socios = RepositorioSociosSQL(sesiones)
    solicitudes = RepositorioSolicitudesSQL(sesiones)
    clases = RepositorioClasesSQL(sesiones)
    ingresos = RepositorioIngresosSQL(sesiones)
    publicador = PublicadorEnMemoria()
    if con_solicitudes:
        sembrar_clases_si_vacio(clases, reloj)
    return Servicios(
        ServicioDeMembresias(socios, RepositorioPlanesSQL(sesiones), solicitudes, publicador),
        ServicioDeClases(socios, solicitudes, clases, ingresos, publicador, reloj),
        ServicioDeReportes(clases, ingresos),
    )


def crear_servicio_sql(
    url: str, directorio: Path = DATA_DIR, con_solicitudes: bool = True
) -> ServicioDeMembresias:
    return crear_servicios_sql(url, directorio, con_solicitudes).membresias


def crear_servicios(con_solicitudes: bool = True) -> Servicios:
    """Punto de entrada de la API: PostgreSQL si hay DATABASE_URL, memoria si no."""
    url = os.getenv("DATABASE_URL")
    if url:
        return crear_servicios_sql(url, con_solicitudes=con_solicitudes)
    return crear_servicios_en_memoria(con_solicitudes=con_solicitudes)


def crear_servicio(con_solicitudes: bool = True) -> ServicioDeMembresias:
    return crear_servicios(con_solicitudes).membresias
