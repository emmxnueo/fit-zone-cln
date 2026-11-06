"""Escenarios Gherkin de US-06 (RN-25 a RN-28)."""
from datetime import datetime, timedelta

from src.domain import events as ev
from src.domain.entities import Socio
from src.domain.value_objects import Falta, MotivoFalta


def falta(dia, mes=11):
    return Falta("C1", datetime(2026, mes, dia, 18), MotivoFalta.NO_SHOW)


def socio_con(*faltas):
    s = Socio("S1", "Uno")
    for f in faltas:
        s.registrar_falta(f)
    return s


def test_tercera_falta_del_mes_sanciona_7_dias():
    s = socio_con(falta(1), falta(2), falta(3))
    assert s.sancion_hasta == datetime(2026, 11, 3, 18) + timedelta(days=7)
    assert s.tiene_sancion_activa(datetime(2026, 11, 10, 17, 59))
    assert not s.tiene_sancion_activa(datetime(2026, 11, 10, 18))
    assert ev.SancionAplicada in [type(e) for e in s.pull_events()]


def test_dos_faltas_no_sancionan():
    assert socio_con(falta(1), falta(2)).sancion_hasta is None


def test_faltas_de_meses_distintos_no_se_suman():
    assert socio_con(falta(29, 10), falta(30, 10), falta(1)).sancion_hasta is None


def test_las_faltas_sancionadas_se_consumen_y_siguen_en_el_historial():
    s = socio_con(falta(1), falta(2), falta(3))
    hasta = s.sancion_hasta
    s.registrar_falta(falta(4))
    assert len(s.faltas) == 4
    assert [f.consumida for f in s.faltas] == [True, True, True, False]
    assert s.sancion_hasta == hasta  # RN-28: no se extiende


def test_nuevo_ciclo_tras_la_sancion():
    s = socio_con(falta(1), falta(2), falta(3), falta(4), falta(20), falta(21))
    assert s.sancion_hasta == datetime(2026, 11, 21, 18) + timedelta(days=7)
