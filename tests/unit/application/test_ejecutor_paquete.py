import pytest

from src.application.ejecutor_paquete import aplicar_accion, ejecutar_casos
from tests.unit.application.test_servicio import armar


def test_accion_desconocida_se_rechaza():
    svc, _ = armar(solicitudes=[("O1", "S1", 1)])
    with pytest.raises(ValueError):
        aplicar_accion(svc, "O1", "inventada")


def test_tipo_de_prueba_desconocido_se_rechaza():
    svc, _ = armar(solicitudes=[("O1", "S1", 1)])
    with pytest.raises(ValueError):
        ejecutar_casos(svc, [{"caso_id": "X", "operacion_id": "O1", "tipo_prueba": "otro"}])
