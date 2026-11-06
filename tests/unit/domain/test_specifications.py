from src.domain.specifications import (
    BeneficioDeReferencia, CupoDisponible, PlanesHabilitados, SinMembresiaActiva,
    SocioActivo, SocioPremium, SolicitudConLineas, SolicitudProcesable,
    SolicitudValidada,
)
from tests.unit.domain.helpers import contexto, plan, solicitud


def test_procesable_cumple_las_tres_condiciones():
    assert SolicitudProcesable().is_satisfied_by(contexto())


def test_procesable_falla_si_socio_inactivo():
    assert not SolicitudProcesable().is_satisfied_by(contexto(activo=False))


def test_procesable_falla_sin_lineas():
    assert not SolicitudProcesable().is_satisfied_by(contexto(solicitud(lineas=())))


def test_procesable_falla_sin_validacion():
    assert not SolicitudProcesable().is_satisfied_by(contexto(solicitud(validada=False)))


def test_and_or_not_combinan():
    ctx = contexto(activo=False)
    assert (SocioActivo() | SolicitudValidada()).is_satisfied_by(ctx)
    assert not (SocioActivo() & SolicitudValidada()).is_satisfied_by(ctx)
    assert (~SocioActivo()).is_satisfied_by(ctx)
    # los métodos nombrados equivalen a los operadores
    assert SolicitudConLineas().and_(SolicitudValidada()).is_satisfied_by(ctx)
    assert not SocioActivo().or_(SocioPremium()).is_satisfied_by(ctx)
    assert SocioActivo().not_().is_satisfied_by(ctx)


def test_repr_muestra_la_composicion():
    assert repr(SocioActivo() & ~SocioPremium()) == "(SocioActivo AND NOT SocioPremium)"
    assert repr(SocioActivo() | SocioPremium()) == "(SocioActivo OR SocioPremium)"


def test_beneficio_de_referencia_caso_positivo():
    s = solicitud(lineas=((("P1", "500"), 3),))  # 1500 exactos
    assert BeneficioDeReferencia().is_satisfied_by(contexto(s, premium=True))


def test_beneficio_falla_bajo_el_umbral():
    s = solicitud(lineas=((("P1", "499.99"), 3),))
    assert not BeneficioDeReferencia().is_satisfied_by(contexto(s, premium=True))


def test_beneficio_falla_si_no_es_premium():
    s = solicitud(lineas=((("P1", "500"), 4),))
    assert not BeneficioDeReferencia().is_satisfied_by(contexto(s, premium=False))


def test_beneficio_falla_con_cortesia_activa():
    s = solicitud(lineas=((("P1", "500"), 4),), cortesia=True)
    assert not BeneficioDeReferencia().is_satisfied_by(contexto(s, premium=True))


def test_planes_habilitados():
    s = solicitud()
    assert PlanesHabilitados().is_satisfied_by(contexto(s))
    assert not PlanesHabilitados().is_satisfied_by(
        contexto(s, planes={"P1": plan("P1", habilitado=False)}))
    assert not PlanesHabilitados().is_satisfied_by(contexto(s, planes={"X": plan("X")}))


def test_cupo_disponible():
    s = solicitud()
    assert CupoDisponible().is_satisfied_by(contexto(s, ocupacion={"P1": 4}))
    assert not CupoDisponible().is_satisfied_by(contexto(s, ocupacion={"P1": 5}))
    assert not CupoDisponible().is_satisfied_by(contexto(s, planes={"X": plan("X")}))


def test_sin_membresia_activa():
    assert SinMembresiaActiva().is_satisfied_by(contexto(activas=0))
    assert not SinMembresiaActiva().is_satisfied_by(contexto(activas=1))
