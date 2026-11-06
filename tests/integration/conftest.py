import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import get_servicio, get_servicio_clases
from src.api.main import app
from src.infrastructure.composicion import crear_servicios_en_memoria


@pytest.fixture
def api():
    """Cliente HTTP con un servicio nuevo (sin solicitudes) por cada prueba."""
    s = crear_servicios_en_memoria(con_solicitudes=False)
    app.dependency_overrides[get_servicio] = lambda: s.membresias
    app.dependency_overrides[get_servicio_clases] = lambda: s.clases
    yield TestClient(app)
    app.dependency_overrides.clear()
