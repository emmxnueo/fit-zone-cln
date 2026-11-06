from datetime import date

from src.domain.entities import Plan, Socio
from src.domain.solicitud import SolicitudDeMembresia
from src.domain.specifications import ContextoSolicitud
from src.domain.value_objects import Dinero


def plan(id="P1", precio="500", cupo=5, habilitado=True):
    return Plan(id, f"Plan {id}", Dinero.de(precio), cupo, habilitado)


def solicitud(lineas=((("P1", "500"), 1),), validada=True, cortesia=False):
    s = SolicitudDeMembresia("O1", "S1", date(2026, 10, 1),
                             validada=validada, cortesia_activa=cortesia)
    for (pid, precio), cantidad in lineas:
        s.agregar_linea(plan(pid, precio), cantidad)
    return s


def contexto(s=None, activo=True, premium=False, planes=None, ocupacion=None, activas=0):
    s = s or solicitud()
    socio = Socio("S1", "Socio", es_premium=premium, activo=activo)
    planes = planes or {l.plan_id: plan(l.plan_id) for l in s.lineas}
    return ContextoSolicitud(s, socio, planes, ocupacion or {}, activas)
