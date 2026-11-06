"""Contratos de la API (entrada y salida). Los importes viajan como texto
decimal ("1500.00") para no perder precisión con float."""
from datetime import date, datetime

from pydantic import BaseModel, Field, NaiveDatetime, StrictBool, StrictInt

from src.domain.clase import Clase
from src.domain.entities import Socio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.specifications import CategoriaClase
from src.domain.state_machine import acciones_permitidas


# --- entrada ----------------------------------------------------------------
class LineaIn(BaseModel):
    plan_id: str = Field(min_length=1, examples=["FIT-P001"])
    cantidad: StrictInt = Field(
        examples=[3], description="Periodos contratados. Entero >= 1 (RN-38)."
    )


class SolicitudIn(BaseModel):
    socio_id: str = Field(min_length=1, examples=["FIT-C001"])
    lineas: list[LineaIn] = Field(default_factory=list)
    validada: StrictBool = Field(
        default=False, description="Validación registrada por Recepción o Administrador."
    )
    cortesia_activa: StrictBool = Field(
        default=False, description="Cortesía vigente autorizada por el Administrador."
    )
    referencia: str = ""


class DecisionIn(BaseModel):
    aprobada: StrictBool = Field(
        description="Resolución del Administrador (RN-09, RN-10, RN-30)."
    )


class PagoIn(BaseModel):
    pago_confirmado: StrictBool = Field(description="Pago confirmado (RN-08).")


class ClaseIn(BaseModel):
    nombre: str = Field(min_length=1, examples=["Yoga"])
    categoria: CategoriaClase
    inicio: NaiveDatetime = Field(
        examples=["2026-12-01T18:00:00"], description="Hora local de Monterrey, sin zona."
    )
    capacidad: StrictInt = Field(examples=[20], description="Entero >= 1 (RN-11).")
    instructor: str = ""
    salon: str = ""


class SocioIn(BaseModel):
    socio_id: str = Field(min_length=1, examples=["FIT-C001"])


class CancelacionClaseIn(BaseModel):
    instructor: str = Field(min_length=1, examples=["Ana Ruiz"])


class RelojIn(BaseModel):
    ahora: NaiveDatetime | None = Field(
        default=None,
        description="Momento a evaluar. Si se omite, se usa el reloj del sistema; "
                    "sirve para demostrar la tolerancia y la expiración sin esperar.",
    )


# --- salida -----------------------------------------------------------------
class LineaOut(BaseModel):
    plan_id: str
    precio_unitario_mxn: str
    cantidad: int
    subtotal_mxn: str


class SolicitudOut(BaseModel):
    id: str
    socio_id: str
    fecha_solicitud: date
    estado: str
    validada: bool
    cortesia_activa: bool
    referencia: str
    total_mxn: str
    lineas: list[LineaOut]
    acciones_permitidas: list[str]


class EvaluacionOut(BaseModel):
    cumple: bool
    motivos: list[str]


class PlanOut(BaseModel):
    id: str
    descripcion: str
    precio_mxn: str
    cupo: int
    habilitado: bool
    duracion_meses: int


class ReservaOut(BaseModel):
    id: str
    socio_id: str
    creada_en: datetime
    estado: str


class EntradaEsperaOut(BaseModel):
    id: str
    socio_id: str
    orden: int
    registrada_en: datetime
    estado: str
    ofertada_en: datetime | None


class ClaseOut(BaseModel):
    id: str
    nombre: str
    categoria: str
    inicio: datetime
    capacidad: int
    instructor: str
    salon: str
    estado: str
    lugares_libres: int
    etiqueta: str | None = Field(
        default=None, description="Solo si se consulta con `socio_id` (RN-14)."
    )
    reservas: list[ReservaOut]
    lista_espera: list[EntradaEsperaOut]


class ResultadoReservaOut(BaseModel):
    resultado: str = Field(description="RESERVA_CONFIRMADA o EN_LISTA_DE_ESPERA (RN-13).")
    id: str
    clase: ClaseOut


class ResumenRelojOut(BaseModel):
    ofertas_expiradas: int
    lugares_ofrecidos: int
    no_shows: int
    lugares_asignados: int


class FaltaOut(BaseModel):
    clase_id: str
    momento: datetime
    motivo: str
    consumida: bool


class SocioOut(BaseModel):
    id: str
    nombre: str
    es_premium: bool
    activo: bool
    faltas: list[FaltaOut]
    sancion_hasta: datetime | None


class IngresoOut(BaseModel):
    socio_id: str
    momento: datetime


class IngresosPorHoraOut(BaseModel):
    hora: int
    ingresos: int


class IngresosPorDiaOut(BaseModel):
    dia: str
    ingresos: int


class AfluenciaOut(BaseModel):
    desde: date
    hasta: date
    total: int
    por_hora: list[IngresosPorHoraOut]
    por_dia: list[IngresosPorDiaOut]


class DemandaOut(BaseModel):
    clase_id: str
    nombre: str
    inicio: datetime
    capacidad: int
    reservas_confirmadas: int
    ocupacion_pct: str = Field(description='Porcentaje como texto decimal, por ejemplo "100.00".')
    en_lista_de_espera: int


class EventoOut(BaseModel):
    evento: str
    solicitud_id: str
    clase_id: str
    socio_id: str
    socios_a_notificar: list[str] = []
    ocurrido_en: datetime


class ErrorOut(BaseModel):
    detail: str
    regla: str | None = None
    error: str | None = None


def a_salida(s: SolicitudDeMembresia) -> SolicitudOut:
    return SolicitudOut(
        id=s.id,
        socio_id=s.socio_id,
        fecha_solicitud=s.fecha_solicitud,
        estado=s.estado.value,
        validada=s.validada,
        cortesia_activa=s.cortesia_activa,
        referencia=s.referencia,
        total_mxn=str(s.total.monto),
        lineas=[
            LineaOut(
                plan_id=l.plan_id,
                precio_unitario_mxn=str(l.precio_unitario.monto),
                cantidad=l.cantidad.valor,
                subtotal_mxn=str(l.subtotal.monto),
            )
            for l in s.lineas
        ],
        acciones_permitidas=[a.value for a in acciones_permitidas(s.estado)],
    )


def clase_a_salida(c: Clase, etiqueta: str | None = None) -> ClaseOut:
    return ClaseOut(
        id=c.id,
        nombre=c.nombre,
        categoria=c.categoria.value,
        inicio=c.inicio,
        capacidad=c.capacidad,
        instructor=c.instructor,
        salon=c.salon,
        estado=c.estado.value,
        lugares_libres=c.lugares_libres,
        etiqueta=etiqueta,
        reservas=[
            ReservaOut(id=r.id, socio_id=r.socio_id, creada_en=r.creada_en, estado=r.estado.value)
            for r in c.reservas
        ],
        lista_espera=[
            EntradaEsperaOut(
                id=e.id, socio_id=e.socio_id, orden=e.orden, registrada_en=e.registrada_en,
                estado=e.estado.value, ofertada_en=e.ofertada_en,
            )
            for e in sorted(c.lista_espera, key=lambda e: e.orden)
        ],
    )


def socio_a_salida(s: Socio) -> SocioOut:
    return SocioOut(
        id=s.id,
        nombre=s.nombre,
        es_premium=s.es_premium,
        activo=s.activo,
        faltas=[
            FaltaOut(clase_id=f.clase_id, momento=f.momento, motivo=f.motivo.value,
                     consumida=f.consumida)
            for f in s.faltas
        ],
        sancion_hasta=s.sancion_hasta,
    )
