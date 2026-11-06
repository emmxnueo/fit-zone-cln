"""Domain Events de la membresía, las reservas y las sanciones (BRD sección 13)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class EventoDeDominio:
    socio_id: str
    solicitud_id: str = ""
    clase_id: str = ""
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


@dataclass(frozen=True, kw_only=True)
class ReservaConfirmada(EventoDeDominio):
    reserva_id: str = ""


@dataclass(frozen=True, kw_only=True)
class SocioEnListaDeEspera(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class ReservaCancelada(EventoDeDominio):
    reserva_id: str = ""


@dataclass(frozen=True, kw_only=True)
class CancelacionTardiaRegistrada(EventoDeDominio):
    reserva_id: str = ""


@dataclass(frozen=True, kw_only=True)
class NoShowRegistrado(EventoDeDominio):
    reserva_id: str = ""


@dataclass(frozen=True, kw_only=True)
class LugarOfrecido(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class OfertaExpirada(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class LugarAsignado(EventoDeDominio):
    reserva_id: str = ""


@dataclass(frozen=True, kw_only=True)
class FaltaRegistrada(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class SancionAplicada(EventoDeDominio):
    pass
