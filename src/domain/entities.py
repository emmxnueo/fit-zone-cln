"""Socio (registra faltas y sanciones, ADR-003) y Plan."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from . import events as ev
from .value_objects import Dinero, Falta

FALTAS_PARA_SANCION = 3  # RN-26
DURACION_SANCION = timedelta(days=7)  # RN-26


@dataclass
class Socio:
    id: str
    nombre: str
    es_premium: bool = False  # equivale a es_preferente del paquete (Anexo B)
    activo: bool = True
    ciudad: str = ""
    faltas: list[Falta] = field(default_factory=list)
    sancion_hasta: datetime | None = None
    _eventos: list[ev.EventoDeDominio] = field(default_factory=list, repr=False)

    def tiene_sancion_activa(self, ahora: datetime) -> bool:
        return self.sancion_hasta is not None and ahora < self.sancion_hasta

    def registrar_falta(self, falta: Falta) -> None:
        """RN-26 a RN-28: la tercera falta del mes calendario sanciona sin
        intervención del Administrador. Una sanción activa no se extiende."""
        self.faltas.append(falta)
        self._eventos.append(ev.FaltaRegistrada(socio_id=self.id, clase_id=falta.clase_id))
        if self.tiene_sancion_activa(falta.momento):
            return
        del_mes = [f for f in self.faltas if self._cuenta_para_sancion(f, falta.momento)]
        if len(del_mes) >= FALTAS_PARA_SANCION:
            self.faltas = [
                replace(f, consumida=True) if self._cuenta_para_sancion(f, falta.momento) else f
                for f in self.faltas
            ]
            self.sancion_hasta = falta.momento + DURACION_SANCION
            self._eventos.append(ev.SancionAplicada(socio_id=self.id, clase_id=falta.clase_id))

    def pull_events(self) -> list[ev.EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos

    @staticmethod
    def _cuenta_para_sancion(falta: Falta, momento: datetime) -> bool:
        return not falta.consumida and (falta.momento.year, falta.momento.month) == (
            momento.year, momento.month,
        )


@dataclass
class Plan:
    id: str
    descripcion: str
    precio: Dinero
    cupo: int  # cupo de contratación (capacidad_o_stock del paquete, RN-39)
    habilitado: bool = True
    duracion_meses: int = 1  # la duración es un dato, no un tipo (supuesto del BRD)
