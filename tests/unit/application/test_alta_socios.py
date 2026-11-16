"""Caso de uso de alta de socio (BPMN 12.1, carril de Recepción)."""
from datetime import date, datetime

import pytest

from src.domain.errors import ReglaDeNegocioViolada
from src.domain.value_objects import FichaDeAlta
from src.infrastructure.composicion import crear_servicios_en_memoria
from tests.unit.domain.helpers import RelojFijo

AHORA = datetime(2026, 11, 16, 10, 0)


@pytest.fixture
def s():
    return crear_servicios_en_memoria(con_solicitudes=False, reloj=RelojFijo(AHORA))


def ficha(nacimiento, completa=False):
    return FichaDeAlta(nacimiento, "ana@correo.com", "8112345678", completa, completa)


def test_alta_continua_la_numeracion_del_paquete(s):
    a = s.clases.dar_de_alta_socio("Ana", ficha(date(2000, 1, 1)))
    b = s.clases.dar_de_alta_socio("Beto", ficha(date(2001, 1, 1)))
    assert (a.id, b.id) == ("FIT-C041", "FIT-C042")
    assert s.clases.obtener_socio("FIT-C041").ficha.correo == "ana@correo.com"


def test_alta_de_menor_publica_deslinde_firmado(s):
    s.clases.dar_de_alta_socio("Ana", ficha(date(2009, 5, 20), completa=True))
    assert "DeslindeFirmado" in [e.nombre for e in s.membresias.eventos()]


def test_la_edad_se_calcula_con_el_reloj_del_negocio(s):
    with pytest.raises(ReglaDeNegocioViolada) as e:
        s.clases.dar_de_alta_socio("Ana", ficha(date(2010, 11, 17), completa=True))
    assert e.value.regla == "RN-01"
    assert len(s.clases.listar_socios()) == 40  # el rechazo no deja nada guardado


def test_flujo_bpmn_12_1_alta_solicitud_y_activacion(s):
    socio = s.clases.dar_de_alta_socio("Ana", ficha(date(2009, 5, 20), completa=True))
    plan = next(p for p in s.membresias.planes.todos().values() if p.habilitado and p.cupo >= 1)
    sol = s.membresias.crear(socio.id, [(plan.id, 1)], validada=True, fecha=AHORA.date())
    assert s.membresias.activar(sol.id).estado.value == "ACTIVA"
