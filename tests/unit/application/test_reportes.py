"""Escenarios Gherkin de US-08 y US-09."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from src.application.reportes import ServicioDeReportes
from src.domain.clase import Clase, EntradaListaEspera, EstadoEntrada, Reserva
from src.domain.errors import ReglaDeNegocioViolada
from src.domain.specifications import CategoriaClase
from src.domain.state_machine import EstadoReserva
from src.infrastructure.memoria import RepositorioClasesMemoria, RepositorioIngresosMemoria

INICIO = datetime(2026, 12, 1, 18, 0)
LUNES = date(2026, 11, 2)


def clase(id, capacidad, confirmadas=0, espera=0, ofertada=False, canceladas=0):
    c = Clase(id, id, CategoriaClase.ESTANDAR, INICIO, capacidad)
    c.reservas = [Reserva(f"R{i}", f"S{i}", INICIO) for i in range(confirmadas)]
    c.reservas += [
        Reserva(f"X{i}", f"X{i}", INICIO, EstadoReserva.CANCELADA) for i in range(canceladas)
    ]
    c.lista_espera = [EntradaListaEspera(f"E{i}", f"W{i}", i, INICIO) for i in range(espera)]
    if ofertada:
        c.lista_espera.append(
            EntradaListaEspera("EO", "WO", 99, INICIO, EstadoEntrada.OFERTADA, INICIO)
        )
    return c


def armar(clases=(), ingresos=()):
    repo = RepositorioIngresosMemoria()
    for i, momento in enumerate(ingresos):
        repo.registrar(f"S{i}", momento)
    return ServicioDeReportes(RepositorioClasesMemoria({c.id: c for c in clases}), repo)


def test_afluencia_agrupa_por_hora_y_dia_de_la_semana():
    svc = armar(ingresos=[
        datetime(2026, 11, 2, 7, 5), datetime(2026, 11, 2, 7, 50), datetime(2026, 11, 3, 18, 0),
    ])
    r = svc.afluencia(LUNES, LUNES + timedelta(days=6))
    assert r.total == 3
    assert r.por_hora[7] == 2 and r.por_hora[18] == 1
    assert r.por_dia["Lunes"] == 2 and r.por_dia["Martes"] == 1


def test_el_mismo_socio_cuenta_cada_ingreso():
    repo = RepositorioIngresosMemoria()
    repo.registrar("S1", datetime(2026, 11, 2, 7))
    repo.registrar("S1", datetime(2026, 11, 2, 19))
    assert ServicioDeReportes(RepositorioClasesMemoria(), repo).afluencia(LUNES, LUNES).total == 2


def test_el_rango_incluye_ambos_extremos_y_nada_mas():
    svc = armar(ingresos=[
        datetime(2026, 11, 1, 23, 59), datetime(2026, 11, 2, 0, 0),
        datetime(2026, 11, 3, 23, 59), datetime(2026, 11, 4, 0, 0),
    ])
    assert svc.afluencia(LUNES, LUNES + timedelta(days=1)).total == 2


def test_rango_sin_ingresos_sale_en_ceros():
    r = armar().afluencia(LUNES, LUNES)
    assert r.total == 0
    assert len(r.por_hora) == 24 and set(r.por_hora.values()) == {0}
    assert list(r.por_dia)[0] == "Lunes" and set(r.por_dia.values()) == {0}


def test_rango_invalido_se_rechaza():
    with pytest.raises(ReglaDeNegocioViolada) as e:
        armar().afluencia(LUNES, LUNES - timedelta(days=1))
    assert e.value.regla == "RN-35"


def test_clase_llena_con_lista_de_espera():
    d = armar([clase("A", 20, confirmadas=20, espera=3)]).demanda()[0]
    assert d.ocupacion_pct == Decimal("100.00") and d.en_lista_de_espera == 3


def test_clase_sin_reservas():
    d = armar([clase("A", 20)]).demanda()[0]
    assert d.ocupacion_pct == Decimal("0.00") and d.en_lista_de_espera == 0


def test_solo_cuentan_reservas_confirmadas_y_quien_sigue_esperando():
    c = clase("A", 3, confirmadas=1, espera=1, ofertada=True, canceladas=2)
    c.lista_espera.append(EntradaListaEspera("EX", "WX", 100, INICIO, EstadoEntrada.EXPIRADA))
    d = armar([c]).demanda()[0]
    assert d.reservas_confirmadas == 1
    assert d.ocupacion_pct == Decimal("33.33")
    assert d.en_lista_de_espera == 2


def test_demanda_ordena_de_mayor_a_menor():
    clases = [clase("Baja", 10, 1), clase("Llena", 2, 2), clase("LlenaConLista", 2, 2, 4)]
    assert [d.clase_id for d in armar(clases).demanda()] == ["LlenaConLista", "Llena", "Baja"]
