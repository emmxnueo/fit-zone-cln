"""Adaptadores SQL de los puertos de `application/puertos.py` (DIP).

Cada operación abre su propia transacción: si algo falla, SQLAlchemy hace
rollback y no queda nada a medias.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, distinct, func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from src.domain.clase import Clase, EntradaListaEspera, EstadoEntrada, Reserva
from src.domain.entities import Plan, Socio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.specifications import CategoriaClase
from src.domain.state_machine import EstadoClase, EstadoMembresia, EstadoReserva
from src.domain.value_objects import Cantidad, Dinero, Falta, LineaSolicitud, MotivoFalta

from .db import (
    CancelacionClaseRow,
    ClaseRow,
    EntradaEsperaRow,
    FaltaRow,
    IngresoRow,
    LineaRow,
    PlanRow,
    ReservaRow,
    SancionRow,
    SocioRow,
    SolicitudRow,
)

_VIGENTES = (EstadoMembresia.ACTIVA.value, EstadoMembresia.SUSPENDIDA.value)


def _a_socio(r: SocioRow, faltas: list[FaltaRow], sancion: SancionRow | None) -> Socio:
    return Socio(
        r.id, r.nombre, es_premium=r.es_premium, activo=r.activo, ciudad=r.ciudad,
        faltas=[
            Falta(f.clase_id, f.momento, MotivoFalta(f.motivo), f.consumida) for f in faltas
        ],
        sancion_hasta=sancion.hasta if sancion else None,
    )


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


def _a_clase(r: ClaseRow) -> Clase:
    return Clase(
        r.id, r.nombre, CategoriaClase(r.categoria), r.inicio, r.capacidad,
        instructor=r.instructor, salon=r.salon,
        reservas=[
            Reserva(x.id, x.socio_id, x.creada_en, EstadoReserva(x.estado)) for x in r.reservas
        ],
        lista_espera=[
            EntradaListaEspera(
                x.id, x.socio_id, x.orden, x.registrada_en, EstadoEntrada(x.estado), x.ofertada_en
            )
            for x in r.lista_espera
        ],
        estado=EstadoClase(r.cancelacion.estado) if r.cancelacion else EstadoClase.PROGRAMADA,
    )


class RepositorioSociosSQL:
    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._sesiones = sesiones

    def obtener(self, socio_id: str) -> Socio | None:
        with self._sesiones() as s:
            fila = s.get(SocioRow, socio_id)
            if fila is None:
                return None
            faltas = s.scalars(
                select(FaltaRow).where(FaltaRow.socio_id == socio_id).order_by(FaltaRow.id)
            ).all()
            return _a_socio(fila, list(faltas), s.get(SancionRow, socio_id))

    def guardar(self, socio: Socio) -> None:
        """Solo persiste lo que cambia en el Socio: su historial de faltas y su sanción."""
        with self._sesiones.begin() as s:
            s.execute(delete(FaltaRow).where(FaltaRow.socio_id == socio.id))
            s.add_all(
                FaltaRow(socio_id=socio.id, clase_id=f.clase_id, momento=f.momento,
                         motivo=f.motivo.value, consumida=f.consumida)
                for f in socio.faltas
            )
            if socio.sancion_hasta is not None:
                s.merge(SancionRow(socio_id=socio.id, hasta=socio.sancion_hasta))


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

    def tiene_activa(self, socio_id: str) -> bool:
        """RN-13: una membresía congelada no permite reservar ni ingresar."""
        with self._sesiones() as s:
            return (s.scalar(
                select(func.count())
                .select_from(SolicitudRow)
                .where(
                    SolicitudRow.socio_id == socio_id,
                    SolicitudRow.estado == EstadoMembresia.ACTIVA.value,
                )
            ) or 0) > 0

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


class RepositorioClasesSQL:
    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._sesiones = sesiones

    def _consulta(self):
        return select(ClaseRow).options(
            selectinload(ClaseRow.reservas), selectinload(ClaseRow.lista_espera),
            selectinload(ClaseRow.cancelacion),
        )

    def obtener(self, clase_id: str) -> Clase | None:
        with self._sesiones() as s:
            fila = s.scalars(self._consulta().where(ClaseRow.id == clase_id)).first()
            return _a_clase(fila) if fila else None

    def listar(self) -> list[Clase]:
        with self._sesiones() as s:
            return [_a_clase(f) for f in s.scalars(self._consulta().order_by(ClaseRow.inicio, ClaseRow.id))]

    def guardar(self, clase: Clase) -> None:
        with self._sesiones.begin() as s:  # commit al salir, rollback si falla
            fila = s.get(ClaseRow, clase.id)
            if fila is None:
                fila = ClaseRow(id=clase.id)
                s.add(fila)
            fila.nombre = clase.nombre
            fila.categoria = clase.categoria.value
            fila.inicio = clase.inicio
            fila.capacidad = clase.capacidad
            fila.instructor = clase.instructor
            fila.salon = clase.salon
            if clase.estado == EstadoClase.PROGRAMADA:
                fila.cancelacion = None  # delete-orphan borra la solicitud rechazada
            elif fila.cancelacion is None:
                fila.cancelacion = CancelacionClaseRow(estado=clase.estado.value)
            else:
                fila.cancelacion.estado = clase.estado.value
            reservas = {r.id: r for r in fila.reservas}
            for r in clase.reservas:
                if r.id in reservas:
                    reservas[r.id].estado = r.estado.value
                else:
                    fila.reservas.append(ReservaRow(
                        id=r.id, socio_id=r.socio_id, creada_en=r.creada_en, estado=r.estado.value
                    ))
            entradas = {e.id: e for e in fila.lista_espera}
            for e in clase.lista_espera:
                if e.id in entradas:
                    entradas[e.id].estado = e.estado.value
                    entradas[e.id].ofertada_en = e.ofertada_en
                else:
                    fila.lista_espera.append(EntradaEsperaRow(
                        id=e.id, socio_id=e.socio_id, orden=e.orden,
                        registrada_en=e.registrada_en, estado=e.estado.value,
                        ofertada_en=e.ofertada_en,
                    ))


class RepositorioIngresosSQL:
    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._sesiones = sesiones

    def registrar(self, socio_id: str, momento: datetime) -> None:
        with self._sesiones.begin() as s:
            s.add(IngresoRow(socio_id=socio_id, momento=momento))

    def presentes_el(self, dia: date) -> set[str]:
        """RN-18: presente es tener un ingreso registrado ese día."""
        desde = datetime.combine(dia, time.min)
        with self._sesiones() as s:
            return set(s.scalars(
                select(IngresoRow.socio_id).where(
                    IngresoRow.momento >= desde, IngresoRow.momento < desde + timedelta(days=1)
                )
            ))

    def entre(self, desde: date, hasta: date) -> list[datetime]:
        """RN-35: momentos de los ingresos del rango, con ambas fechas incluidas."""
        inicio = datetime.combine(desde, time.min)
        fin = datetime.combine(hasta, time.min) + timedelta(days=1)
        with self._sesiones() as s:
            return list(s.scalars(
                select(IngresoRow.momento).where(
                    IngresoRow.momento >= inicio, IngresoRow.momento < fin
                )
            ))
