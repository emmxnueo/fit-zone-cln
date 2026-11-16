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


_SALON = {1: "Salón 1", 5: "Salón 2", 10: "Salón 3"}  # RN-11: la capacidad la fija el salón


def crear_clase(api, en=timedelta(days=1), capacidad=1, categoria="ESTANDAR"):
    inicio = RelojDelSistema().ahora() + en
    r = api.post("/clases", json={
        "nombre": "Yoga", "categoria": categoria, "inicio": inicio.isoformat(),
        "salon": _SALON[capacidad], "instructor": "Ana Ruiz",
    })
    assert r.status_code == 201 and r.json()["capacidad"] == capacidad
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
    inicio = (RelojDelSistema().ahora() + timedelta(days=1)).replace(microsecond=0)
    cuerpo = {"nombre": "Yoga", "categoria": "ESTANDAR", "inicio": inicio.isoformat(),
              "instructor": "Ana Ruiz"}
    assert api.post("/clases", json={**cuerpo, "salon": "Salón 9"}).status_code == 400
    assert api.post("/clases", json=cuerpo).status_code == 400  # falta el salón
    assert api.post("/clases", json={**cuerpo, "salon": "Salón 1", "categoria": "X"}).status_code == 400
    con_zona = {**cuerpo, "salon": "Salón 1", "inicio": inicio.isoformat() + "Z"}
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


def test_ingreso_y_tolerancia_con_el_reloj(api_reloj):
    api, reloj = api_reloj
    a, b = (con_membresia(api, s) for s in NORMALES[:2])
    inicio = reloj.ahora() + timedelta(hours=2)
    clase = api.post("/clases", json={
        "nombre": "Yoga", "categoria": "ESTANDAR", "inicio": inicio.isoformat(),
        "salon": "Salón 2", "instructor": "Ana Ruiz",
    }).json()
    reservar(api, clase, a)
    reservar(api, clase, b)
    assert api.post(f"/socios/{b}/ingresos").status_code == 201
    reloj.fijar(inicio + timedelta(minutes=11))
    r = api.post("/clases/procesar-reloj")
    assert r.status_code == 200 and r.json()["no_shows"] == 1
    assert api.get(f"/clases/{clase['id']}").json()["ya_inicio"] is True
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
        "salon": "Salón 1", "instructor": "Ana Ruiz",
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


# --- Correcciones de la versión 0.7.1 -----------------------------------------
import pytest  # noqa: E402


def test_el_reloj_no_se_adelanta_pero_se_puede_repetir(api_reloj):
    api, reloj = api_reloj
    futuro = (reloj.ahora() + timedelta(hours=3)).isoformat()
    r = api.post("/clases/procesar-reloj", json={"ahora": futuro})
    assert r.status_code == 422 and "adelantar" in r.json()["detail"]
    pasado = (reloj.ahora() - timedelta(hours=1)).isoformat()
    assert api.post("/clases/procesar-reloj", json={"ahora": pasado}).status_code == 200


def test_no_se_crean_clases_en_el_pasado(api_reloj):
    api, reloj = api_reloj
    r = api.post("/clases", json={
        "nombre": "Yoga", "categoria": "ESTANDAR", "salon": "Salón 2", "instructor": "Ana Ruiz",
        "inicio": (reloj.ahora() - timedelta(minutes=1)).isoformat(),
    })
    assert r.status_code == 422 and "futuras" in r.json()["detail"]


def test_ya_inicio_se_calcula_con_el_reloj_del_negocio(api_reloj):
    api, reloj = api_reloj
    inicio = reloj.ahora() + timedelta(hours=1)
    clase = api.post("/clases", json={
        "nombre": "Spinning", "categoria": "ESTANDAR", "salon": "Salón 2", "instructor": "Luis Vega",
        "inicio": inicio.isoformat(),
    }).json()
    assert clase["ya_inicio"] is False
    reloj.fijar(inicio)
    assert api.get("/clases").json()[0]["ya_inicio"] is True


def test_sin_membresia_la_etiqueta_no_dice_incluida(api):
    clase = crear_clase(api)
    socio = NORMALES[0]
    etiqueta = api.get(f"/clases/{clase['id']}", params={"socio_id": socio}).json()["etiqueta"]
    assert etiqueta == "Necesitas una membresía vigente"
    assert reservar(api, clase, socio).json()["regla"] == "RN-13"


_CLASE = {"nombre": "Yoga", "categoria": "ESTANDAR", "salon": "Salón 2", "instructor": "Ana Ruiz"}


@pytest.mark.parametrize("campo,valor", [
    ("nombre", "   "), ("nombre", "<b>$$$</b>"), ("nombre", "Y"),
    ("instructor", ""), ("instructor", "Ana123"), ("instructor", "<script>"),
    ("salon", "@@@"), ("salon", "Salón 4"), ("salon", ""),
])
def test_formato_de_la_clase_es_400(api, campo, valor):
    inicio = (RelojDelSistema().ahora() + timedelta(days=1)).isoformat()
    r = api.post("/clases", json={**_CLASE, "inicio": inicio, campo: valor})
    assert r.status_code == 400, r.json()


def test_nombres_validos_se_normalizan(api):
    inicio = (RelojDelSistema().ahora() + timedelta(days=1)).isoformat()
    r = api.post("/clases", json={**_CLASE, "inicio": inicio, "nombre": "  HIIT   Pro 2 ",
                                  "instructor": " María  O'Neil "})
    assert r.status_code == 201
    assert (r.json()["nombre"], r.json()["instructor"]) == ("HIIT Pro 2", "María O'Neil")


def test_la_capacidad_la_fija_el_salon(api):
    """RN-11: capacidad fija por salón, independiente de instructor y horario."""
    assert api.get("/salones").json() == [
        {"nombre": "Salón 1", "capacidad": 1},
        {"nombre": "Salón 2", "capacidad": 5},
        {"nombre": "Salón 3", "capacidad": 10},
    ]
    inicio = (RelojDelSistema().ahora() + timedelta(days=1)).isoformat()
    for salon, capacidad in (("Salón 1", 1), ("Salón 2", 5), ("Salón 3", 10)):
        r = api.post("/clases", json={**_CLASE, "inicio": inicio, "salon": salon})
        assert (r.json()["salon"], r.json()["capacidad"]) == (salon, capacidad)
    r = api.post("/clases", json={**_CLASE, "inicio": inicio, "capacidad": 50})
    assert r.json()["capacidad"] == 5  # la capacidad enviada se ignora: manda el salón
