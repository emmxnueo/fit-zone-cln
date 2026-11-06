"""Textos para el usuario de la API: errores de formato y motivos de evaluación
en lenguaje claro, en lugar de los mensajes técnicos de las librerías."""
from __future__ import annotations

_CAMPOS = {
    "socio_id": "socio",
    "plan_id": "plan",
    "lineas": "planes",
    "categoria": "categoría",
    "pago_confirmado": "pago confirmado",
    "ahora": "fecha y hora",
    "salon": "salón",
}

_MENSAJES = {
    "missing": "Falta {campo}",
    "int_type": "{Campo} debe ser un número entero",
    "int_parsing": "{Campo} debe ser un número entero",
    "bool_type": "{Campo} debe ser true o false",
    "bool_parsing": "{Campo} debe ser true o false",
    "string_type": "{Campo} debe ser texto",
    "string_too_short": "{Campo} no puede estar vacío",
    "list_type": "{Campo} debe ser una lista",
    "date_from_datetime_parsing": "{Campo} debe ser una fecha, por ejemplo 2026-12-01",
    "date_parsing": "{Campo} debe ser una fecha, por ejemplo 2026-12-01",
    "datetime_from_date_parsing": "{Campo} debe ser una fecha y hora, por ejemplo 2026-12-01T18:00:00",
    "datetime_parsing": "{Campo} debe ser una fecha y hora, por ejemplo 2026-12-01T18:00:00",
    "timezone_naive": "{Campo} debe ir sin zona horaria, por ejemplo 2026-12-01T18:00:00",
}

MOTIVOS = {
    "socio_inactivo": "El socio no está activo",
    "sin_lineas": "La solicitud no tiene planes",
    "sin_validacion": "Falta la validación de Recepción",
    "socio_no_premium": "El socio no es Premium",
    "total_menor_a_1500": "El total es menor a 1500 MXN",
    "cortesia_activa": "Tiene una cortesía activa",
}


def _un_error(error: dict) -> str:
    if error["type"] == "json_invalid":
        return "El cuerpo de la petición no es un JSON válido"
    nombres = [str(parte) for parte in error["loc"] if isinstance(parte, str)]
    nombre = nombres[-1] if nombres and nombres[-1] not in ("body", "query", "path") else ""
    if not nombre:
        return "Falta el cuerpo de la petición"
    campo = _CAMPOS.get(nombre, nombre)
    if error["type"] == "enum":
        return f"{campo.capitalize()} debe ser uno de: {error['ctx']['expected']}"
    plantilla = _MENSAJES.get(error["type"], "{Campo} no es válido")
    return plantilla.format(campo=f"el campo {campo}", Campo=f"El campo {campo}")


def explicar_formato(errores: list[dict]) -> str:
    """Une los errores de validación en una sola frase, sin repetir."""
    return ". ".join(dict.fromkeys(_un_error(e) for e in errores))
