"""Escenarios Gherkin de US-11 y US-15 (RN-01, RN-02) y compuertas de edad del BPMN 12.1."""
from datetime import date

import pytest

from src.domain import events as ev
from src.domain.entities import Socio
from src.domain.errors import ReglaDeNegocioViolada
from src.domain.state_machine import EstadoMembresia
from src.domain.value_objects import FichaDeAlta
from tests.unit.domain.helpers import contexto, solicitud

HOY = date(2026, 11, 16)


def ficha(edad, deslinde=False, cuestionario=False, cumple_hoy=False):
    nacimiento = date(HOY.year - edad, HOY.month, HOY.day if cumple_hoy else HOY.day - 1)
    return FichaDeAlta(nacimiento, "ana@correo.com", "8112345678", deslinde, cuestionario)


def alta(f):
    return Socio.dar_de_alta("FIT-C041", "Ana", f, HOY)


# --- Esquema del escenario de US-11 (los cuatro ejemplos) --------------------
def test_15_anos_se_rechaza_por_edad_minima():
    with pytest.raises(ReglaDeNegocioViolada) as e:
        alta(ficha(15, deslinde=True, cuestionario=True))
    assert e.value.regla == "RN-01" and e.value.codigo_http == 422


def test_16_anos_sin_deslinde_ni_cuestionario_se_rechaza():
    with pytest.raises(ReglaDeNegocioViolada) as e:
        alta(ficha(16))
    assert e.value.regla == "RN-02"


def test_17_anos_con_deslinde_y_cuestionario_se_acepta():
    socio = alta(ficha(17, deslinde=True, cuestionario=True))
    assert socio.ficha.edad_en(HOY) == 17
    assert [type(x) for x in socio.pull_events()] == [ev.DeslindeFirmado]


def test_18_anos_sin_deslinde_se_acepta_sin_evento_de_deslinde():
    socio = alta(ficha(18))
    assert socio.pull_events() == []


# --- Bordes ------------------------------------------------------------------
def test_el_dia_del_cumpleanos_ya_cuenta():
    assert ficha(16, cumple_hoy=True).edad_en(HOY) == 16
    assert alta(ficha(16, deslinde=True, cuestionario=True, cumple_hoy=True)).id == "FIT-C041"
    assert ficha(16, cumple_hoy=False).edad_en(date(2026, 11, 14)) == 15


def test_un_dia_antes_de_cumplir_16_se_rechaza():
    nacimiento = date(2010, 11, 17)  # cumple 16 mañana
    with pytest.raises(ReglaDeNegocioViolada) as e:
        alta(FichaDeAlta(nacimiento, "a@b.co", "8112345678", True, True))
    assert e.value.regla == "RN-01"


@pytest.mark.parametrize("deslinde,cuestionario", [(True, False), (False, True)])
def test_rn02_exige_ambos_documentos(deslinde, cuestionario):
    with pytest.raises(ReglaDeNegocioViolada) as e:
        alta(ficha(17, deslinde, cuestionario))
    assert e.value.regla == "RN-02"


# --- Activación: la compuerta de edad va antes de RN-03 (BPMN 12.1) ----------
def _contexto_de(socio, activas=0):
    ctx = contexto(activas=activas)
    return type(ctx)(ctx.solicitud, socio, ctx.planes, ctx.ocupacion_por_plan, activas)


def test_activar_rechaza_menor_sin_deslinde_antes_que_rn03():
    # 16 años a la fecha de la solicitud (1/10/2026), sin documentos: dato cargado a mano
    socio = Socio("S1", "Ana", ficha=FichaDeAlta(date(2010, 1, 1), "a@b.co", "8112345678"))
    s = solicitud()
    ctx = _contexto_de(socio, activas=1)
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.activar(type(ctx)(s, socio, ctx.planes, {}, 1))
    assert e.value.regla == "RN-02"
    assert s.estado == EstadoMembresia.SOLICITADA


def test_activar_rechaza_menor_de_16_con_rn01():
    socio = Socio("S1", "Ana", ficha=FichaDeAlta(date(2015, 1, 1), "a@b.co", "8112345678"))
    s = solicitud()
    ctx = _contexto_de(socio)
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.activar(type(ctx)(s, socio, ctx.planes, {}, 0))
    assert e.value.regla == "RN-01"


def test_activar_menor_con_documentacion_completa():
    socio = alta(ficha(17, True, True))
    s = solicitud()
    ctx = _contexto_de(socio)
    s.activar(type(ctx)(s, socio, ctx.planes, {}, 0))
    assert s.estado == EstadoMembresia.ACTIVA


def test_la_edad_se_mide_a_la_fecha_de_la_solicitud():
    socio = Socio("S1", "Ana", ficha=FichaDeAlta(date(2010, 11, 15), "a@b.co", "8112345678", True, True))
    assert not socio.cumple_requisitos_de_edad(date(2026, 10, 1))  # aún tenía 15
    assert socio.cumple_requisitos_de_edad(date(2026, 11, 15))


def test_socios_del_paquete_sin_ficha_cumplen_la_edad():
    assert Socio("FIT-C001", "Socio 01").cumple_requisitos_de_edad(HOY)
