"""Patrón Specification (ADR-001): reglas de negocio como objetos combinables
con AND (&), OR (|) y NOT (~)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

from .entities import Plan, Socio
from .value_objects import Dinero

if TYPE_CHECKING:  # evita import circular con el agregado
    from .solicitud import SolicitudDeMembresia


@dataclass(frozen=True)
class ContextoSolicitud:
    """Todo lo que las Specifications necesitan para evaluar una solicitud."""

    solicitud: "SolicitudDeMembresia"
    socio: Socio
    planes: Mapping[str, Plan] = field(default_factory=dict)
    ocupacion_por_plan: Mapping[str, int] = field(default_factory=dict)
    membresias_activas_del_socio: int = 0


class Specification(ABC):
    @abstractmethod
    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool: ...

    def and_(self, otra: "Specification") -> "Specification":
        return _And(self, otra)

    def or_(self, otra: "Specification") -> "Specification":
        return _Or(self, otra)

    def not_(self) -> "Specification":
        return _Not(self)

    __and__ = and_
    __or__ = or_
    __invert__ = not_

    def __repr__(self) -> str:
        return type(self).__name__


class _And(Specification):
    def __init__(self, a: Specification, b: Specification) -> None:
        self.a, self.b = a, b

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return self.a.is_satisfied_by(ctx) and self.b.is_satisfied_by(ctx)

    def __repr__(self) -> str:
        return f"({self.a!r} AND {self.b!r})"


class _Or(Specification):
    def __init__(self, a: Specification, b: Specification) -> None:
        self.a, self.b = a, b

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return self.a.is_satisfied_by(ctx) or self.b.is_satisfied_by(ctx)

    def __repr__(self) -> str:
        return f"({self.a!r} OR {self.b!r})"


class _Not(Specification):
    def __init__(self, a: Specification) -> None:
        self.a = a

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return not self.a.is_satisfied_by(ctx)

    def __repr__(self) -> str:
        return f"NOT {self.a!r}"


# --- Specifications simples -------------------------------------------------
class SocioActivo(Specification):
    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return ctx.socio.activo


class SolicitudConLineas(Specification):
    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return len(ctx.solicitud.lineas) >= 1


class SolicitudValidada(Specification):
    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return ctx.solicitud.validada


class SocioPremium(Specification):
    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return ctx.socio.es_premium


class TotalMinimo(Specification):
    def __init__(self, minimo: Dinero) -> None:
        self.minimo = minimo

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return ctx.solicitud.total >= self.minimo


class CortesiaActiva(Specification):
    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return ctx.solicitud.cortesia_activa


class PlanesHabilitados(Specification):
    """RN-38: todos los planes de la solicitud deben estar habilitados."""

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return all(
            (p := ctx.planes.get(l.plan_id)) is not None and p.habilitado
            for l in ctx.solicitud.lineas
        )


class CupoDisponible(Specification):
    """RN-39: cada plan de la solicitud tiene cupo de contratación libre."""

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return all(
            (p := ctx.planes.get(l.plan_id)) is not None
            and ctx.ocupacion_por_plan.get(l.plan_id, 0) < p.cupo
            for l in ctx.solicitud.lineas
        )


class SinMembresiaActiva(Specification):
    """RN-03: un socio solo puede tener una membresía activa."""

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return ctx.membresias_activas_del_socio == 0


# --- Specifications compuestas (reglas del BRD) -----------------------------
class SolicitudProcesable(Specification):
    """RN-37: socio activo AND al menos una línea AND validada."""

    def __init__(self) -> None:
        self._spec = SocioActivo() & SolicitudConLineas() & SolicitudValidada()

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return self._spec.is_satisfied_by(ctx)


class BeneficioDeReferencia(Specification):
    """RN-40: socio Premium AND total >= 1500 MXN AND NOT cortesía activa."""

    UMBRAL = Dinero.de("1500")

    def __init__(self) -> None:
        self._spec = SocioPremium() & TotalMinimo(self.UMBRAL) & ~CortesiaActiva()

    def is_satisfied_by(self, ctx: ContextoSolicitud) -> bool:
        return self._spec.is_satisfied_by(ctx)
