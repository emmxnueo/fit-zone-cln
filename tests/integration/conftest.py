import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import get_servicio
from src.api.main import app
from src.infrastructure.composicion import crear_servicio_en_memoria


@pytest.fixture
def api():
    """Cliente HTTP con un servicio nuevo (sin solicitudes) por cada prueba."""
    svc = crear_servicio_en_memoria(con_solicitudes=False)
    app.dependency_overrides[get_servicio] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()
