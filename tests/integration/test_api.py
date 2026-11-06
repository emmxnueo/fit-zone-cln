"""Pruebas de la API REST: contrato, códigos HTTP (201/200/400/404/409/422) y
trazabilidad a las reglas RN-xx."""
from decimal import Decimal

from src.api import exportar_openapi
from src.api.dependencias import get_servicio
from src.application.servicio import ServicioDeMembresias
from src.infrastructure.csv_loader import cargar_paquete

_P = cargar_paquete()
PREMIUM = next(s.id for s in _P.socios.values() if s.es_premium and s.activo)
NORMAL = next(s.id for s in _P.socios.values() if not s.es_premium and s.activo)
INACTIVO = next(s.id for s in _P.socios.values() if not s.activo)
PLAN = next(p for p in _P.planes.values() if p.habilitado)
PLAN_OFF = next(p for p in _P.planes.values() if not p.habilitado)


def crear(api, socio=NORMAL, lineas=None, **extra):
    cuerpo = {"socio_id": socio, "validada": True,
              "lineas": lineas if lineas is not None else [{"plan_id": PLAN.id, "cantidad": 1}]}
    cuerpo.update(extra)
    return api.post("/solicitudes", json=cuerpo)


# --- sistema y documentación ------------------------------------------------
def test_health(api):
    assert api.get("/health").json() == {"status": "ok"}


def test_swagger_y_openapi_estan_activos(api):
    assert api.get("/docs").status_code == 200
    spec = api.get("/openapi.json").json()
    assert "/solicitudes" in spec["paths"]
    assert "/solicitudes/{solicitud_id}/activar" in spec["paths"]
    assert "409" in spec["paths"]["/solicitudes/{solicitud_id}/activar"]["post"]["responses"]


def test_exportar_openapi_escribe_el_archivo():
    ruta = exportar_openapi.main()
    assert ruta.exists() and '"openapi"' in ruta.read_text(encoding="utf-8")


def test_dependencia_por_defecto_entrega_el_servicio():
    assert isinstance(get_servicio(), ServicioDeMembresias)


def test_catalogo_de_planes(api):
    planes = api.get("/planes").json()
    assert len(planes) == 20
    p011 = next(p for p in planes if p["id"] == PLAN_OFF.id)
    assert p011["habilitado"] is False


# --- crear (201 / 400 / 404 / 422) ---------------------------------------
def test_crear_devuelve_201_con_total_decimal(api):
    r = crear(api, lineas=[{"plan_id": PLAN.id, "cantidad": 3}])
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["estado"] == "SOLICITADA"
    assert Decimal(cuerpo["total_mxn"]) == PLAN.precio.monto * 3
    assert set(cuerpo["acciones_permitidas"]) == {"activar", "cancelar"}


def test_crear_con_socio_o_plan_inexistente_es_404(api):
    assert crear(api, socio="NOPE").status_code == 404
    r = crear(api, lineas=[{"plan_id": "NOPE", "cantidad": 1}])
    assert r.status_code == 404


def test_cantidad_cero_es_422_por_rn38(api):
    r = crear(api, lineas=[{"plan_id": PLAN.id, "cantidad": 0}])
    assert r.status_code == 422 and r.json()["regla"] == "RN-38"


def test_formato_invalido_es_400(api):
    assert crear(api, lineas=[{"plan_id": PLAN.id, "cantidad": "abc"}]).status_code == 400
    assert crear(api, lineas=[{"plan_id": PLAN.id, "cantidad": 1.5}]).status_code == 400
    assert api.post("/solicitudes", json={}).status_code == 400
    assert api.post("/solicitudes", json={"socio_id": NORMAL, "validada": "si"}).status_code == 400


# --- consultas (200 / 404) ----------------------------------------------------
def test_consultar_y_listar(api):
    sid = crear(api).json()["id"]
    assert api.get(f"/solicitudes/{sid}").status_code == 200
    assert api.get("/solicitudes/NOPE").status_code == 404
    assert len(api.get("/solicitudes").json()) == 1
    assert api.get("/solicitudes", params={"estado": "ACTIVA"}).json() == []
    assert api.get("/solicitudes", params={"estado": "INVENTADO"}).status_code == 400


def test_procesable_explica_los_motivos(api):
    ok = crear(api).json()["id"]
    assert api.get(f"/solicitudes/{ok}/procesable").json() == {"cumple": True, "motivos": []}
    mal = crear(api, socio=INACTIVO, validada=False).json()["id"]
    r = api.get(f"/solicitudes/{mal}/procesable").json()
    assert r["cumple"] is False and r["motivos"] == ["socio_inactivo", "sin_validacion"]
    assert api.get("/solicitudes/NOPE/procesable").status_code == 404


def test_beneficio_de_referencia(api):
    sid = crear(api, socio=PREMIUM, lineas=[{"plan_id": PLAN.id, "cantidad": 4}]).json()["id"]
    assert PLAN.precio.monto * 4 >= 1500  # el dato del paquete lo permite
    assert api.get(f"/solicitudes/{sid}/beneficio-referencia").json()["cumple"] is True
    cort = crear(api, socio=PREMIUM, cortesia_activa=True,
                 lineas=[{"plan_id": PLAN.id, "cantidad": 4}]).json()["id"]
    r = api.get(f"/solicitudes/{cort}/beneficio-referencia").json()
    assert r == {"cumple": False, "motivos": ["cortesia_activa"]}


# --- ciclo de vida y reglas (200 / 409 / 422) -----------------------------
def test_activar_y_repetir_aprobacion(api):
    sid = crear(api).json()["id"]
    r = api.post(f"/solicitudes/{sid}/activar")
    assert r.status_code == 200 and r.json()["estado"] == "ACTIVA"
    repetido = api.post(f"/solicitudes/{sid}/activar")
    assert repetido.status_code == 409 and repetido.json()["regla"] == "RN-41"
    assert [e["evento"] for e in api.get("/eventos").json()] == ["MembresiaActivada"]


def test_activar_no_validada_es_422_por_rn37(api):
    sid = crear(api, validada=False).json()["id"]
    r = api.post(f"/solicitudes/{sid}/activar")
    assert r.status_code == 422 and r.json()["regla"] == "RN-37"
    assert api.get("/eventos").json() == []


def test_activar_con_plan_deshabilitado_es_422_por_rn38(api):
    sid = crear(api, lineas=[{"plan_id": PLAN_OFF.id, "cantidad": 1}]).json()["id"]
    r = api.post(f"/solicitudes/{sid}/activar")
    assert r.status_code == 422 and r.json()["regla"] == "RN-38"


def test_segunda_membresia_activa_es_409_por_rn03(api):
    a = crear(api).json()["id"]
    b = crear(api).json()["id"]
    assert api.post(f"/solicitudes/{a}/activar").status_code == 200
    r = api.post(f"/solicitudes/{b}/activar")
    assert r.status_code == 409 and r.json()["regla"] == "RN-03"


def test_activar_o_cancelar_inexistente_es_404(api):
    assert api.post("/solicitudes/NOPE/activar").status_code == 404
    assert api.post("/solicitudes/NOPE/cancelar").status_code == 404


def test_cancelar_y_no_se_puede_dos_veces(api):
    sid = crear(api).json()["id"]
    assert api.post(f"/solicitudes/{sid}/cancelar").json()["estado"] == "CANCELADA"
    assert api.post(f"/solicitudes/{sid}/cancelar").status_code == 409


def test_saltar_estado_es_409(api):
    sid = crear(api).json()["id"]
    r = api.post(f"/solicitudes/{sid}/vencer")  # SOLICITADA -> VENCIDA es ilegal
    assert r.status_code == 409 and r.json()["regla"] == "RN-41"


def test_congelar_descongelar_y_rn09(api):
    sid = crear(api).json()["id"]
    api.post(f"/solicitudes/{sid}/activar")
    sin = api.post(f"/solicitudes/{sid}/congelar", json={"aprobada": False})
    assert sin.status_code == 422 and sin.json()["regla"] == "RN-09"
    assert api.post(f"/solicitudes/{sid}/congelar", json={}).status_code == 400
    con = api.post(f"/solicitudes/{sid}/congelar", json={"aprobada": True})
    assert con.json()["estado"] == "SUSPENDIDA"
    assert api.post(f"/solicitudes/{sid}/descongelar").json()["estado"] == "ACTIVA"


def test_vencer_renovar_y_rn08(api):
    sid = crear(api).json()["id"]
    api.post(f"/solicitudes/{sid}/activar")
    assert api.post(f"/solicitudes/{sid}/vencer").json()["estado"] == "VENCIDA"
    sin = api.post(f"/solicitudes/{sid}/renovar", json={"pago_confirmado": False})
    assert sin.status_code == 422 and sin.json()["regla"] == "RN-08"
    con = api.post(f"/solicitudes/{sid}/renovar", json={"pago_confirmado": True})
    assert con.json()["estado"] == "ACTIVA"


def test_baja_requiere_administrador_rn10(api):
    sid = crear(api).json()["id"]
    api.post(f"/solicitudes/{sid}/activar")
    sin = api.post(f"/solicitudes/{sid}/dar-de-baja", json={"aprobada": False})
    assert sin.status_code == 422 and sin.json()["regla"] == "RN-10"
    con = api.post(f"/solicitudes/{sid}/dar-de-baja", json={"aprobada": True})
    assert con.json()["estado"] == "CANCELADA" and con.json()["acciones_permitidas"] == []
