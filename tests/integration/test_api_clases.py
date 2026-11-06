"""API de clases, reservas, lista de espera, ingresos, sanciones y reportes."""
from datetime import datetime, timedelta

from src.api.dependencias import get_servicio_clases, get_servicio_reportes
from src.application.clases import ServicioDeClases
from src.application.reportes import ServicioDeReportes
from src.infrastructure.csv_loader import cargar_paquete
from src.infrastructure.reloj import RelojDelSistema

_P = cargar_paquete()
_ACTIVOS = [s for s in _P.socios.values() if s.activo]
NORMALES = [s.id for s in _ACTIVOS if not s.es_premium]
PREMIUM = next(s.id for s in _ACTIVOS if s.es_premium)
PLAN = next(p.id for p in _P.planes.values() if p.habilitado and p.cupo >= 5)


def con_membresia(api, socio):
    r = api.post("/solicitudes", json={
        "socio_id": socio, "validada": True, "lineas": [{"plan_id": PLAN, "cantidad": 1}],
    })
    assert api.post(f"/solicitudes/{r.json()['id']}/activar").status_code == 200
    return socio


def crear_clase(api, en=timedelta(days=1), capacidad=1, categoria="ESTANDAR"):
    inicio = RelojDelSistema().ahora() + en
    r = api.post("/clases", json={
        "nombre": "Yoga", "categoria": categoria, "inicio": inicio.isoformat(),
        "capacidad": capacidad,
    })
    assert r.status_code == 201
    return r.json()


def reservar(api, clase, socio):
    return api.post(f"/clases/{clase['id']}/reservas", json={"socio_id": socio})


def test_swagger_documenta_las_rutas_nuevas(api):
    rutas = api.get("/openapi.json").json()["paths"]
    assert "/clases/{clase_id}/reservas" in rutas
    assert "/clases/procesar-reloj" in rutas
    assert "/socios/{socio_id}/ingresos" in rutas


def test_dependencia_por_defecto_entrega_el_servicio_de_clases():
    assert isinstance(get_servicio_clases(), ServicioDeClases)


def test_formato_y_reglas_al_crear_clase(api):
    cuerpo = {"nombre": "Yoga", "categoria": "ESTANDAR", "inicio": "2026-12-01T18:00:00"}
    assert api.post("/clases", json={**cuerpo, "capacidad": 0}).status_code == 422
    assert api.post("/clases", json={**cuerpo, "capacidad": "diez"}).status_code == 400
    assert api.post("/clases", json={**cuerpo, "capacidad": 1, "categoria": "X"}).status_code == 400
    con_zona = {**cuerpo, "capacidad": 1, "inicio": "2026-12-01T18:00:00Z"}
    assert api.post("/clases", json=con_zona).status_code == 400


def test_reservar_y_lista_de_espera(api):
    a, b = (con_membresia(api, s) for s in NORMALES[:2])
    clase = crear_clase(api)
    r = reservar(api, clase, a)
    assert r.status_code == 201 and r.json()["resultado"] == "RESERVA_CONFIRMADA"
    assert r.json()["clase"]["lugares_libres"] == 0
    assert reservar(api, clase, a).status_code == 409
    r = reservar(api, clase, b)
    assert r.json()["resultado"] == "EN_LISTA_DE_ESPERA"
    r = reservar(api, clase, b)
    assert r.status_code == 409 and r.json()["regla"] == "RN-24"


def test_sin_membresia_es_422_y_sin_socio_es_404(api):
    clase = crear_clase(api)
    r = reservar(api, clase, NORMALES[0])
    assert r.status_code == 422 and r.json()["regla"] == "RN-13"
    assert reservar(api, clase, "NADIE").status_code == 404
    assert api.get("/clases/NADA").status_code == 404


def test_clase_premium_y_etiquetas(api):
    normal, premium = con_membresia(api, NORMALES[0]), con_membresia(api, PREMIUM)
    clase = crear_clase(api, categoria="PREMIUM", capacidad=5)
    assert reservar(api, clase, normal).status_code == 422
    assert reservar(api, clase, premium).status_code == 201
    url = f"/clases/{clase['id']}"
    assert api.get(url, params={"socio_id": premium}).json()["etiqueta"] == "Incluida en tu membresía"
    assert "Costo adicional" in api.get("/clases", params={"socio_id": normal}).json()[0]["etiqueta"]


def test_cancelar_ofrecer_y_confirmar(api):
    a, b = (con_membresia(api, s) for s in NORMALES[:2])
    clase = crear_clase(api)
    rid = reservar(api, clase, a).json()["id"]
    reservar(api, clase, b)
    r = api.post(f"/clases/{clase['id']}/reservas/{rid}/cancelar")
    assert r.status_code == 200 and r.json()["lista_espera"][0]["estado"] == "OFERTADA"
    assert api.post(f"/clases/{clase['id']}/reservas/{rid}/cancelar").status_code == 409
    assert api.post(f"/clases/{clase['id']}/reservas/NADA/cancelar").status_code == 404
    url = f"/clases/{clase['id']}/oferta/confirmar"
    assert api.post(url, json={"socio_id": a}).status_code == 409
    assert api.post(url, json={"socio_id": b}).json()["estado"] == "CONFIRMADA"


def test_cancelacion_tardia_aparece_como_falta(api):
    a = con_membresia(api, NORMALES[0])
    clase = crear_clase(api, en=timedelta(minutes=30))
    rid = reservar(api, clase, a).json()["id"]
    r = api.post(f"/clases/{clase['id']}/reservas/{rid}/cancelar")
    assert r.json()["reservas"][0]["estado"] == "CANCELADA_TARDE"
    faltas = api.get(f"/socios/{a}").json()["faltas"]
    assert [f["motivo"] for f in faltas] == ["CANCELACION_TARDIA"]


def test_ingreso_y_tolerancia_con_el_reloj(api):
    a, b = (con_membresia(api, s) for s in NORMALES[:2])
    clase = crear_clase(api, en=timedelta(hours=2))
    reservar(api, clase, a)
    reservar(api, clase, b)
    assert api.post(f"/socios/{b}/ingresos").status_code == 201
    ahora = datetime.fromisoformat(clase["inicio"]) + timedelta(minutes=11)
    r = api.post("/clases/procesar-reloj", json={"ahora": ahora.isoformat()})
    # la clase puede caer al día siguiente cerca de medianoche: entonces B no está presente
    assert r.status_code == 200 and r.json()["no_shows"] == 1
    assert api.post("/clases/procesar-reloj").status_code == 200
    eventos = [e["evento"] for e in api.get("/eventos").json()]
    assert "NoShowRegistrado" in eventos and "FaltaRegistrada" in eventos


def test_ingreso_sin_membresia_es_422(api):
    r = api.post(f"/socios/{NORMALES[0]}/ingresos")
    assert r.status_code == 422 and r.json()["regla"] == "RN-05"
    assert api.post("/socios/NADIE/ingresos").status_code == 404
    assert api.get("/socios/NADIE").status_code == 404


def test_reporte_de_afluencia(api):
    a = con_membresia(api, NORMALES[0])
    api.post(f"/socios/{a}/ingresos")
    hoy = RelojDelSistema().ahora().date().isoformat()
    r = api.get("/reportes/afluencia", params={"desde": hoy, "hasta": hoy})
    assert r.status_code == 200 and r.json()["total"] == 1
    assert len(r.json()["por_hora"]) == 24 and len(r.json()["por_dia"]) == 7


def test_reporte_de_afluencia_con_rango_invalido(api):
    r = api.get("/reportes/afluencia", params={"desde": "2026-11-02", "hasta": "2026-11-01"})
    assert r.status_code == 422 and r.json()["regla"] == "RN-35"
    assert api.get("/reportes/afluencia", params={"desde": "ayer", "hasta": "hoy"}).status_code == 400
    assert api.get("/reportes/afluencia").status_code == 400


def test_reporte_de_demanda(api):
    a, b = (con_membresia(api, s) for s in NORMALES[:2])
    clase = crear_clase(api)
    reservar(api, clase, a)
    reservar(api, clase, b)
    d = api.get("/reportes/demanda").json()[0]
    assert d["clase_id"] == clase["id"]
    assert d["ocupacion_pct"] == "100.00" and d["en_lista_de_espera"] == 1


def test_dependencia_por_defecto_entrega_el_servicio_de_reportes():
    assert isinstance(get_servicio_reportes(), ServicioDeReportes)


def clase_de_instructor(api, en=timedelta(days=1)):
    inicio = RelojDelSistema().ahora() + en
    return api.post("/clases", json={
        "nombre": "Yoga", "categoria": "ESTANDAR", "inicio": inicio.isoformat(),
        "capacidad": 1, "instructor": "Ana Ruiz",
    }).json()


def test_cancelacion_de_clase_aprobada(api):
    a = con_membresia(api, NORMALES[0])
    clase = clase_de_instructor(api)
    reservar(api, clase, a)
    url = f"/clases/{clase['id']}/cancelacion"
    r = api.post(url, json={"instructor": "Ana Ruiz"})
    assert r.status_code == 200 and r.json()["estado"] == "CANCELACION_SOLICITADA"
    assert api.post(url, json={"instructor": "Ana Ruiz"}).status_code == 409
    r = api.post(f"{url}/resolver", json={"aprobada": True})
    assert r.json()["estado"] == "CANCELADA"
    assert r.json()["reservas"][0]["estado"] == "CANCELADA"
    assert api.post(f"{url}/resolver", json={"aprobada": True}).status_code == 409
    assert api.get(f"/socios/{a}").json()["faltas"] == []
    evento = next(e for e in api.get("/eventos").json() if e["evento"] == "ClaseCancelada")
    assert evento["socios_a_notificar"] == [a]
    assert reservar(api, clase, a).status_code == 409


def test_cancelacion_de_clase_rechazada(api):
    clase = clase_de_instructor(api)
    url = f"/clases/{clase['id']}/cancelacion"
    api.post(url, json={"instructor": "Ana Ruiz"})
    r = api.post(f"{url}/resolver", json={"aprobada": False})
    assert r.json()["estado"] == "PROGRAMADA"


def test_solicitud_de_cancelacion_invalida(api):
    clase = clase_de_instructor(api, en=timedelta(minutes=90))
    url = f"/clases/{clase['id']}/cancelacion"
    r = api.post(url, json={"instructor": "Ana Ruiz"})
    assert r.status_code == 422 and r.json()["regla"] == "RN-29"
    assert api.post(url, json={"instructor": "Otro"}).status_code == 422
    assert api.post(url, json={}).status_code == 400
    assert api.post("/clases/NADA/cancelacion", json={"instructor": "Ana"}).status_code == 404
    assert api.post(f"{url}/resolver", json={"aprobada": "si"}).status_code == 400


def test_listar_socios(api):
    socios = api.get("/socios").json()
    assert len(socios) == 40 and socios[0]["id"] == "FIT-C001"


def test_la_interfaz_se_sirve_en_la_raiz(api):
    r = api.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Quattrocento Sans" in r.text and "Administrador" in r.text
