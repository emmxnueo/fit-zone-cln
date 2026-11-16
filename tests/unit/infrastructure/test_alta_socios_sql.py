"""El alta de socios persiste en SQL sin migraciones: `fichas_socio` es una tabla nueva."""
from datetime import date, datetime

from sqlalchemy import inspect

from src.domain.value_objects import FichaDeAlta
from src.infrastructure.composicion import crear_servicios_sql
from src.infrastructure.db import Base, SocioRow, crear_fabrica_sesiones, crear_motor
from tests.unit.domain.helpers import RelojFijo


def test_alta_se_guarda_y_se_lee_con_su_ficha():
    s = crear_servicios_sql("sqlite://", con_solicitudes=False,
                            reloj=RelojFijo(datetime(2026, 11, 16, 10)))
    ficha = FichaDeAlta(date(2009, 5, 20), "ana@correo.com", "8112345678", True, True)
    socio = s.clases.dar_de_alta_socio("Ana", ficha, ciudad="Monterrey")
    leido = s.clases.obtener_socio(socio.id)
    assert leido.ficha == ficha and leido.ciudad == "Monterrey"
    assert [x.id for x in s.clases.listar_socios()][-1] == "FIT-C041"
    assert s.clases.obtener_socio("FIT-C001").ficha is None  # socios del paquete


def test_base_existente_sin_la_tabla_nueva_la_recibe_al_arrancar():
    motor = crear_motor("sqlite://")
    viejas = [t for t in Base.metadata.sorted_tables if t.name != "fichas_socio"]
    Base.metadata.create_all(motor, tables=viejas)  # como la base de Render antes de 0.8.0
    assert "fichas_socio" not in inspect(motor).get_table_names()
    crear_fabrica_sesiones(motor)
    assert "fichas_socio" in inspect(motor).get_table_names()
    assert {c["name"] for c in inspect(motor).get_columns("socios")} == {
        c.name for c in SocioRow.__table__.columns
    }
