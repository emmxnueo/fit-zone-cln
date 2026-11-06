import pytest

from src.domain.errors import TransicionInvalida
from src.domain.state_machine import (
    TRANSICIONES, AccionMembresia as A, EstadoMembresia as E,
    acciones_permitidas, siguiente_estado,
)


@pytest.mark.parametrize("desde,accion,hacia", [(d, a, h) for (d, a), h in TRANSICIONES.items()])
def test_cada_transicion_valida(desde, accion, hacia):
    assert siguiente_estado(desde, accion) == hacia


def test_todo_par_fuera_de_la_tabla_se_rechaza():
    for estado in E:
        for accion in A:
            if (estado, accion) not in TRANSICIONES:
                with pytest.raises(TransicionInvalida) as e:
                    siguiente_estado(estado, accion)
                assert e.value.codigo_http == 409 and e.value.regla == "RN-41"


def test_cancelada_es_estado_final():
    assert acciones_permitidas(E.CANCELADA) == []


def test_solicitada_solo_activa_o_cancela():
    assert set(acciones_permitidas(E.SOLICITADA)) == {A.ACTIVAR, A.CANCELAR}
