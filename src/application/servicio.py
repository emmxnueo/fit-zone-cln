"""Casos de uso del módulo de solicitud de membresía.

Cada caso de uso: carga el agregado, ejecuta el comando de dominio, persiste y
publica los Domain Events. Las reglas viven en el dominio, no aquí (SRP).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

from src.domain.events import EventoDeDominio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.state_machine import EstadoMembresia
from src.domain.specifications import (
    BeneficioDeReferencia,
    ContextoSolicitud,
    SocioActivo,
    SolicitudConLineas,
    SolicitudValidada,
    Specification,
)

from .errors import NoEncontrado
from .puertos import (
    PublicadorDeEventos,
    RepositorioPlanes,
    RepositorioSocios,
    RepositorioSolicitudes,
)


@dataclass(frozen=True)
class Evaluacion:
    cumple: bool
    motivos: list[str] = field(default_factory=list)  # condiciones que fallaron


_CONDICIONES_PROCESABLE: list[tuple[str, Specification]] = [
    ("socio_inactivo", SocioActivo()),
    ("sin_lineas", SolicitudConLineas()),
    ("sin_validacion", SolicitudValidada()),
]


class ServicioDeMembresias:
    def __init__(
        self,
        socios: RepositorioSocios,
        planes: RepositorioPlanes,
        solicitudes: RepositorioSolicitudes,
        publicador: PublicadorDeEventos,
    ) -> None:
        self.socios = socios
        self.planes = planes
        self.solicitudes = solicitudes
        self.publicador = publicador

    # --- consultas ----------------------------------------------------------
    def obtener(self, solicitud_id: str) -> SolicitudDeMembresia:
        solicitud = self.solicitudes.obtener(solicitud_id)
        if solicitud is None:
            raise NoEncontrado(f"La solicitud {solicitud_id} no existe")
        return solicitud

    def evaluar_procesable(self, solicitud_id: str) -> Evaluacion:
        """RN-37. Devuelve además qué condiciones fallaron (útil para la API)."""
        solicitud = self.obtener(solicitud_id)
        ctx = self._contexto(solicitud)
        motivos = [n for n, spec in _CONDICIONES_PROCESABLE if not spec.is_satisfied_by(ctx)]
        return Evaluacion(solicitud.puede_procesarse(ctx), motivos)

    def evaluar_beneficio(self, solicitud_id: str) -> Evaluacion:
        """RN-40."""
        solicitud = self.obtener(solicitud_id)
        ctx = self._contexto(solicitud)
        cumple = solicitud.aplica_beneficio_de_referencia(ctx)
        motivos = []
        if not cumple:
            if not ctx.socio.es_premium:
                motivos.append("socio_no_premium")
            if solicitud.total < BeneficioDeReferencia.UMBRAL:
                motivos.append("total_menor_a_1500")
            if solicitud.cortesia_activa:
                motivos.append("cortesia_activa")
        return Evaluacion(cumple, motivos)

    def listar(self, estado: EstadoMembresia | None = None) -> list[SolicitudDeMembresia]:
        todas = self.solicitudes.listar()
        return [s for s in todas if estado is None or s.estado == estado]

    def eventos(self) -> list[EventoDeDominio]:
        return self.publicador.listar()

    # --- comandos -----------------------------------------------------------
    def crear(
        self,
        socio_id: str,
        lineas: list[tuple[str, int]],
        validada: bool = False,
        cortesia_activa: bool = False,
        referencia: str = "",
        fecha: date | None = None,
    ) -> SolicitudDeMembresia:
        """Crea una solicitud en estado SOLICITADA. La arma completa antes de
        guardarla: si una línea es inválida (RN-38) no queda nada a medias."""
        if self.socios.obtener(socio_id) is None:
            raise NoEncontrado(f"El socio {socio_id} no existe")
        solicitud = SolicitudDeMembresia(
            id=f"SOL-{uuid4().hex[:8].upper()}", socio_id=socio_id,
            fecha_solicitud=fecha or date.today(), validada=validada,
            cortesia_activa=cortesia_activa, referencia=referencia,
        )
        for plan_id, cantidad in lineas:
            plan = self.planes.obtener(plan_id)
            if plan is None:
                raise NoEncontrado(f"El plan {plan_id} no existe")
            solicitud.agregar_linea(plan, cantidad)
        self.solicitudes.guardar(solicitud)
        return solicitud

    def activar(self, solicitud_id: str) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.activar(self._contexto(s)))

    def cancelar(self, solicitud_id: str) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.cancelar())

    def vencer(self, solicitud_id: str) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.vencer())

    def congelar(self, solicitud_id: str, aprobada: bool) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.congelar(aprobada))

    def descongelar(self, solicitud_id: str) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.descongelar())

    def renovar(self, solicitud_id: str, pago_confirmado: bool) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.renovar(pago_confirmado))

    def dar_de_baja(self, solicitud_id: str, aprobada: bool) -> SolicitudDeMembresia:
        return self._ejecutar(solicitud_id, lambda s: s.dar_de_baja(aprobada))

    # --- internos -----------------------------------------------------------
    def _ejecutar(self, solicitud_id, comando) -> SolicitudDeMembresia:
        solicitud = self.obtener(solicitud_id)
        comando(solicitud)  # si el dominio rechaza, nada se guarda ni se publica
        self.solicitudes.guardar(solicitud)
        self.publicador.publicar(solicitud.pull_events())
        return solicitud

    def _contexto(self, solicitud: SolicitudDeMembresia) -> ContextoSolicitud:
        socio = self.socios.obtener(solicitud.socio_id)
        if socio is None:
            raise NoEncontrado(f"El socio {solicitud.socio_id} no existe")
        return ContextoSolicitud(
            solicitud=solicitud,
            socio=socio,
            planes=self.planes.todos(),
            ocupacion_por_plan=self.solicitudes.vigentes_por_plan(),
            membresias_activas_del_socio=self.solicitudes.vigentes_del_socio(socio.id),
        )
