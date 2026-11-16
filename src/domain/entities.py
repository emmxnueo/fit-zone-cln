"""Socio (alta con edad y deslinde, RN-01 y RN-02; faltas y sanciones, ADR-003) y Plan."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from . import events as ev
from .errors import ReglaDeNegocioViolada
from .value_objects import Dinero, Falta, FichaDeAlta

FALTAS_PARA_SANCION = 3  # RN-26
DURACION_SANCION = timedelta(days=7)  # RN-26
EDAD_MINIMA = 16  # RN-01
MAYORIA_DE_EDAD = 18  # RN-02: con 16 o 17 se exige deslinde


@dataclass
class Socio:
    id: str
    nombre: str
    es_premium: bool = False  # equivale a es_preferente del paquete (Anexo B)
    activo: bool = True
    ciudad: str = ""
    faltas: list[Falta] = field(default_factory=list)
    sancion_hasta: datetime | None = None
    ficha: FichaDeAlta | None = None  # None en los socios del paquete del PIA
    _eventos: list[ev.EventoDeDominio] = field(default_factory=list, repr=False)

    @classmethod
    def dar_de_alta(
        cls, socio_id: str, nombre: str, ficha: FichaDeAlta, hoy: date,
        es_premium: bool = False, ciudad: str = "",
    ) -> "Socio":
        """BPMN 12.1: ¿Tiene 16 años cumplidos? (RN-01) y, con 16 o 17,
        deslinde y cuestionario de salud (RN-02)."""
        edad = ficha.edad_en(hoy)
        if edad < EDAD_MINIMA:
            raise ReglaDeNegocioViolada("El socio debe tener 16 años cumplidos", "RN-01")
        menor = edad < MAYORIA_DE_EDAD
        if menor and not ficha.documentacion_completa:
            raise ReglaDeNegocioViolada(
                "Con 16 o 17 años se exige el deslinde firmado y el cuestionario de salud",
                "RN-02",
            )
        socio = cls(socio_id, nombre, es_premium=es_premium, ciudad=ciudad, ficha=ficha)
        if menor:
            socio._eventos.append(ev.DeslindeFirmado(socio_id=socio_id))
        return socio

    def cumple_requisitos_de_edad(self, dia: date) -> bool:
        """RN-01 y RN-02 en `dia`. Los socios del paquete no traen edad: se aceptan."""
        if self.ficha is None:
            return True
        edad = self.ficha.edad_en(dia)
        return edad >= MAYORIA_DE_EDAD or (
            edad >= EDAD_MINIMA and self.ficha.documentacion_completa
        )

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
