"""Escenarios Gherkin de US-01, US-04, US-05, US-14, US-19 y US-20."""
from datetime import datetime, timedelta

import pytest

from src.domain import events as ev
from src.domain.clase import Clase, EntradaListaEspera, EstadoEntrada, Reserva
from src.domain.entities import Socio
from src.domain.errors import ConflictoDeEstado, ReglaDeNegocioViolada, TransicionInvalida
from src.domain.specifications import CategoriaClase, ContextoReserva, ElegibleParaReservar
from src.domain.state_machine import EstadoReserva

INICIO = datetime(2026, 12, 1, 18, 0)
ANTES = INICIO - timedelta(days=1)


def clase(capacidad=1, categoria=CategoriaClase.ESTANDAR):
    return Clase("C1", "Yoga", categoria, INICIO, capacidad)


def ctx(socio_id="A", ahora=ANTES, vigente=True, premium=False, categoria=CategoriaClase.ESTANDAR,
        sancion_hasta=None):
    socio = Socio(socio_id, socio_id, es_premium=premium, sancion_hasta=sancion_hasta)
    return ContextoReserva(socio, categoria, vigente, ahora)


def llena_con_lista(*espera):
    c = clase()
    titular = c.reservar(ctx("T"))
    for s in espera:
        c.reservar(ctx(s))
    c.pull_events()
    return c, titular


def tipos(c):
    return [type(e) for e in c.pull_events()]


# --- US-01: reservar --------------------------------------------------------
def test_capacidad_debe_ser_positiva():
    with pytest.raises(ReglaDeNegocioViolada) as e:
        clase(capacidad=0)
    assert e.value.regla == "RN-11"


def test_reservar_con_lugar_confirma_y_descuenta():
    c = clase(capacidad=2)
    assert isinstance(c.reservar(ctx()), Reserva)
    assert c.lugares_libres == 1
    assert tipos(c) == [ev.ReservaConfirmada]


def test_clase_llena_manda_a_lista_de_espera():
    c, _ = llena_con_lista()
    entrada = c.reservar(ctx("B"))
    assert isinstance(entrada, EntradaListaEspera)
    assert tipos(c) == [ev.SocioEnListaDeEspera]
    assert len(c.confirmadas) == 1  # RN-11: no se supera la capacidad


@pytest.mark.parametrize("kwargs, regla", [
    ({"vigente": False}, "RN-13"),
    ({"categoria": CategoriaClase.PREMIUM}, "RN-13"),
    ({"sancion_hasta": ANTES + timedelta(days=1)}, "RN-26"),
])
def test_socio_no_elegible_se_rechaza(kwargs, regla):
    c = clase(categoria=kwargs.get("categoria", CategoriaClase.ESTANDAR))
    with pytest.raises(ReglaDeNegocioViolada) as e:
        c.reservar(ctx(**kwargs))
    assert e.value.regla == regla and c.confirmadas == []


def test_premium_reserva_clase_premium():
    c = clase(categoria=CategoriaClase.PREMIUM)
    c.reservar(ctx(premium=True, categoria=CategoriaClase.PREMIUM))
    assert len(c.confirmadas) == 1


def test_elegible_compone_las_condiciones():
    assert ElegibleParaReservar().is_satisfied_by(ctx())
    assert not ElegibleParaReservar().is_satisfied_by(ctx(vigente=False))


def test_no_se_reserva_clase_iniciada():
    with pytest.raises(ConflictoDeEstado):
        clase().reservar(ctx(ahora=INICIO))


def test_reserva_repetida_es_conflicto():
    c = clase(capacidad=2)
    c.reservar(ctx())
    with pytest.raises(ConflictoDeEstado):
        c.reservar(ctx())


def test_registro_duplicado_conserva_la_posicion():
    c, _ = llena_con_lista("A", "B")
    with pytest.raises(ConflictoDeEstado) as e:
        c.reservar(ctx("A"))
    assert e.value.regla == "RN-24"
    assert [x.socio_id for x in c.en_espera] == ["A", "B"]


# --- US-14: cancelar --------------------------------------------------------
@pytest.mark.parametrize("anticipacion, estado, evento", [
    (timedelta(hours=2), EstadoReserva.CANCELADA, ev.ReservaCancelada),
    (timedelta(hours=1), EstadoReserva.CANCELADA, ev.ReservaCancelada),
    (timedelta(minutes=59), EstadoReserva.CANCELADA_TARDE, ev.CancelacionTardiaRegistrada),
])
def test_cancelacion_segun_anticipacion(anticipacion, estado, evento):
    c, r = llena_con_lista()
    c.cancelar_reserva(r, INICIO - anticipacion)
    assert r.estado == estado and c.lugares_libres == 1
    assert tipos(c) == [evento]


def test_cancelar_dos_veces_es_409():
    c, r = llena_con_lista()
    c.cancelar_reserva(r, ANTES)
    with pytest.raises(TransicionInvalida):
        c.cancelar_reserva(r, ANTES)


def test_no_se_cancela_con_la_clase_iniciada():
    c, r = llena_con_lista()
    with pytest.raises(ConflictoDeEstado):
        c.cancelar_reserva(r, INICIO)
    assert r.estado == EstadoReserva.CONFIRMADA


# --- US-04, US-05: oferta FIFO ----------------------------------------------
def test_lugar_liberado_se_ofrece_al_primero_y_queda_apartado():
    c, r = llena_con_lista("A", "B")
    c.cancelar_reserva(r, ANTES)
    assert c.oferta_activa.socio_id == "A"
    assert [x.socio_id for x in c.en_espera] == ["B"]
    assert c.lugares_libres == 0
    assert ev.LugarOfrecido in tipos(c)


def test_el_orden_depende_solo_del_registro():
    c = clase()
    r = c.reservar(ctx("T"))
    c.reservar(ctx("A"))
    c.reservar(ctx("B", premium=True))
    c.cancelar_reserva(r, ANTES)
    assert c.oferta_activa.socio_id == "A"


def test_sin_lista_el_lugar_queda_disponible():
    c, r = llena_con_lista()
    c.cancelar_reserva(r, ANTES)
    assert c.oferta_activa is None and c.lugares_libres == 1


def test_solo_una_oferta_activa_y_nadie_se_salta_la_lista():
    c = clase(capacidad=2)
    r1 = c.reservar(ctx("T1"))
    r2 = c.reservar(ctx("T2"))
    c.reservar(ctx("A"))
    c.reservar(ctx("B"))
    c.cancelar_reserva(r1, ANTES)
    c.cancelar_reserva(r2, ANTES)
    assert [e.socio_id for e in c.lista_espera if e.estado == EstadoEntrada.OFERTADA] == ["A"]
    assert c.lugares_libres == 1
    assert isinstance(c.reservar(ctx("Nuevo")), EntradaListaEspera)  # RN-19
    c.confirmar_oferta(ctx("A"))
    assert c.oferta_activa.socio_id == "B"  # el segundo lugar pasa al siguiente


# --- US-20: expiración ------------------------------------------------------
def ofertada():
    c, r = llena_con_lista("A", "B")
    c.cancelar_reserva(r, ANTES)
    c.pull_events()
    return c


def test_confirmar_a_los_15_minutos_exactos():
    c = ofertada()
    reserva = c.confirmar_oferta(ctx("A", ANTES + timedelta(minutes=15)))
    assert reserva in c.confirmadas


def test_oferta_vencida_pasa_al_siguiente():
    c = ofertada()
    c.expirar_oferta(ANTES + timedelta(minutes=16))
    assert c.oferta_activa.socio_id == "B"
    assert tipos(c) == [ev.OfertaExpirada, ev.LugarOfrecido]


def test_a_los_15_minutos_la_oferta_no_expira():
    c = ofertada()
    c.expirar_oferta(ANTES + timedelta(minutes=15))
    assert c.oferta_activa.socio_id == "A"


def test_oferta_vencida_sin_lista_deja_el_lugar_libre():
    c, r = llena_con_lista("A")
    c.cancelar_reserva(r, ANTES)
    c.expirar_oferta(ANTES + timedelta(minutes=16))
    assert c.oferta_activa is None and c.lugares_libres == 1


def test_confirmar_oferta_vencida_o_ajena_se_rechaza():
    c = ofertada()
    with pytest.raises(ConflictoDeEstado):
        c.confirmar_oferta(ctx("A", ANTES + timedelta(minutes=16)))
    with pytest.raises(ConflictoDeEstado):
        c.confirmar_oferta(ctx("B"))
    c.expirar_oferta(ANTES + timedelta(minutes=16))
    with pytest.raises(ConflictoDeEstado) as e:
        c.confirmar_oferta(ctx("A", ANTES + timedelta(minutes=17)))
    assert e.value.regla == "RN-20"


def test_confirmar_exige_seguir_elegible():
    c = ofertada()
    with pytest.raises(ReglaDeNegocioViolada):
        c.confirmar_oferta(ctx("A", vigente=False))
    assert c.oferta_activa.socio_id == "A"


def test_con_la_clase_iniciada_no_se_ofrece():
    c = ofertada()
    c.expirar_oferta(INICIO + timedelta(minutes=1))
    assert c.oferta_activa is None


# --- US-19: tolerancia ------------------------------------------------------
def test_retraso_mayor_a_10_minutos_asigna_al_presente():
    c, r = llena_con_lista("A", "B")
    c.aplicar_tolerancia(INICIO + timedelta(minutes=11), {"B"}, {"B"})
    assert r.estado == EstadoReserva.NO_SHOW
    assert [x.socio_id for x in c.confirmadas] == ["B"]
    assert [x.socio_id for x in c.en_espera] == ["A"]
    assert tipos(c) == [ev.NoShowRegistrado, ev.LugarAsignado]


def test_a_los_10_minutos_exactos_no_se_libera():
    c, r = llena_con_lista("A")
    c.aplicar_tolerancia(INICIO + timedelta(minutes=10), set(), set())
    assert r.estado == EstadoReserva.CONFIRMADA


def test_nadie_presente_deja_el_lugar_libre():
    c, r = llena_con_lista("A")
    c.aplicar_tolerancia(INICIO + timedelta(minutes=12), set(), set())
    assert r.estado == EstadoReserva.NO_SHOW and c.lugares_libres == 1


def test_presente_no_elegible_no_recibe_el_lugar():
    c, _ = llena_con_lista("A")
    c.aplicar_tolerancia(INICIO + timedelta(minutes=12), {"A"}, set())
    assert c.confirmadas == []


def test_titular_presente_conserva_su_lugar_y_reaplicar_no_duplica():
    c, r = llena_con_lista("A")
    c.aplicar_tolerancia(INICIO + timedelta(minutes=12), {"T"}, set())
    assert r.estado == EstadoReserva.CONFIRMADA
    c.aplicar_tolerancia(INICIO + timedelta(minutes=13), set(), set())
    assert tipos(c) == [ev.NoShowRegistrado]
    c.aplicar_tolerancia(INICIO + timedelta(minutes=14), set(), set())
    assert tipos(c) == []


def test_oferta_confirmada_despues_del_limite_no_es_no_show():
    c, r = llena_con_lista("A")
    c.cancelar_reserva(r, INICIO - timedelta(minutes=2))
    tardia = c.confirmar_oferta(ctx("A", INICIO + timedelta(minutes=12)))
    c.aplicar_tolerancia(INICIO + timedelta(minutes=13), set(), set())
    assert tardia.estado == EstadoReserva.CONFIRMADA
