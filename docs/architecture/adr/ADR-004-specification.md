# ADR-004: Reglas de negocio como Specifications

**Estado:** Aceptada, implementada

## Contexto
Las reglas RN-37 y RN-40 se componen de varias condiciones (socio activo, con líneas, validada; Premium, total mínimo, sin cortesía). El paquete del profesor pide verificarlas con composición AND y NOT, y el servicio además debe explicar qué condición falló.

## Alternativas
- **`if` anidados dentro de cada caso de uso:** simples, pero repiten la regla y no se pueden combinar ni probar por separado.
- **Funciones booleanas sueltas:** se prueban solas, pero no se componen con operadores ni se pueden mostrar como expresión.
- **Specification:** cada condición es un objeto con `is_satisfied_by(ctx)` y se combinan con `&`, `|` y `~`.

## Decisión
Patrón Specification en `src/domain/specifications.py`. Las condiciones simples (`SocioActivo`, `SolicitudConLineas`, `SolicitudValidada`, `SocioPremium`, `TotalMinimo`, `CortesiaActiva`, `PlanesHabilitados`, `CupoDisponible`, `SinMembresiaActiva`) se componen en `SolicitudProcesable` (RN-37) y `BeneficioDeReferencia` (RN-40). Todas evalúan un `ContextoSolicitud` inmutable.

## Consecuencias
- Beneficio: cada regla se prueba sola y compuesta; agregar una regla no toca las demás; el `repr` muestra la composición.
- Costo: más clases pequeñas que un `if`.
- El servicio repite la lista de condiciones de RN-37 para devolver los motivos (ver [solid.md](../solid.md)).

## Trazabilidad
RN-37, RN-38, RN-39, RN-40, RN-03 · US-21, US-22 · `tests/unit/domain/test_specifications.py`
