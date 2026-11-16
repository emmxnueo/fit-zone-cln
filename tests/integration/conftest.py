import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import get_servicio, get_servicio_clases, get_servicio_reportes
from src.api.main import app
from src.infrastructure.composicion import crear_servicios_en_memoria


@pytest.fixture
def api():
    """Cliente HTTP con un servicio nuevo (sin solicitudes) por cada prueba."""
    s = crear_servicios_en_memoria(con_solicitudes=False)
    app.dependency_overrides[get_servicio] = lambda: s.membresias
    app.dependency_overrides[get_servicio_clases] = lambda: s.clases
    app.dependency_overrides[get_servicio_reportes] = lambda: s.reportes
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def api_reloj():
    """Cliente con un reloj de pruebas que se puede avanzar (`reloj.fijar`)."""
    from datetime import datetime

    from tests.unit.domain.helpers import RelojFijo

    reloj = RelojFijo(datetime(2026, 12, 1, 8, 0))
    s = crear_servicios_en_memoria(con_solicitudes=False, reloj=reloj)
    app.dependency_overrides[get_servicio] = lambda: s.membresias
    app.dependency_overrides[get_servicio_clases] = lambda: s.clases
    app.dependency_overrides[get_servicio_reportes] = lambda: s.reportes
    yield TestClient(app), reloj
    app.dependency_overrides.clear()
