"""Adaptador del puerto Reloj. El dominio trabaja con hora local sin zona:
"ese día" (RN-18) y "mes calendario" (RN-26) son conceptos locales del gimnasio."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

_MONTERREY = timezone(timedelta(hours=-6))  # sin horario de verano desde 2022


class RelojDelSistema:
    def ahora(self) -> datetime:
        return datetime.now(_MONTERREY).replace(tzinfo=None)
