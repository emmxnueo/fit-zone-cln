"""Ejecuta los casos del paquete del PIA (casos_prueba.csv y
transiciones_prueba.csv) sobre el servicio y devuelve los resultados.

Cada transición se ejecuta sobre un estado nuevo (fábrica de servicio) porque
20 socios tienen dos solicitudes y chocarían entre sí por la RN-03.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.domain.errors import ErrorDeDominio

from .servicio import ServicioDeMembresias


@dataclass(frozen=True)
class ResultadoCaso:
    caso_id: str
    operacion_id: str
    tipo_prueba: str
    resultado: str  # CUMPLE / NO_CUMPLE
    motivos: str
    total_mxn: str


@dataclass(frozen=True)
class ResultadoTransicion:
    caso_id: str
    operacion_id: str
    accion: str
    estado_inicial: str
    estado_final: str
    eventos: str
    error: str
    codigo_http: int
    regla: str
    mensaje: str


def ejecutar_casos(svc: ServicioDeMembresias, casos: list[dict]) -> list[ResultadoCaso]:
    resultados = []
    for c in casos:
        if c["tipo_prueba"] == "validar_operacion":
            ev = svc.evaluar_procesable(c["operacion_id"])
        elif c["tipo_prueba"] == "evaluar_beneficio":
            ev = svc.evaluar_beneficio(c["operacion_id"])
        else:
            raise ValueError(f"tipo_prueba desconocido: {c['tipo_prueba']}")
        total = svc.obtener(c["operacion_id"]).total.monto
        resultados.append(ResultadoCaso(
            c["caso_id"], c["operacion_id"], c["tipo_prueba"],
            "CUMPLE" if ev.cumple else "NO_CUMPLE", ";".join(ev.motivos), str(total),
        ))
    return resultados


def aplicar_accion(svc: ServicioDeMembresias, solicitud_id: str, accion: str) -> None:
    """Traduce las acciones del paquete a las del BRD (Anexo B)."""
    if accion == "aprobar":
        svc.activar(solicitud_id)
    elif accion in ("completar", "saltar_estado"):
        svc.vencer(solicitud_id)  # desde SOLICITADA es una transición ilegal (409)
    elif accion == "cancelar":
        svc.cancelar(solicitud_id)
    elif accion == "repetir_aprobacion":
        svc.activar(solicitud_id)
        svc.activar(solicitud_id)  # la segunda debe rechazarse (409)
    else:
        raise ValueError(f"accion_sugerida desconocida: {accion}")


def ejecutar_transiciones(
    fabrica: Callable[[], ServicioDeMembresias], transiciones: list[dict]
) -> list[ResultadoTransicion]:
    resultados = []
    for t in transiciones:
        svc = fabrica()
        sid = t["operacion_id"]
        error = None
        try:
            aplicar_accion(svc, sid, t["accion_sugerida"])
        except ErrorDeDominio as e:
            error = e
        eventos = [e.nombre for e in svc.publicador.publicados]  # type: ignore[attr-defined]
        resultados.append(ResultadoTransicion(
            t["caso_id"], sid, t["accion_sugerida"], t["estado_inicial"],
            svc.obtener(sid).estado.value, ";".join(eventos),
            type(error).__name__ if error else "",
            error.codigo_http if error else 200,
            (error.regla or "") if error else "",
            error.mensaje if error else "",
        ))
    return resultados
