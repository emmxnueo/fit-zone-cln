"""El flujo de clases sobre los repositorios SQL: siempre en SQLite y, si
DATABASE_URL apunta a PostgreSQL (Docker y CI), también ahí."""
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.domain.clase import EstadoEntrada
from src.domain.specifications import CategoriaClase
from src.domain.state_machine import EstadoClase, EstadoReserva
from src.infrastructure.composicion import crear_servicios_sql, sembrar_clases_si_vacio
from src.infrastructure.db import crear_motor
from src.infrastructure.reloj import RelojDelSistema
from tests.unit.application.test_clases import INICIO
from tests.unit.domain.helpers import RelojFijo


@pytest.fixture(params=["sqlite", "postgresql"])
def url(request):
    """En PostgreSQL cada prueba usa un esquema temporal: no toca los datos de la base."""
    if request.param == "sqlite":
        yield "sqlite://"
        return
    base = os.getenv("DATABASE_URL", "")
    if not base.startswith("postgres"):
        pytest.skip("DATABASE_URL no apunta a PostgreSQL")
    esquema = f"prueba_{uuid4().hex[:8]}"
    motor = crear_motor(base)
    with motor.begin() as c:
        c.execute(text(f"CREATE SCHEMA {esquema}"))
    separador = "&" if "?" in base else "?"
    yield f"{base}{separador}options=-csearch_path%3D{esquema}"
    with motor.begin() as c:
        c.execute(text(f"DROP SCHEMA {esquema} CASCADE"))
    motor.dispose()


@pytest.fixture
def entorno(url):
    reloj = RelojFijo(INICIO - timedelta(days=1))
    s = crear_servicios_sql(url, con_solicitudes=False, reloj=reloj)
    socios = ["FIT-C001", "FIT-C002", "FIT-C003"]
    plan = next(p.id for p in s.membresias.planes.todos().values() if p.habilitado and p.cupo >= 3)
    for socio in socios:
        sol = s.membresias.crear(socio, [(plan, 1)], validada=True)
        s.membresias.activar(sol.id)
    return s, socios, reloj


def test_lista_y_oferta_sobreviven_a_la_persistencia(entorno):
    s, (t, a, b), reloj = entorno
    c = s.clases.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO, 1, "Ana", "Salón 1")
    r = s.clases.reservar(c.id, t)
    s.clases.reservar(c.id, a)
    s.clases.reservar(c.id, b)
    s.clases.cancelar_reserva(c.id, r.id)
    leida = s.clases.obtener(c.id)
    assert leida.reserva(r.id).estado == EstadoReserva.CANCELADA
    assert leida.oferta_activa.socio_id == a
    assert leida.oferta_activa.ofertada_en == reloj.ahora()
    assert [e.socio_id for e in leida.en_espera] == [b]
    s.clases.confirmar_oferta(c.id, a)
    leida = s.clases.obtener(c.id)
    assert [x.socio_id for x in leida.confirmadas] == [a]
    assert leida.lista_espera[0].estado == EstadoEntrada.ASIGNADA
    assert [x.id for x in s.clases.listar()] == [c.id]


def test_no_show_falta_sancion_e_ingresos_persisten(entorno):
    s, (t, a, _), reloj = entorno
    for dia in range(3):
        c = s.clases.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO + timedelta(days=dia), 1)
        reloj.fijar(c.inicio - timedelta(hours=2))
        s.clases.reservar(c.id, t)
        s.clases.reservar(c.id, a)
        s.clases.registrar_ingreso(a)
        s.clases.procesar_reloj(c.inicio + timedelta(minutes=11))
        assert [x.socio_id for x in s.clases.obtener(c.id).confirmadas] == [a]
    socio = s.clases.obtener_socio(t)
    assert len(socio.faltas) == 3 and all(f.consumida for f in socio.faltas)
    assert socio.sancion_hasta == INICIO + timedelta(days=2) + timedelta(days=7)
    assert s.clases.socios.obtener(a).faltas == []


def test_siembra_clases_una_sola_vez():
    s = crear_servicios_sql("sqlite://")
    assert len(s.clases.listar()) == 3
    sembrar_clases_si_vacio(s.clases.clases, s.clases.reloj)
    assert len(s.clases.listar()) == 3


def test_reloj_del_sistema_no_tiene_zona():
    assert RelojDelSistema().ahora().tzinfo is None


def test_reportes_leen_lo_persistido(entorno):
    s, (t, a, _), reloj = entorno
    c = s.clases.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO, 1)
    s.clases.reservar(c.id, t)
    s.clases.reservar(c.id, a)
    s.clases.registrar_ingreso(t)  # hoy, un día antes de la clase
    dia = reloj.ahora().date()
    afluencia = s.reportes.afluencia(dia, dia)
    assert afluencia.total == 1 and afluencia.por_hora[reloj.ahora().hour] == 1
    assert s.reportes.afluencia(dia + timedelta(days=1), dia + timedelta(days=1)).total == 0
    demanda = s.reportes.demanda()[0]
    assert (demanda.reservas_confirmadas, demanda.en_lista_de_espera) == (1, 1)


def test_ciclo_de_cancelacion_persiste(entorno):
    s, (t, a, _), _ = entorno
    c = s.clases.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO, 1, "Ana")
    s.clases.reservar(c.id, t)
    s.clases.reservar(c.id, a)
    s.clases.solicitar_cancelacion(c.id, "Ana")
    assert s.clases.obtener(c.id).estado == EstadoClase.CANCELACION_SOLICITADA
    s.clases.resolver_cancelacion(c.id, aprobada=False)
    assert s.clases.obtener(c.id).estado == EstadoClase.PROGRAMADA
    s.clases.solicitar_cancelacion(c.id, "Ana")
    s.clases.resolver_cancelacion(c.id, aprobada=True)
    leida = s.clases.obtener(c.id)
    assert leida.estado == EstadoClase.CANCELADA and leida.confirmadas == []
    assert leida.lista_espera[0].estado == EstadoEntrada.DESCARTADA
