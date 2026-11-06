"""Casos de uso de clases, reservas, lista de espera, ingresos y sanciones.

Igual que `servicio.py`: carga el agregado, ejecuta el comando de dominio,
persiste y publica. Las faltas llegan al Socio por eventos (ADR-003).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.domain import events as ev
from src.domain.clase import Clase, EntradaListaEspera, Reserva
from src.domain.entities import Socio
from src.domain.errors import ReglaDeNegocioViolada
from src.domain.specifications import (
    CategoriaClase,
    ContextoReserva,
    ElegibleParaReservar,
    PlanIncluyeCategoria,
)
from src.domain.value_objects import Falta, MotivoFalta

from .errors import NoEncontrado
from .puertos import (
    PublicadorDeEventos,
    RepositorioClases,
    RepositorioIngresos,
    RepositorioSocios,
    RepositorioSolicitudes,
    Reloj,
)

_MOTIVOS = {
    ev.NoShowRegistrado: MotivoFalta.NO_SHOW,
    ev.CancelacionTardiaRegistrada: MotivoFalta.CANCELACION_TARDIA,
}


@dataclass(frozen=True)
class ResumenReloj:
    ofertas_expiradas: int
    lugares_ofrecidos: int
    no_shows: int
    lugares_asignados: int


class ServicioDeClases:
    def __init__(
        self,
        socios: RepositorioSocios,
        solicitudes: RepositorioSolicitudes,
        clases: RepositorioClases,
        ingresos: RepositorioIngresos,
        publicador: PublicadorDeEventos,
        reloj: Reloj,
    ) -> None:
        self.socios = socios
        self.solicitudes = solicitudes
        self.clases = clases
        self.ingresos = ingresos
        self.publicador = publicador
        self.reloj = reloj
        for tipo in _MOTIVOS:
            publicador.suscribir(tipo, self._registrar_falta)

    # --- consultas ----------------------------------------------------------
    def obtener(self, clase_id: str) -> Clase:
        clase = self.clases.obtener(clase_id)
        if clase is None:
            raise NoEncontrado(f"La clase {clase_id} no existe")
        return clase

    def listar(self) -> list[Clase]:
        return self.clases.listar()

    def listar_socios(self) -> list[Socio]:
        return self.socios.listar()

    def obtener_socio(self, socio_id: str) -> Socio:
        socio = self.socios.obtener(socio_id)
        if socio is None:
            raise NoEncontrado(f"El socio {socio_id} no existe")
        return socio

    def etiqueta(self, clase: Clase, socio_id: str) -> str:
        """RN-14: cómo ve el socio la clase en el catálogo."""
        ctx = self._contexto(clase, self.obtener_socio(socio_id), self.reloj.ahora())
        if PlanIncluyeCategoria().is_satisfied_by(ctx):
            return "Incluida en tu membresía"
        return "Costo adicional / Exclusiva Plan Premium"

    # --- comandos -----------------------------------------------------------
    def crear_clase(
        self, nombre: str, categoria: CategoriaClase, inicio: datetime, capacidad: int,
        instructor: str = "", salon: str = "",
    ) -> Clase:
        clase = Clase(
            f"CLA-{uuid4().hex[:8].upper()}", nombre, categoria, inicio, capacidad,
            instructor=instructor, salon=salon,
        )
        self.clases.guardar(clase)
        return clase

    def reservar(self, clase_id: str, socio_id: str) -> Reserva | EntradaListaEspera:
        clase = self.obtener(clase_id)
        socio = self.obtener_socio(socio_id)
        resultado = clase.reservar(self._contexto(clase, socio, self.reloj.ahora()))
        self._guardar(clase)
        return resultado

    def cancelar_reserva(self, clase_id: str, reserva_id: str) -> Clase:
        clase = self.obtener(clase_id)
        reserva = clase.reserva(reserva_id)
        if reserva is None:
            raise NoEncontrado(f"La reserva {reserva_id} no existe")
        clase.cancelar_reserva(reserva, self.reloj.ahora())
        self._guardar(clase)
        return clase

    def confirmar_oferta(self, clase_id: str, socio_id: str) -> Reserva:
        clase = self.obtener(clase_id)
        socio = self.obtener_socio(socio_id)
        reserva = clase.confirmar_oferta(self._contexto(clase, socio, self.reloj.ahora()))
        self._guardar(clase)
        return reserva

    def solicitar_cancelacion(self, clase_id: str, instructor: str) -> Clase:
        clase = self.obtener(clase_id)
        clase.solicitar_cancelacion(instructor, self.reloj.ahora())
        self._guardar(clase)
        return clase

    def resolver_cancelacion(self, clase_id: str, aprobada: bool) -> Clase:
        """RN-30: lo resuelve el Administrador."""
        clase = self.obtener(clase_id)
        if aprobada:
            clase.aprobar_cancelacion(self.reloj.ahora())
        else:
            clase.rechazar_cancelacion()
        self._guardar(clase)
        return clase

    def registrar_ingreso(self, socio_id: str) -> datetime:
        """RN-05: solo con membresía vigente. La sanción no bloquea el acceso (RN-26)."""
        self.obtener_socio(socio_id)
        if not self.solicitudes.tiene_activa(socio_id):
            raise ReglaDeNegocioViolada("El socio no tiene membresía vigente", "RN-05")
        momento = self.reloj.ahora()
        self.ingresos.registrar(socio_id, momento)
        return momento

    def procesar_reloj(self, ahora: datetime | None = None) -> ResumenReloj:
        """Actor Sistema (reloj): expira ofertas y aplica la tolerancia de retraso."""
        ahora = ahora or self.reloj.ahora()
        cuenta: dict[type, int] = {}
        for clase in self.clases.listar():
            clase.expirar_oferta(ahora)
            presentes = self.ingresos.presentes_el(clase.inicio.date())
            asignables = {
                e.socio_id for e in clase.en_espera
                if e.socio_id in presentes and self._sigue_elegible(clase, e.socio_id, ahora)
            }
            clase.aplicar_tolerancia(ahora, presentes, asignables)
            eventos = self._guardar(clase)
            for e in eventos:
                cuenta[type(e)] = cuenta.get(type(e), 0) + 1
        return ResumenReloj(
            cuenta.get(ev.OfertaDeLugarExpirada, 0), cuenta.get(ev.LugarOfrecidoASocio, 0),
            cuenta.get(ev.NoShowRegistrado, 0),
            cuenta.get(ev.ReservaConfirmada, 0),  # en el reloj solo confirma RN-21
        )

    # --- internos -----------------------------------------------------------
    def _guardar(self, clase: Clase) -> list[ev.EventoDeDominio]:
        eventos = clase.pull_events()
        if eventos:
            self.clases.guardar(clase)
            self.publicador.publicar(eventos)
        return eventos

    def _registrar_falta(self, evento: ev.EventoDeDominio) -> None:
        """RN-25: suscriptor de NoShowRegistrado y CancelacionTardiaRegistrada."""
        socio = self.obtener_socio(evento.socio_id)
        socio.registrar_falta(Falta(evento.clase_id, self._momento_de_falta(evento), _MOTIVOS[type(evento)]))
        self.socios.guardar(socio)
        self.publicador.publicar(socio.pull_events())

    def _momento_de_falta(self, evento: ev.EventoDeDominio) -> datetime:
        """El mes de la falta (RN-26) es el de la clase, aunque el reloj corra después."""
        return self.obtener(evento.clase_id).inicio

    def _sigue_elegible(self, clase: Clase, socio_id: str, ahora: datetime) -> bool:
        ctx = self._contexto(clase, self.obtener_socio(socio_id), ahora)
        return ElegibleParaReservar().is_satisfied_by(ctx)

    def _contexto(self, clase: Clase, socio: Socio, ahora: datetime) -> ContextoReserva:
        return ContextoReserva(
            socio=socio,
            categoria=clase.categoria,
            membresia_vigente=self.solicitudes.tiene_activa(socio.id),
            ahora=ahora,
        )
