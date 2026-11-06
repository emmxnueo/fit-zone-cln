"""Adaptadores SQL de los puertos de `application/puertos.py` (DIP).

Cada operación abre su propia transacción: si algo falla, SQLAlchemy hace
rollback y no queda nada a medias.
"""
from __future__ import annotations

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from src.domain.entities import Plan, Socio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.state_machine import EstadoMembresia
from src.domain.value_objects import Cantidad, Dinero, LineaSolicitud

from .db import LineaRow, PlanRow, SocioRow, SolicitudRow

_VIGENTES = (EstadoMembresia.ACTIVA.value, EstadoMembresia.SUSPENDIDA.value)


def _a_socio(r: SocioRow) -> Socio:
    return Socio(r.id, r.nombre, es_premium=r.es_premium, activo=r.activo, ciudad=r.ciudad)


def _a_plan(r: PlanRow) -> Plan:
    return Plan(
        r.id, r.descripcion, Dinero.de(r.precio), r.cupo,
        habilitado=r.habilitado, duracion_meses=r.duracion_meses,
    )


def _a_solicitud(r: SolicitudRow) -> SolicitudDeMembresia:
    return SolicitudDeMembresia(
        id=r.id,
        socio_id=r.socio_id,
        fecha_solicitud=r.fecha_solicitud,
        validada=r.validada,
        cortesia_activa=r.cortesia_activa,
        referencia=r.referencia,
        estado=EstadoMembresia(r.estado),
        lineas=[
            LineaSolicitud(l.plan_id, Dinero.de(l.precio_unitario), Cantidad(l.cantidad))
            for l in r.lineas
        ],
    )


class RepositorioSociosSQL:
    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._sesiones = sesiones

    def obtener(self, socio_id: str) -> Socio | None:
        with self._sesiones() as s:
            fila = s.get(SocioRow, socio_id)
            return _a_socio(fila) if fila else None


class RepositorioPlanesSQL:
    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._sesiones = sesiones

    def obtener(self, plan_id: str) -> Plan | None:
        with self._sesiones() as s:
            fila = s.get(PlanRow, plan_id)
            return _a_plan(fila) if fila else None

    def todos(self) -> dict[str, Plan]:
        with self._sesiones() as s:
            return {f.id: _a_plan(f) for f in s.scalars(select(PlanRow))}


class RepositorioSolicitudesSQL:
    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._sesiones = sesiones

    def obtener(self, solicitud_id: str) -> SolicitudDeMembresia | None:
        with self._sesiones() as s:
            fila = s.scalars(
                select(SolicitudRow)
                .where(SolicitudRow.id == solicitud_id)
                .options(selectinload(SolicitudRow.lineas))
            ).first()
            return _a_solicitud(fila) if fila else None

    def guardar(self, solicitud: SolicitudDeMembresia) -> None:
        with self._sesiones.begin() as s:  # commit al salir, rollback si falla
            fila = s.get(SolicitudRow, solicitud.id)
            if fila is None:
                fila = SolicitudRow(id=solicitud.id)
                s.add(fila)
            fila.socio_id = solicitud.socio_id
            fila.fecha_solicitud = solicitud.fecha_solicitud
            fila.validada = solicitud.validada
            fila.cortesia_activa = solicitud.cortesia_activa
            fila.referencia = solicitud.referencia
            fila.estado = solicitud.estado.value
            fila.lineas = [  # delete-orphan borra las líneas anteriores
                LineaRow(
                    plan_id=l.plan_id,
                    precio_unitario=l.precio_unitario.monto,
                    cantidad=l.cantidad.valor,
                )
                for l in solicitud.lineas
            ]

    def listar(self) -> list[SolicitudDeMembresia]:
        with self._sesiones() as s:
            filas = s.scalars(
                select(SolicitudRow)
                .options(selectinload(SolicitudRow.lineas))
                .order_by(SolicitudRow.id)
            )
            return [_a_solicitud(f) for f in filas]

    def vigentes_del_socio(self, socio_id: str) -> int:
        """RN-03: membresías ACTIVA o SUSPENDIDA del socio."""
        with self._sesiones() as s:
            return s.scalar(
                select(func.count())
                .select_from(SolicitudRow)
                .where(SolicitudRow.socio_id == socio_id, SolicitudRow.estado.in_(_VIGENTES))
            ) or 0

    def vigentes_por_plan(self) -> dict[str, int]:
        """RN-39: ocupación de cupo por plan (solicitudes ACTIVA o SUSPENDIDA)."""
        with self._sesiones() as s:
            filas = s.execute(
                select(LineaRow.plan_id, func.count(distinct(LineaRow.solicitud_id)))
                .join(SolicitudRow, SolicitudRow.id == LineaRow.solicitud_id)
                .where(SolicitudRow.estado.in_(_VIGENTES))
                .group_by(LineaRow.plan_id)
            )
            return {plan_id: cuenta for plan_id, cuenta in filas}
