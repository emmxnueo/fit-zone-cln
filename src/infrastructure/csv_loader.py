"""Carga del paquete de datos del PIA (CSV UTF-8 con BOM) al modelo de dominio."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.domain.entities import Plan, Socio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.value_objects import Dinero

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# La duración es un dato en meses (supuesto del BRD): se deduce de la descripción.
_MESES = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}


@dataclass
class PaqueteDeDatos:
    socios: dict[str, Socio]
    planes: dict[str, Plan]
    solicitudes: dict[str, SolicitudDeMembresia]


def leer_csv(nombre: str, directorio: Path = DATA_DIR) -> list[dict[str, str]]:
    with open(directorio / nombre, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cargar_paquete(directorio: Path = DATA_DIR) -> PaqueteDeDatos:
    socios = {
        r["actor_id"]: Socio(
            r["actor_id"], r["nombre"], es_premium=r["es_preferente"] == "1",
            activo=r["activo"] == "1", ciudad=r["ciudad"],
        )
        for r in leer_csv("actores.csv", directorio)
    }
    planes = {
        r["recurso_id"]: Plan(
            r["recurso_id"], r["descripcion"], Dinero.de(r["precio_mxn"]),
            int(r["capacidad_o_stock"]), habilitado=r["habilitado"] == "1",
            duracion_meses=_MESES.get(r["descripcion"].split()[0], 1),
        )
        for r in leer_csv("catalogo.csv", directorio)
    }
    solicitudes = {
        r["operacion_id"]: SolicitudDeMembresia(
            id=r["operacion_id"], socio_id=r["actor_id"],
            fecha_solicitud=date.fromisoformat(r["fecha_solicitud"]),
            validada=r["autorizado"] == "1", cortesia_activa=r["promocion_activa"] == "1",
            referencia=r["referencia"],
        )
        for r in leer_csv("operaciones.csv", directorio)
    }
    for r in leer_csv("detalle_operaciones.csv", directorio):
        solicitudes[r["operacion_id"]].agregar_linea(planes[r["recurso_id"]], int(r["cantidad"]))
    return PaqueteDeDatos(socios, planes, solicitudes)
