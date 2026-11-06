"""Contratos de la API (entrada y salida). Los importes viajan como texto
decimal ("1500.00") para no perder precisión con float."""
from datetime import date, datetime

from pydantic import BaseModel, Field, StrictBool, StrictInt

from src.domain.solicitud import SolicitudDeMembresia
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
        description="Resolución del Administrador sobre la solicitud de excepción (RN-09, RN-10)."
    )


class PagoIn(BaseModel):
    pago_confirmado: StrictBool = Field(description="Pago confirmado (RN-08).")


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


class EventoOut(BaseModel):
    evento: str
    solicitud_id: str
    socio_id: str
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
