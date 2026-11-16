"""RN-11: catálogo de salones con capacidad fija."""
import pytest

from src.domain.errors import ReglaDeNegocioViolada
from src.domain.salones import SALONES, salon


def test_tres_salones_con_capacidad_1_5_y_10():
    assert [(s.nombre, s.capacidad) for s in SALONES.values()] == [
        ("Salón 1", 1), ("Salón 2", 5), ("Salón 3", 10),
    ]


def test_salon_inexistente_es_422_rn11():
    with pytest.raises(ReglaDeNegocioViolada) as e:
        salon("Salón 9")
    assert (e.value.regla, e.value.codigo_http) == ("RN-11", 422)
