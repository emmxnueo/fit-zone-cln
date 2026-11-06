from datetime import date

import pytest

from src.application.errors import NoEncontrado
from src.application.servicio import ServicioDeMembresias
from src.domain import events as ev
from src.domain.entities import Socio
from src.domain.errors import (
    CupoAgotado, MembresiaActivaExistente, ReglaDeNegocioViolada, TransicionInvalida,
)
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.state_machine import EstadoMembresia as E
from src.infrastructure.memoria import (
    PublicadorEnMemoria, RepositorioPlanesMemoria, RepositorioSociosMemoria,
    RepositorioSolicitudesMemoria,
)
from tests.unit.domain.helpers import plan


def armar(cupo=5, socios=None, solicitudes=(), validadas=True):
    """Servicio con el plan P1 y las solicitudes dadas: (id, socio_id, cantidad)."""
    p = plan("P1", "500", cupo)
    socios = socios or {"S1": Socio("S1", "Uno", True), "S2": Socio("S2", "Dos", es_premium=False, activo=False)}
    sols = {}
    for sid, socio_id, cantidad in solicitudes:
        s = SolicitudDeMembresia(sid, socio_id, date(2026, 10, 1), validada=validadas)
        s.agregar_linea(p, cantidad)
        sols[sid] = s
    pub = PublicadorEnMemoria()
    return ServicioDeMembresias(
        RepositorioSociosMemoria(socios), RepositorioPlanesMemoria({"P1": p}),
        RepositorioSolicitudesMemoria(sols), pub,
    ), pub


def test_activar_persiste_y_publica_el_evento():
    svc, pub = armar(solicitudes=[("O1", "S1", 1)])
    svc.activar("O1")
    assert svc.obtener("O1").estado == E.ACTIVA
    assert [type(e) for e in pub.publicados] == [ev.MembresiaActivada]


def test_si_el_dominio_rechaza_no_se_publica_nada():
    svc, pub = armar(solicitudes=[("O1", "S1", 1)], validadas=False)
    with pytest.raises(ReglaDeNegocioViolada):
        svc.activar("O1")
    assert pub.publicados == [] and svc.obtener("O1").estado == E.SOLICITADA


def test_solicitud_inexistente_es_404():
    svc, _ = armar()
    with pytest.raises(NoEncontrado) as e:
        svc.activar("NOPE")
    assert e.value.codigo_http == 404


def test_socio_inexistente_es_404():
    svc, _ = armar(solicitudes=[("O1", "S1", 1)])
    svc.solicitudes.obtener("O1").socio_id = "FANTASMA"
    with pytest.raises(NoEncontrado):
        svc.evaluar_procesable("O1")


def test_segunda_membresia_activa_del_mismo_socio_es_409():
    svc, _ = armar(solicitudes=[("O1", "S1", 1), ("O2", "S1", 1)])
    svc.activar("O1")
    with pytest.raises(MembresiaActivaExistente):
        svc.activar("O2")


def test_la_cancelada_no_cuenta_como_activa():
    svc, _ = armar(solicitudes=[("O1", "S1", 1), ("O2", "S1", 1)])
    svc.cancelar("O1")
    svc.activar("O2")
    assert svc.obtener("O2").estado == E.ACTIVA


def test_cupo_agotado_es_409():
    socios = {"S1": Socio("S1", "a"), "S2": Socio("S2", "b")}
    svc, _ = armar(cupo=1, socios=socios, solicitudes=[("O1", "S1", 1), ("O2", "S2", 1)])
    svc.activar("O1")
    with pytest.raises(CupoAgotado):
        svc.activar("O2")


def test_ciclo_completo_congelar_vencer_renovar_baja():
    svc, pub = armar(solicitudes=[("O1", "S1", 1)])
    svc.activar("O1")
    svc.congelar("O1", aprobada=True)
    svc.descongelar("O1")
    svc.vencer("O1")
    svc.renovar("O1", pago_confirmado=True)
    svc.dar_de_baja("O1", aprobada=True)
    assert svc.obtener("O1").estado == E.CANCELADA
    assert [e.nombre for e in pub.publicados] == [
        "MembresiaActivada", "MembresiaCongelada", "MembresiaDescongelada",
        "MembresiaVencida", "MembresiaRenovada", "MembresiaDadaDeBaja",
    ]
    with pytest.raises(TransicionInvalida):
        svc.activar("O1")


def test_evaluar_procesable_explica_los_motivos():
    svc, _ = armar(solicitudes=[("O1", "S2", 1)], validadas=False)
    r = svc.evaluar_procesable("O1")
    assert not r.cumple and r.motivos == ["socio_inactivo", "sin_validacion"]


def test_evaluar_beneficio_explica_los_motivos():
    svc, _ = armar(solicitudes=[("O1", "S1", 3), ("O2", "S2", 1)])
    assert svc.evaluar_beneficio("O1").cumple
    r = svc.evaluar_beneficio("O2")
    assert not r.cumple and r.motivos == ["socio_no_premium", "total_menor_a_1500"]
    svc.solicitudes.obtener("O1").cortesia_activa = True
    assert svc.evaluar_beneficio("O1").motivos == ["cortesia_activa"]


def test_publicador_notifica_a_los_suscriptores():
    svc, pub = armar(solicitudes=[("O1", "S1", 1)])
    recibidos = []
    pub.suscribir(ev.MembresiaActivada, recibidos.append)
    svc.activar("O1")
    assert len(recibidos) == 1 and recibidos[0].solicitud_id == "O1"
