"""Domain Events del ciclo de vida de la membresía (BRD sección 13)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class EventoDeDominio:
    solicitud_id: str
    socio_id: str
    ocurrido_en: datetime = field(default_factory=_ahora)

    @property
    def nombre(self) -> str:
        return type(self).__name__


@dataclass(frozen=True, kw_only=True)
class MembresiaActivada(EventoDeDominio):
    total_mxn: str = ""


@dataclass(frozen=True, kw_only=True)
class MembresiaCongelada(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class MembresiaDescongelada(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class MembresiaVencida(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class MembresiaRenovada(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class MembresiaDadaDeBaja(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class SolicitudCancelada(EventoDeDominio):
    pass
