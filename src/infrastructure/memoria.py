"""Adaptadores en memoria de los puertos (para pruebas y para el paquete CSV).
Los repositorios PostgreSQL llegan en el paso de persistencia."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from src.domain.entities import Plan, Socio
from src.domain.events import EventoDeDominio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.state_machine import EstadoMembresia

_VIGENTES = (EstadoMembresia.ACTIVA, EstadoMembresia.SUSPENDIDA)


class RepositorioSociosMemoria:
    def __init__(self, socios: dict[str, Socio]) -> None:
        self._d = dict(socios)

    def obtener(self, socio_id: str) -> Socio | None:
        return self._d.get(socio_id)


class RepositorioPlanesMemoria:
    def __init__(self, planes: dict[str, Plan]) -> None:
        self._d = dict(planes)

    def obtener(self, plan_id: str) -> Plan | None:
        return self._d.get(plan_id)

    def todos(self) -> dict[str, Plan]:
        return dict(self._d)


class RepositorioSolicitudesMemoria:
    def __init__(self, solicitudes: dict[str, SolicitudDeMembresia] | None = None) -> None:
        self._d = dict(solicitudes or {})

    def obtener(self, solicitud_id: str) -> SolicitudDeMembresia | None:
        return self._d.get(solicitud_id)

    def guardar(self, solicitud: SolicitudDeMembresia) -> None:
        self._d[solicitud.id] = solicitud

    def listar(self) -> list[SolicitudDeMembresia]:
        return list(self._d.values())

    def vigentes_del_socio(self, socio_id: str) -> int:
        """RN-03: cuenta membresías ACTIVA o SUSPENDIDA (congelada sigue siendo suya)."""
        return sum(1 for s in self._d.values() if s.socio_id == socio_id and s.estado in _VIGENTES)

    def vigentes_por_plan(self) -> dict[str, int]:
        """RN-39: ocupación de cupo por plan (solicitudes ACTIVA o SUSPENDIDA)."""
        cuenta: dict[str, int] = defaultdict(int)
        for s in self._d.values():
            if s.estado in _VIGENTES:
                for plan_id in {l.plan_id for l in s.lineas}:
                    cuenta[plan_id] += 1
        return dict(cuenta)


class PublicadorEnMemoria:
    """Publica Domain Events a suscriptores y guarda un registro de lo publicado."""

    def __init__(self) -> None:
        self.publicados: list[EventoDeDominio] = []
        self._suscriptores: dict[type, list[Callable]] = defaultdict(list)

    def suscribir(self, tipo: type, manejador: Callable[[EventoDeDominio], None]) -> None:
        self._suscriptores[tipo].append(manejador)

    def publicar(self, eventos: list[EventoDeDominio]) -> None:
        for e in eventos:
            self.publicados.append(e)
            for manejador in self._suscriptores.get(type(e), []):
                manejador(e)
