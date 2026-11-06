# ADR-005: Máquina de estados por tabla de transiciones

**Estado:** Aceptada, implementada

## Contexto
La solicitud de membresía pasa por SOLICITADA, ACTIVA, SUSPENDIDA, VENCIDA y CANCELADA (RN-41). Saltar un estado o repetir una aprobación debe rechazarse por conflicto (409), y el paquete trae 20 transiciones de prueba.

## Alternativas
- **Comparaciones de estado dentro de cada método:** fáciles al inicio, pero las transiciones válidas quedan repartidas y hay que leer todo para saber cuáles existen.
- **Patrón State (una clase por estado):** expresivo, pero con cinco estados y siete acciones genera muchas clases para reglas que son datos.
- **Tabla `(estado, acción) → estado`:** una sola estructura que se lee y se prueba completa.

## Decisión
`TRANSICIONES` en `src/domain/state_machine.py`, con `siguiente_estado()` como única forma de cambiar de estado. Todo par fuera de la tabla lanza `TransicionInvalida` (409, regla RN-41). Cada método del agregado llama primero a la tabla y después valida sus reglas propias (RN-09, RN-10, RN-08 con 422). CANCELADA es estado final.

## Consecuencias
- Beneficio: las 9 transiciones válidas se ven de un vistazo; la prueba recorre todos los pares y comprueba que los demás fallan.
- Costo: la tabla no guarda lógica; las reglas extra viven en el agregado.
- Agregar un estado o una acción es agregar filas a la tabla y una prueba.

## Trazabilidad
RN-41, RN-09, RN-10, RN-08 · US-16, US-17, US-21 · `tests/unit/domain/test_state_machine.py`
