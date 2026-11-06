from datetime import date, datetime, timedelta

import pytest

from src.application.clases import ServicioDeClases
from src.application.errors import NoEncontrado
from src.domain import events as ev
from src.domain.clase import Reserva
from src.domain.entities import Socio
from src.domain.errors import ReglaDeNegocioViolada
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.specifications import CategoriaClase
from src.domain.state_machine import EstadoMembresia as E, EstadoReserva
from src.infrastructure.memoria import (
    PublicadorEnMemoria, RepositorioClasesMemoria, RepositorioIngresosMemoria,
    RepositorioSociosMemoria, RepositorioSolicitudesMemoria,
)
from tests.unit.domain.helpers import RelojFijo

INICIO = datetime(2026, 12, 1, 18, 0)


def armar(socios=("T", "A", "B"), sin_membresia=()):
    reloj = RelojFijo(INICIO - timedelta(days=1))
    sols = {
        f"O-{s}": SolicitudDeMembresia(
            f"O-{s}", s, date(2026, 10, 1),
            estado=E.VENCIDA if s in sin_membresia else E.ACTIVA,
        )
        for s in socios
    }
    pub = PublicadorEnMemoria()
    svc = ServicioDeClases(
        RepositorioSociosMemoria({s: Socio(s, s) for s in socios}),
        RepositorioSolicitudesMemoria(sols), RepositorioClasesMemoria(),
        RepositorioIngresosMemoria(), pub, reloj,
    )
    clase = svc.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO, 1)
    return svc, clase.id, reloj, pub


def nombres(pub):
    return [e.nombre for e in pub.publicados]


def test_reservar_persiste_y_publica():
    svc, cid, _, pub = armar()
    assert isinstance(svc.reservar(cid, "T"), Reserva)
    assert len(svc.obtener(cid).confirmadas) == 1
    assert nombres(pub) == ["ReservaConfirmada"]


def test_recursos_inexistentes_son_404():
    svc, cid, _, _ = armar()
    with pytest.raises(NoEncontrado):
        svc.obtener("X")
    with pytest.raises(NoEncontrado):
        svc.reservar(cid, "X")
    with pytest.raises(NoEncontrado):
        svc.cancelar_reserva(cid, "X")


def test_membresia_vencida_no_reserva_ni_ingresa():
    svc, cid, _, pub = armar(sin_membresia=("T",))
    with pytest.raises(ReglaDeNegocioViolada):
        svc.reservar(cid, "T")
    with pytest.raises(ReglaDeNegocioViolada) as e:
        svc.registrar_ingreso("T")
    assert e.value.regla == "RN-05" and pub.publicados == []


def test_cancelacion_tardia_registra_falta_en_el_socio():
    svc, cid, reloj, pub = armar()
    r = svc.reservar(cid, "T")
    reloj.fijar(INICIO - timedelta(minutes=59))
    svc.cancelar_reserva(cid, r.id)
    assert len(svc.obtener_socio("T").faltas) == 1
    assert "FaltaRegistrada" in nombres(pub)


def test_cancelacion_a_tiempo_no_registra_falta():
    svc, cid, _, _ = armar()
    svc.cancelar_reserva(cid, svc.reservar(cid, "T").id)
    assert svc.obtener_socio("T").faltas == []


def test_oferta_confirmada_por_el_servicio():
    svc, cid, _, _ = armar()
    r = svc.reservar(cid, "T")
    svc.reservar(cid, "A")
    svc.cancelar_reserva(cid, r.id)
    assert svc.confirmar_oferta(cid, "A").socio_id == "A"


def test_reloj_expira_la_oferta_y_ofrece_al_siguiente():
    svc, cid, reloj, _ = armar()
    r = svc.reservar(cid, "T")
    svc.reservar(cid, "A")
    svc.reservar(cid, "B")
    svc.cancelar_reserva(cid, r.id)
    resumen = svc.procesar_reloj(reloj.ahora() + timedelta(minutes=16))
    assert (resumen.ofertas_expiradas, resumen.lugares_ofrecidos) == (1, 1)
    assert svc.obtener(cid).oferta_activa.socio_id == "B"


def test_reloj_aplica_no_show_y_asigna_al_presente():
    svc, cid, reloj, _ = armar()
    r = svc.reservar(cid, "T")
    svc.reservar(cid, "A")
    svc.reservar(cid, "B")
    reloj.fijar(INICIO - timedelta(minutes=30))
    svc.registrar_ingreso("B")
    reloj.fijar(INICIO + timedelta(minutes=11))
    resumen = svc.procesar_reloj()
    assert (resumen.no_shows, resumen.lugares_asignados) == (1, 1)
    clase = svc.obtener(cid)
    assert clase.reserva(r.id).estado == EstadoReserva.NO_SHOW
    assert [x.socio_id for x in clase.confirmadas] == ["B"]
    assert svc.obtener_socio("T").faltas[0].clase_id == cid


def test_presente_que_perdio_la_membresia_no_recibe_el_lugar():
    svc, cid, reloj, _ = armar()
    svc.reservar(cid, "T")
    svc.reservar(cid, "A")
    reloj.fijar(INICIO - timedelta(minutes=30))
    svc.registrar_ingreso("A")
    svc.solicitudes.obtener("O-A").estado = E.VENCIDA
    assert svc.procesar_reloj(INICIO + timedelta(minutes=11)).lugares_asignados == 0


def test_ingreso_de_otro_dia_no_cuenta_como_presente():
    svc, cid, reloj, _ = armar()
    svc.reservar(cid, "T")
    svc.registrar_ingreso("T")  # un día antes de la clase
    assert svc.procesar_reloj(INICIO + timedelta(minutes=11)).no_shows == 1


def test_tres_faltas_sancionan_y_bloquean_reservas_pero_no_el_acceso():
    svc, cid, reloj, pub = armar()
    for dia in range(3):
        c = svc.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO + timedelta(days=dia), 1)
        reloj.fijar(c.inicio - timedelta(days=1))
        svc.reservar(c.id, "T")
        svc.procesar_reloj(c.inicio + timedelta(minutes=11))
    assert ev.SancionAplicada in [type(e) for e in pub.publicados]
    reloj.fijar(INICIO + timedelta(days=3))
    otra = svc.crear_clase("Yoga", CategoriaClase.ESTANDAR, INICIO + timedelta(days=4), 1)
    with pytest.raises(ReglaDeNegocioViolada) as e:
        svc.reservar(otra.id, "T")
    assert e.value.regla == "RN-26"
    svc.registrar_ingreso("T")  # RN-26: conserva el acceso


def test_etiqueta_segun_el_plan():
    svc, cid, _, _ = armar()
    premium = svc.crear_clase("HIIT", CategoriaClase.PREMIUM, INICIO, 5)
    assert svc.etiqueta(svc.obtener(cid), "T") == "Incluida en tu membresía"
    assert svc.etiqueta(premium, "T") == "Costo adicional / Exclusiva Plan Premium"
