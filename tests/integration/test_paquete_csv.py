"""Ejecuta el paquete completo del PIA y lo contrasta con un ORÁCULO INDEPENDIENTE:
reglas escritas a mano sobre los CSV, sin usar Specifications ni el dominio."""
import csv
import tempfile
from decimal import Decimal
from pathlib import Path

from src.application.ejecutor_paquete import ejecutar_casos, ejecutar_transiciones
from src.infrastructure import ejecutar_paquete
from src.infrastructure.csv_loader import DATA_DIR, cargar_paquete, leer_csv
from src.infrastructure.ejecutar_paquete import fabrica_servicio


def _oraculo():
    actores = {r["actor_id"]: r for r in leer_csv("actores.csv")}
    catalogo = {r["recurso_id"]: r for r in leer_csv("catalogo.csv")}
    ops = {r["operacion_id"]: r for r in leer_csv("operaciones.csv")}
    lineas = {}
    for r in leer_csv("detalle_operaciones.csv"):
        lineas.setdefault(r["operacion_id"], []).append(r)
    info = {}
    for oid, o in ops.items():
        ls = lineas.get(oid, [])
        total = sum((Decimal(catalogo[l["recurso_id"]]["precio_mxn"]) * int(l["cantidad"])
                     for l in ls), Decimal("0"))
        a = actores[o["actor_id"]]
        info[oid] = {
            "procesable": a["activo"] == "1" and len(ls) > 0 and o["autorizado"] == "1",
            "beneficio": a["es_preferente"] == "1" and total >= 1500 and o["promocion_activa"] == "0",
            "planes_ok": all(catalogo[l["recurso_id"]]["habilitado"] == "1" for l in ls),
            "total": total,
        }
    return info


def test_el_paquete_se_carga_completo():
    p = cargar_paquete()
    assert len(p.socios) == 40 and len(p.planes) == 20 and len(p.solicitudes) == 60
    assert sum(len(s.lineas) for s in p.solicitudes.values()) == 117
    assert p.planes["FIT-P003"].duracion_meses == 6 and p.planes["FIT-P001"].duracion_meses == 1


def test_120_casos_coinciden_con_el_oraculo():
    oraculo = _oraculo()
    casos = leer_csv("casos_prueba.csv")
    resultados = ejecutar_casos(fabrica_servicio(), casos)
    assert len(resultados) == 120
    for r in resultados:
        clave = "procesable" if r.tipo_prueba == "validar_operacion" else "beneficio"
        esperado = "CUMPLE" if oraculo[r.operacion_id][clave] else "NO_CUMPLE"
        assert r.resultado == esperado, r.caso_id
        assert Decimal(r.total_mxn) == oraculo[r.operacion_id]["total"], r.caso_id


def test_20_transiciones_coinciden_con_el_oraculo():
    oraculo = _oraculo()
    resultados = ejecutar_transiciones(fabrica_servicio, leer_csv("transiciones_prueba.csv"))
    assert len(resultados) == 20
    for r in resultados:
        o = oraculo[r.operacion_id]
        if r.accion in ("completar", "saltar_estado"):
            esperado = ("SOLICITADA", 409)
        elif r.accion == "cancelar":
            esperado = ("CANCELADA", 200)
        elif o["procesable"] and o["planes_ok"]:
            # aprobar -> ACTIVA; repetir_aprobacion -> ACTIVA y la 2.ª se rechaza
            esperado = ("ACTIVA", 200 if r.accion == "aprobar" else 409)
        else:
            esperado = ("SOLICITADA", 422)
        assert (r.estado_final, r.codigo_http) == esperado, r.caso_id


def test_se_genera_la_evidencia_en_csv():
    with tempfile.TemporaryDirectory() as tmp:
        ejecutar_paquete.main(Path(tmp))
        with open(Path(tmp) / "resultados_casos.csv", encoding="utf-8-sig") as f:
            assert len(list(csv.DictReader(f))) == 120
        with open(Path(tmp) / "resultados_transiciones.csv", encoding="utf-8-sig") as f:
            assert len(list(csv.DictReader(f))) == 20


def test_los_datos_estan_donde_se_espera():
    assert (DATA_DIR / "casos_prueba.csv").exists()
