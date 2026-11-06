# ADR-007: Los errores de dominio llevan su código HTTP

**Estado:** Aceptada, implementada

## Contexto
El BRD define qué respuesta corresponde a cada fallo (Anexo B): 409 para conflictos de estado, cupo o membresía activa, y 422 para reglas de negocio. FastAPI usa 422 por defecto para formato inválido, que aquí significa otra cosa.

## Alternativas
- **`try/except` con `HTTPException` en cada endpoint:** repetitivo y se puede olvidar un caso.
- **Que el dominio conozca HTTP:** acopla el negocio a la API.
- **Excepciones de dominio con un atributo de código y un manejador único.**

## Decisión
`ErrorDeDominio` lleva `codigo_http` y `regla`. `ReglaDeNegocioViolada` es 422; `ConflictoDeEstado` es 409 (con `TransicionInvalida`, `CupoAgotado`, `MembresiaActivaExistente`); `NoEncontrado` es 404. `main.py` registra un manejador que devuelve `{detail, regla, error}`. El formato inválido se reasigna a 400.

| Código | Cuándo |
|---|---|
| 201 | Se crea una solicitud |
| 200 | Lecturas y cambios de estado |
| 400 | Formato inválido (tipos, campos) |
| 404 | La solicitud, el socio o el plan no existe |
| 409 | Transición inválida, cupo agotado, membresía activa existente |
| 422 | Regla de negocio violada (RN-37, RN-38, RN-08, RN-09, RN-10) |

## Consecuencias
- Beneficio: la API responde siempre con el mismo formato y la regla violada; un error nuevo no exige tocar los endpoints.
- Costo: el dominio lleva un número HTTP; se acepta por ser un detalle del contrato del BRD.

## Trazabilidad
Anexo B del BRD · RN-03, RN-08, RN-09, RN-10, RN-37, RN-38, RN-39, RN-41 · `tests/integration/test_api.py`
