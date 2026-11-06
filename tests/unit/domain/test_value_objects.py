from decimal import Decimal

import pytest

from src.domain.errors import ReglaDeNegocioViolada
from src.domain.value_objects import Cantidad, Dinero, LineaSolicitud


def test_dinero_usa_decimal_con_dos_decimales():
    assert Dinero.de("474").monto == Decimal("474.00")
    assert Dinero.de("0.1") + Dinero.de("0.2") == Dinero.de("0.30")


def test_dinero_rechaza_float_y_negativos():
    with pytest.raises(TypeError):
        Dinero(0.1)
    with pytest.raises(ReglaDeNegocioViolada):
        Dinero.de("-1")


@pytest.mark.parametrize("valor", [0, -3])
def test_cantidad_menor_a_uno_se_rechaza(valor):
    with pytest.raises(ReglaDeNegocioViolada) as e:
        Cantidad(valor)
    assert e.value.regla == "RN-38"


@pytest.mark.parametrize("valor", [1.5, "2", True])
def test_cantidad_debe_ser_entero(valor):
    with pytest.raises(ReglaDeNegocioViolada):
        Cantidad(valor)


def test_subtotal_es_precio_por_cantidad():
    linea = LineaSolicitud("P1", Dinero.de("474.00"), Cantidad(3))
    assert linea.subtotal == Dinero.de("1422.00")
