"""API de alta de socios (POST /socios, BPMN 12.1, RN-01 y RN-02)."""
from datetime import date

from src.infrastructure.reloj import RelojDelSistema

HOY = RelojDelSistema().ahora().date()


def nacido_hace(anos):
    """1 de enero: a cualquier fecha del año ya cumplió `anos`."""
    return date(HOY.year - anos, 1, 1)


def datos(anos, completa=False, **extra):
    return {
        "nombre": "Ana López", "fecha_nacimiento": nacido_hace(anos).isoformat(),
        "correo": "ana@correo.com", "telefono": "8112345678",
        "deslinde_firmado": completa, "cuestionario_salud": completa, **extra,
    }


def test_alta_de_adulto_201(api):
    r = api.post("/socios", json=datos(30))
    assert r.status_code == 201
    assert r.json()["id"] == "FIT-C041"
    assert r.json()["ficha"]["correo"] == "ana@correo.com"
    assert api.get("/socios/FIT-C041").json()["nombre"] == "Ana López"


def test_menor_de_16_422_rn01(api):
    r = api.post("/socios", json=datos(15, completa=True))
    assert (r.status_code, r.json()["regla"]) == (422, "RN-01")


def test_16_sin_deslinde_422_rn02(api):
    r = api.post("/socios", json=datos(16))
    assert (r.status_code, r.json()["regla"]) == (422, "RN-02")


def test_17_con_deslinde_publica_el_evento(api):
    assert api.post("/socios", json=datos(17, completa=True)).status_code == 201
    assert "DeslindeFirmado" in [e["evento"] for e in api.get("/eventos").json()]


def test_ciudad_solo_monterrey_o_apodaca(api):
    assert api.post("/socios", json=datos(30, ciudad="Apodaca")).status_code == 201
    assert api.post("/socios", json=datos(30)).status_code == 201  # es opcional
    r = api.post("/socios", json=datos(30, ciudad="Guadalajara"))
    assert r.status_code == 400 and "ciudad" in r.json()["detail"]


def test_formato_invalido_400_en_espanol(api):
    r = api.post("/socios", json=datos(30, correo="sin-arroba"))
    assert r.status_code == 400
    assert "correo" in r.json()["detail"]
    r = api.post("/socios", json={"nombre": "Ana"})
    assert r.status_code == 400 and "fecha de nacimiento" in r.json()["detail"]


def test_flujo_completo_alta_solicitud_activacion(api):
    socio = api.post("/socios", json=datos(17, completa=True)).json()
    plan = next(p for p in api.get("/planes").json() if p["habilitado"] and p["cupo"] >= 1)
    sol = api.post("/solicitudes", json={
        "socio_id": socio["id"], "validada": True,
        "lineas": [{"plan_id": plan["id"], "cantidad": 1}],
    }).json()
    r = api.post(f"/solicitudes/{sol['id']}/activar")
    assert r.status_code == 200 and r.json()["estado"] == "ACTIVA"


def test_swagger_documenta_el_alta(api):
    ruta = api.get("/openapi.json").json()["paths"]["/socios"]["post"]
    assert "RN-01" in ruta["description"] and "201" in ruta["responses"]


# --- Formato de las entradas (400): nada de texto libre en el alta ----------
import pytest  # noqa: E402

_MALOS = [
    ("nombre", "   "), ("nombre", "A"), ("nombre", "!!!$$$"), ("nombre", "12345"),
    ("nombre", "<script>alert(1)</script>"), ("nombre", "Ana  ;DROP TABLE"),
    ("correo", "a@b.c"), ("correo", "a b@c.co"), ("correo", "sin-arroba"), ("correo", "a@@b.com"),
    ("telefono", "1234567"), ("telefono", "81123456789"), ("telefono", "81-ABC-5678"),
    ("fecha_nacimiento", "1800-01-01"), ("fecha_nacimiento", "2999-01-01"),
]


@pytest.mark.parametrize("campo,valor", _MALOS)
def test_entradas_invalidas_son_400(api, campo, valor):
    r = api.post("/socios", json=datos(30, **{campo: valor}))
    assert r.status_code == 400, r.json()
    assert r.json()["regla"] is None and r.json()["detail"]


def test_entradas_validas_se_normalizan(api):
    r = api.post("/socios", json=datos(
        30, nombre="  María   José O'Neil-Garza ", correo=" Ana.Lopez@Correo.COM ",
        telefono="+52 (81) 1234-5678",
    ))
    assert r.status_code == 201
    socio = r.json()
    assert socio["nombre"] == "María José O'Neil-Garza"
    assert socio["ficha"]["correo"] == "ana.lopez@correo.com"
    assert socio["ficha"]["telefono"] == "8112345678"


def test_fecha_futura_es_formato_no_regla(api):
    r = api.post("/socios", json=datos(30, fecha_nacimiento="2999-01-01"))
    assert r.json()["detail"] == "La fecha de nacimiento no puede ser futura"
