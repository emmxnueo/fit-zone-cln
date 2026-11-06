from decimal import Decimal

import pytest

from src.domain import events as ev
from src.domain.errors import (
    CupoAgotado, MembresiaActivaExistente, ReglaDeNegocioViolada, TransicionInvalida,
)
from src.domain.state_machine import EstadoMembresia as E
from tests.unit.domain.helpers import contexto, plan, solicitud


def activa():
    s = solicitud()
    s.activar(contexto(s))
    s.pull_events()
    return s


def test_total_es_suma_precio_por_cantidad_en_decimal():
    s = solicitud(lineas=((("P1", "474.00"), 3), (("P2", "545.00"), 1)))
    assert s.total.monto == Decimal("1967.00")


def test_solicitud_sin_lineas_tiene_total_cero():
    assert solicitud(lineas=()).total.monto == Decimal("0.00")


def test_cantidad_invalida_al_agregar_linea():
    with pytest.raises(ReglaDeNegocioViolada):
        solicitud().agregar_linea(plan("P9"), 0)


def test_activar_exitoso_emite_evento():
    s = solicitud()
    s.activar(contexto(s))
    assert s.estado == E.ACTIVA
    (evento,) = s.pull_events()
    assert isinstance(evento, ev.MembresiaActivada) and evento.total_mxn == "500.00"
    assert s.pull_events() == []


def test_activar_no_procesable_es_422():
    s = solicitud(validada=False)
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.activar(contexto(s))
    assert e.value.codigo_http == 422 and e.value.regla == "RN-37"
    assert s.estado == E.SOLICITADA


def test_activar_con_plan_deshabilitado_es_422():
    s = solicitud()
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.activar(contexto(s, planes={"P1": plan("P1", habilitado=False)}))
    assert e.value.regla == "RN-38"


def test_activar_con_membresia_activa_es_409():
    s = solicitud()
    with pytest.raises(MembresiaActivaExistente) as e:
        s.activar(contexto(s, activas=1))
    assert e.value.codigo_http == 409 and e.value.regla == "RN-03"


def test_activar_sin_cupo_es_409():
    s = solicitud()
    with pytest.raises(CupoAgotado) as e:
        s.activar(contexto(s, ocupacion={"P1": 5}))
    assert e.value.codigo_http == 409 and e.value.regla == "RN-39"


def test_repetir_aprobacion_es_409():
    s = activa()
    with pytest.raises(TransicionInvalida):
        s.activar(contexto(s))


def test_cancelar_desde_solicitada():
    s = solicitud()
    s.cancelar()
    assert s.estado == E.CANCELADA
    assert isinstance(s.pull_events()[0], ev.SolicitudCancelada)


def test_saltar_estado_solicitada_a_vencida_es_409():
    s = solicitud()
    with pytest.raises(TransicionInvalida):
        s.vencer()
    assert s.estado == E.SOLICITADA


def test_vencer_desde_activa_y_renovar():
    s = activa()
    s.vencer()
    assert s.estado == E.VENCIDA
    with pytest.raises(ReglaDeNegocioViolada):
        s.renovar(pago_confirmado=False)
    s.renovar(pago_confirmado=True)
    assert s.estado == E.ACTIVA
    assert [type(x) for x in s.pull_events()] == [ev.MembresiaVencida, ev.MembresiaRenovada]


def test_congelar_exige_aprobacion_del_administrador():
    s = activa()
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.congelar(aprobada_por_administrador=False)
    assert e.value.regla == "RN-09" and s.estado == E.ACTIVA
    s.congelar(aprobada_por_administrador=True)
    s.descongelar()
    assert s.estado == E.ACTIVA


def test_baja_exige_aprobacion_y_es_final():
    s = activa()
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.dar_de_baja(aprobada_por_administrador=False)
    assert e.value.regla == "RN-10"
    s.dar_de_baja(aprobada_por_administrador=True)
    assert s.estado == E.CANCELADA
    with pytest.raises(TransicionInvalida):
        s.activar(contexto(s))


def test_puede_procesarse_y_beneficio_delegan_en_specifications():
    s = solicitud(lineas=((("P1", "500"), 3),))
    ctx = contexto(s, premium=True)
    assert s.puede_procesarse(ctx) and s.aplica_beneficio_de_referencia(ctx)
