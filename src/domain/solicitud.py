"""Aggregate Root: SolicitudDeMembresia (RN-37 a RN-41).

Protege sus invariantes: el estado solo cambia mediante la máquina de estados,
y cada cambio registra un Domain Event que la capa de aplicación publica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import events as ev
from .entities import Plan
from .errors import (
    CupoAgotado,
    MembresiaActivaExistente,
    ReglaDeNegocioViolada,
)
from .specifications import (
    BeneficioDeReferencia,
    ContextoSolicitud,
    CupoDisponible,
    PlanesHabilitados,
    SinMembresiaActiva,
    SolicitudProcesable,
)
from .state_machine import AccionMembresia as Accion
from .state_machine import EstadoMembresia, siguiente_estado
from .value_objects import CERO, Cantidad, Dinero, LineaSolicitud


@dataclass
class SolicitudDeMembresia:
    id: str
    socio_id: str
    fecha_solicitud: date
    validada: bool = False  # `autorizado` del paquete (Anexo B)
    cortesia_activa: bool = False  # `promocion_activa` del paquete (Anexo B)
    referencia: str = ""
    estado: EstadoMembresia = EstadoMembresia.SOLICITADA
    lineas: list[LineaSolicitud] = field(default_factory=list)
    _eventos: list[ev.EventoDeDominio] = field(default_factory=list, repr=False)

    # --- consulta -----------------------------------------------------------
    @property
    def total(self) -> Dinero:
        """RN-38: Σ precio × cantidad, con Decimal."""
        total = CERO
        for linea in self.lineas:
            total = total + linea.subtotal
        return total

    def agregar_linea(self, plan: Plan, cantidad: int) -> None:
        """RN-38: la cantidad es un entero >= 1. La habilitación del plan se
        exige al activar (así se pueden cargar solicitudes con planes
        deshabilitados y rechazarlas con un error claro, Anexo B)."""
        self.lineas.append(LineaSolicitud(plan.id, plan.precio, Cantidad(cantidad)))

    def puede_procesarse(self, ctx: ContextoSolicitud) -> bool:
        return SolicitudProcesable().is_satisfied_by(ctx)

    def aplica_beneficio_de_referencia(self, ctx: ContextoSolicitud) -> bool:
        return BeneficioDeReferencia().is_satisfied_by(ctx)

    def pull_events(self) -> list[ev.EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos

    # --- comandos (cada uno pasa por la máquina de estados) -----------------
    def activar(self, ctx: ContextoSolicitud) -> None:
        nuevo = siguiente_estado(self.estado, Accion.ACTIVAR)  # 409 si no procede
        if not SinMembresiaActiva().is_satisfied_by(ctx):  # primero RN-03 (BPMN 12.1)
            raise MembresiaActivaExistente(
                "El socio ya tiene una membresía activa", "RN-03"
            )
        if not SolicitudProcesable().is_satisfied_by(ctx):
            raise ReglaDeNegocioViolada(
                "La solicitud no es procesable: socio inactivo, sin líneas o sin validar",
                "RN-37",
            )
        if not PlanesHabilitados().is_satisfied_by(ctx):
            raise ReglaDeNegocioViolada(
                "La solicitud incluye un plan deshabilitado o inexistente", "RN-38"
            )
        if not CupoDisponible().is_satisfied_by(ctx):
            raise CupoAgotado("Un plan de la solicitud no tiene cupo disponible", "RN-39")
        self.estado = nuevo
        self._registrar(ev.MembresiaActivada(
            solicitud_id=self.id, socio_id=self.socio_id, total_mxn=str(self.total.monto)
        ))

    def cancelar(self) -> None:
        self.estado = siguiente_estado(self.estado, Accion.CANCELAR)
        self._registrar(ev.SolicitudCancelada(solicitud_id=self.id, socio_id=self.socio_id))

    def congelar(self, aprobada_por_administrador: bool) -> None:
        nuevo = siguiente_estado(self.estado, Accion.CONGELAR)
        if not aprobada_por_administrador:
            raise ReglaDeNegocioViolada(
                "Congelar requiere solicitud aprobada por el Administrador", "RN-09"
            )
        self.estado = nuevo
        self._registrar(ev.MembresiaCongelada(solicitud_id=self.id, socio_id=self.socio_id))

    def descongelar(self) -> None:
        self.estado = siguiente_estado(self.estado, Accion.DESCONGELAR)
        self._registrar(ev.MembresiaDescongelada(solicitud_id=self.id, socio_id=self.socio_id))

    def vencer(self) -> None:
        self.estado = siguiente_estado(self.estado, Accion.VENCER)
        self._registrar(ev.MembresiaVencida(solicitud_id=self.id, socio_id=self.socio_id))

    def renovar(self, pago_confirmado: bool) -> None:
        nuevo = siguiente_estado(self.estado, Accion.RENOVAR)
        if not pago_confirmado:
            raise ReglaDeNegocioViolada("Renovar exige el pago confirmado", "RN-08")
        self.estado = nuevo
        self._registrar(ev.MembresiaRenovada(solicitud_id=self.id, socio_id=self.socio_id))

    def dar_de_baja(self, aprobada_por_administrador: bool) -> None:
        nuevo = siguiente_estado(self.estado, Accion.DAR_DE_BAJA)
        if not aprobada_por_administrador:
            raise ReglaDeNegocioViolada(
                "La baja requiere solicitud aprobada por el Administrador", "RN-10"
            )
        self.estado = nuevo
        self._registrar(ev.MembresiaDadaDeBaja(solicitud_id=self.id, socio_id=self.socio_id))

    def _registrar(self, evento: ev.EventoDeDominio) -> None:
        self._eventos.append(evento)
