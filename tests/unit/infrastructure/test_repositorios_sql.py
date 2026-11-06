"""Pruebas de los repositorios SQL sobre SQLite en memoria (mismo código que PostgreSQL)."""
from decimal import Decimal

import pytest

from src.domain.state_machine import EstadoMembresia
from src.infrastructure.composicion import (
    crear_servicio,
    crear_servicio_en_memoria,
    crear_servicio_sql,
)
from src.infrastructure.csv_loader import cargar_paquete
from src.infrastructure.db import normalizar_url
from src.infrastructure.memoria import RepositorioSolicitudesMemoria
from src.infrastructure.repositorios_sql import RepositorioSolicitudesSQL


@pytest.fixture
def svc():
    """Base SQLite nueva y vacía de solicitudes, con socios y planes del paquete."""
    return crear_servicio_sql("sqlite://", con_solicitudes=False)


@pytest.fixture
def datos():
    p = cargar_paquete()
    socio = next(s for s in p.socios.values() if s.activo)
    plan = next(x for x in p.planes.values() if x.habilitado and x.cupo >= 1)
    return socio, plan


def test_siembra_el_paquete_completo():
    s = crear_servicio_sql("sqlite://")
    assert len(s.solicitudes.listar()) == 60
    assert len(s.planes.todos()) == 20
    assert s.socios.obtener("FIT-C001") is not None


def test_siembra_solo_una_vez():
    from src.infrastructure.composicion import sembrar_si_vacia
    from src.infrastructure.db import crear_fabrica_sesiones, crear_motor

    sesiones = crear_fabrica_sesiones(crear_motor("sqlite://"))
    sembrar_si_vacia(sesiones)
    sembrar_si_vacia(sesiones)  # no duplica
    assert len(RepositorioSolicitudesSQL(sesiones).listar()) == 60


def test_obtener_inexistente_devuelve_none(svc):
    assert svc.socios.obtener("NO-EXISTE") is None
    assert svc.planes.obtener("NO-EXISTE") is None
    assert svc.solicitudes.obtener("NO-EXISTE") is None


def test_solicitud_se_guarda_y_se_lee_igual(svc, datos):
    socio, plan = datos
    creada = svc.crear(socio.id, [(plan.id, 2)], validada=True, referencia="R-1")
    leida = svc.solicitudes.obtener(creada.id)
    assert leida.socio_id == socio.id
    assert leida.estado == EstadoMembresia.SOLICITADA
    assert leida.validada is True and leida.referencia == "R-1"
    assert leida.total.monto == plan.precio.monto * 2
    assert isinstance(leida.total.monto, Decimal)


def test_el_cambio_de_estado_se_persiste(svc, datos):
    socio, plan = datos
    creada = svc.crear(socio.id, [(plan.id, 1)], validada=True)
    svc.activar(creada.id)
    assert svc.solicitudes.obtener(creada.id).estado == EstadoMembresia.ACTIVA
    assert svc.solicitudes.vigentes_del_socio(socio.id) == 1
    assert svc.solicitudes.vigentes_por_plan() == {plan.id: 1}


def test_guardar_dos_veces_no_duplica_lineas(svc, datos):
    socio, plan = datos
    creada = svc.crear(socio.id, [(plan.id, 1), (plan.id, 3)], validada=True)
    svc.solicitudes.guardar(creada)
    assert len(svc.solicitudes.obtener(creada.id).lineas) == 2


def test_listar_filtra_por_estado(svc, datos):
    socio, plan = datos
    a = svc.crear(socio.id, [(plan.id, 1)], validada=True)
    svc.crear(socio.id, [(plan.id, 1)], validada=True)
    svc.cancelar(a.id)
    assert len(svc.listar(EstadoMembresia.CANCELADA)) == 1
    assert len(svc.listar(EstadoMembresia.SOLICITADA)) == 1


def test_sql_y_memoria_dan_los_mismos_conteos_de_cupo(datos):
    socio, plan = datos
    sql = crear_servicio_sql("sqlite://", con_solicitudes=False)
    mem = crear_servicio_en_memoria(con_solicitudes=False)
    for servicio in (sql, mem):
        s = servicio.crear(socio.id, [(plan.id, 1)], validada=True)
        servicio.activar(s.id)
    assert sql.solicitudes.vigentes_por_plan() == mem.solicitudes.vigentes_por_plan()
    assert sql.solicitudes.vigentes_del_socio(socio.id) == mem.solicitudes.vigentes_del_socio(socio.id)
    assert isinstance(mem.solicitudes, RepositorioSolicitudesMemoria)


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_normalizar_url(entrada, esperado):
    assert normalizar_url(entrada) == esperado


def test_crear_servicio_usa_memoria_sin_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert isinstance(crear_servicio().solicitudes, RepositorioSolicitudesMemoria)


def test_crear_servicio_usa_sql_con_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert isinstance(crear_servicio().solicitudes, RepositorioSolicitudesSQL)
