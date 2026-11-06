"""Aggregate Root: Clase, con sus reservas y su lista de espera (RN-11 a RN-24).

La clase protege su capacidad y el orden de la lista. Las operaciones que
dependen del tiempo reciben `ahora`: el dominio no lee el reloj.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Collection
from uuid import uuid4

from . import events as ev
from .errors import ConflictoDeEstado, ReglaDeNegocioViolada
from .specifications import (
    CategoriaClase,
    ContextoReserva,
    MembresiaVigente,
    PlanIncluyeCategoria,
    SinSancionActiva,
    SocioActivo,
)
from .state_machine import AccionReserva, EstadoReserva, siguiente_estado_reserva

ANTICIPACION_SIN_FALTA = timedelta(hours=1)  # RN-15, RN-16
TOLERANCIA_RETRASO = timedelta(minutes=10)  # RN-17
PLAZO_OFERTA = timedelta(minutes=15)  # RN-20


class EstadoEntrada(str, Enum):
    EN_ESPERA = "EN_ESPERA"
    OFERTADA = "OFERTADA"
    ASIGNADA = "ASIGNADA"
    EXPIRADA = "EXPIRADA"


@dataclass
class Reserva:
    id: str
    socio_id: str
    creada_en: datetime
    estado: EstadoReserva = EstadoReserva.CONFIRMADA


@dataclass
class EntradaListaEspera:
    id: str
    socio_id: str
    orden: int  # RN-19: solo el orden de registro decide
    registrada_en: datetime
    estado: EstadoEntrada = EstadoEntrada.EN_ESPERA
    ofertada_en: datetime | None = None


def exigir_elegibilidad(ctx: ContextoReserva) -> None:
    """RN-13: rechaza con la regla exacta que no se cumple."""
    if not (SocioActivo() & MembresiaVigente()).is_satisfied_by(ctx):
        raise ReglaDeNegocioViolada("Reservar exige una membresía vigente", "RN-13")
    if not PlanIncluyeCategoria().is_satisfied_by(ctx):
        raise ReglaDeNegocioViolada("El plan del socio no incluye esta categoría", "RN-13")
    if not SinSancionActiva().is_satisfied_by(ctx):
        raise ReglaDeNegocioViolada("El socio tiene una sanción activa", "RN-26")


@dataclass
class Clase:
    id: str
    nombre: str
    categoria: CategoriaClase
    inicio: datetime
    capacidad: int
    instructor: str = ""
    salon: str = ""
    reservas: list[Reserva] = field(default_factory=list)
    lista_espera: list[EntradaListaEspera] = field(default_factory=list)
    _eventos: list[ev.EventoDeDominio] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.capacidad < 1:
            raise ReglaDeNegocioViolada("La capacidad debe ser 1 o más", "RN-11")

    # --- consulta -----------------------------------------------------------
    @property
    def confirmadas(self) -> list[Reserva]:
        return [r for r in self.reservas if r.estado == EstadoReserva.CONFIRMADA]

    @property
    def en_espera(self) -> list[EntradaListaEspera]:
        """RN-19: socios que aún esperan, en orden FIFO."""
        return sorted(
            (e for e in self.lista_espera if e.estado == EstadoEntrada.EN_ESPERA),
            key=lambda e: e.orden,
        )

    @property
    def oferta_activa(self) -> EntradaListaEspera | None:
        """RN-22: hay como máximo una oferta activa por clase."""
        return next((e for e in self.lista_espera if e.estado == EstadoEntrada.OFERTADA), None)

    @property
    def lugares_libres(self) -> int:
        """RN-11: un lugar ofrecido sigue apartado hasta que la oferta se resuelva."""
        return self.capacidad - len(self.confirmadas) - (1 if self.oferta_activa else 0)

    def reserva(self, reserva_id: str) -> Reserva | None:
        return next((r for r in self.reservas if r.id == reserva_id), None)

    def pull_events(self) -> list[ev.EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos

    # --- comandos -----------------------------------------------------------
    def reservar(self, ctx: ContextoReserva) -> Reserva | EntradaListaEspera:
        """RN-11, RN-13. Sin lugar, o con socios esperando (RN-19), va a la lista."""
        socio_id = ctx.socio.id
        if ctx.ahora >= self.inicio:
            raise ConflictoDeEstado("La clase ya inició", "RN-13")
        if any(r.socio_id == socio_id for r in self.confirmadas):
            raise ConflictoDeEstado("El socio ya tiene una reserva en esta clase")
        if self._esta_en_lista(socio_id):
            raise ConflictoDeEstado("El socio ya está en la lista de espera", "RN-24")
        exigir_elegibilidad(ctx)
        if self.lugares_libres > 0 and not self.en_espera:
            return self._confirmar(socio_id, ctx.ahora)
        entrada = EntradaListaEspera(
            f"ESP-{uuid4().hex[:8].upper()}", socio_id,
            max((e.orden for e in self.lista_espera), default=0) + 1, ctx.ahora,
        )
        self.lista_espera.append(entrada)
        self._eventos.append(ev.SocioEnListaDeEspera(socio_id=socio_id, clase_id=self.id))
        self._ofrecer_siguiente(ctx.ahora)
        return entrada

    def cancelar_reserva(self, reserva: Reserva, ahora: datetime) -> None:
        """RN-15, RN-16: con menos de 1 h el lugar se libera y cuenta como falta."""
        tarde = self.inicio - ahora < ANTICIPACION_SIN_FALTA
        accion = AccionReserva.CANCELAR_TARDE if tarde else AccionReserva.CANCELAR
        nuevo = siguiente_estado_reserva(reserva.estado, accion)
        if ahora >= self.inicio:
            raise ConflictoDeEstado("La clase ya inició", "RN-17")
        reserva.estado = nuevo
        tipo = ev.CancelacionTardiaRegistrada if tarde else ev.ReservaCancelada
        self._eventos.append(tipo(socio_id=reserva.socio_id, clase_id=self.id, reserva_id=reserva.id))
        self._ofrecer_siguiente(ahora)

    def confirmar_oferta(self, ctx: ContextoReserva) -> Reserva:
        """RN-20: a los 15 minutos exactos todavía se acepta."""
        oferta = self.oferta_activa
        if oferta is None or oferta.socio_id != ctx.socio.id:
            raise ConflictoDeEstado("El socio no tiene una oferta activa", "RN-20")
        if self._oferta_vencida(oferta, ctx.ahora):
            raise ConflictoDeEstado("La oferta ya expiró", "RN-20")
        exigir_elegibilidad(ctx)
        oferta.estado = EstadoEntrada.ASIGNADA
        reserva = self._confirmar(oferta.socio_id, ctx.ahora)
        self._ofrecer_siguiente(ctx.ahora)
        return reserva

    def expirar_oferta(self, ahora: datetime) -> None:
        """RN-20, RN-23: la oferta vencida pasa al siguiente; si no hay, el lugar queda libre."""
        oferta = self.oferta_activa
        if oferta is not None and self._oferta_vencida(oferta, ahora):
            oferta.estado = EstadoEntrada.EXPIRADA
            self._eventos.append(ev.OfertaExpirada(socio_id=oferta.socio_id, clase_id=self.id))
        self._ofrecer_siguiente(ahora)

    def aplicar_tolerancia(
        self, ahora: datetime, presentes: Collection[str], asignables: Collection[str]
    ) -> None:
        """RN-17, RN-21, RN-23. `presentes` tienen ingreso el día de la clase (RN-18);
        `asignables` además siguen elegibles. A los 10 minutos exactos no se libera."""
        limite = self.inicio + TOLERANCIA_RETRASO
        if ahora <= limite:
            return
        for reserva in self.confirmadas:
            # Quien confirmó una oferta después del límite no llegó tarde a su reserva.
            if reserva.socio_id in presentes or reserva.creada_en > limite:
                continue
            reserva.estado = siguiente_estado_reserva(reserva.estado, AccionReserva.MARCAR_NO_SHOW)
            self._eventos.append(ev.NoShowRegistrado(
                socio_id=reserva.socio_id, clase_id=self.id, reserva_id=reserva.id
            ))
            self._asignar_a_presente(ahora, asignables)

    # --- internos -----------------------------------------------------------
    def _esta_en_lista(self, socio_id: str) -> bool:
        return any(
            e.socio_id == socio_id and e.estado in (EstadoEntrada.EN_ESPERA, EstadoEntrada.OFERTADA)
            for e in self.lista_espera
        )

    @staticmethod
    def _oferta_vencida(oferta: EntradaListaEspera, ahora: datetime) -> bool:
        return ahora > oferta.ofertada_en + PLAZO_OFERTA

    def _confirmar(self, socio_id: str, ahora: datetime) -> Reserva:
        reserva = Reserva(f"RES-{uuid4().hex[:8].upper()}", socio_id, ahora)
        self.reservas.append(reserva)
        self._eventos.append(ev.ReservaConfirmada(
            socio_id=socio_id, clase_id=self.id, reserva_id=reserva.id
        ))
        return reserva

    def _ofrecer_siguiente(self, ahora: datetime) -> None:
        """RN-20, RN-22. Con la clase iniciada los lugares solo se asignan por RN-21."""
        if ahora >= self.inicio or self.oferta_activa or self.lugares_libres < 1:
            return
        espera = self.en_espera
        if espera:
            espera[0].estado = EstadoEntrada.OFERTADA
            espera[0].ofertada_en = ahora
            self._eventos.append(ev.LugarOfrecido(socio_id=espera[0].socio_id, clase_id=self.id))

    def _asignar_a_presente(self, ahora: datetime, asignables: Collection[str]) -> None:
        """RN-21: el primero de la lista que esté presente y elegible, sin oferta."""
        entrada = next((e for e in self.en_espera if e.socio_id in asignables), None)
        if entrada is None:
            return  # RN-23: el lugar queda libre, no es un error
        entrada.estado = EstadoEntrada.ASIGNADA
        reserva = Reserva(f"RES-{uuid4().hex[:8].upper()}", entrada.socio_id, ahora)
        self.reservas.append(reserva)
        self._eventos.append(ev.LugarAsignado(
            socio_id=entrada.socio_id, clase_id=self.id, reserva_id=reserva.id
        ))
