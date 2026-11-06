"""Ejecuta el paquete del PIA y escribe la evidencia en docs/evidencia/.

Uso:  python -m src.infrastructure.ejecutar_paquete
"""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from src.application.ejecutor_paquete import ejecutar_casos, ejecutar_transiciones
from src.application.servicio import ServicioDeMembresias

from .csv_loader import DATA_DIR, cargar_paquete, leer_csv
from .memoria import (
    PublicadorEnMemoria,
    RepositorioPlanesMemoria,
    RepositorioSociosMemoria,
    RepositorioSolicitudesMemoria,
)


def fabrica_servicio() -> ServicioDeMembresias:
    """Servicio con estado nuevo: recarga el paquete completo desde los CSV."""
    p = cargar_paquete()
    return ServicioDeMembresias(
        RepositorioSociosMemoria(p.socios), RepositorioPlanesMemoria(p.planes),
        RepositorioSolicitudesMemoria(p.solicitudes), PublicadorEnMemoria(),
    )


def _escribir(ruta: Path, filas: list) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(filas[0])))
        w.writeheader()
        w.writerows(asdict(x) for x in filas)


def main(salida: Path | None = None) -> None:
    salida = salida or Path(__file__).resolve().parents[2] / "docs" / "evidencia"
    casos = ejecutar_casos(fabrica_servicio(), leer_csv("casos_prueba.csv", DATA_DIR))
    trans = ejecutar_transiciones(fabrica_servicio, leer_csv("transiciones_prueba.csv", DATA_DIR))
    _escribir(salida / "resultados_casos.csv", casos)
    _escribir(salida / "resultados_transiciones.csv", trans)
    print(f"{len(casos)} casos y {len(trans)} transiciones -> {salida}")


if __name__ == "__main__":
    main()
