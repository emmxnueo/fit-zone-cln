"""Table Module de los reportes (ADR-001): lecturas que agrupan datos y no
cambian estado, por eso no pasan por los agregados (RN-35, RN-36)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from src.domain.clase import Clase
from src.domain.errors import ReglaDeNegocioViolada

from .puertos import RepositorioClases, RepositorioIngresos

DIAS_DE_LA_SEMANA = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


@dataclass(frozen=True)
class ReporteAfluencia:
    desde: date
    hasta: date
    total: int
    por_hora: dict[int, int]  # siempre las 24 horas, en cero si no hay ingresos
    por_dia: dict[str, int]  # siempre los 7 días, de lunes a domingo


@dataclass(frozen=True)
class DemandaDeClase:
    clase_id: str
    nombre: str
    inicio: datetime
    capacidad: int
    reservas_confirmadas: int
    ocupacion_pct: Decimal
    en_lista_de_espera: int


def _agrupar(momentos: list[datetime], desde: date, hasta: date) -> ReporteAfluencia:
    horas = Counter(m.hour for m in momentos)
    dias = Counter(m.weekday() for m in momentos)
    return ReporteAfluencia(
        desde, hasta, len(momentos),
        {h: horas[h] for h in range(24)},
        {nombre: dias[i] for i, nombre in enumerate(DIAS_DE_LA_SEMANA)},
    )


def _demanda(clase: Clase) -> DemandaDeClase:
    confirmadas = len(clase.confirmadas)
    ocupacion = Decimal(confirmadas * 100) / clase.capacidad
    esperando = len(clase.en_espera) + (1 if clase.oferta_activa else 0)
    return DemandaDeClase(
        clase.id, clase.nombre, clase.inicio, clase.capacidad, confirmadas,
        ocupacion.quantize(Decimal("0.01"), ROUND_HALF_UP), esperando,
    )


class ServicioDeReportes:
    def __init__(self, clases: RepositorioClases, ingresos: RepositorioIngresos) -> None:
        self.clases = clases
        self.ingresos = ingresos

    def afluencia(self, desde: date, hasta: date) -> ReporteAfluencia:
        """RN-35: `hasta` es inclusivo. Sin ingresos, el reporte sale en ceros."""
        if hasta < desde:
            raise ReglaDeNegocioViolada("La fecha final es anterior a la inicial", "RN-35")
        return _agrupar(self.ingresos.entre(desde, hasta), desde, hasta)

    def demanda(self) -> list[DemandaDeClase]:
        """RN-36: de mayor a menor demanda, para decidir nuevos horarios (BPMN 12.6)."""
        return sorted(
            (_demanda(c) for c in self.clases.listar()),
            key=lambda d: (-d.ocupacion_pct, -d.en_lista_de_espera, d.inicio),
        )
