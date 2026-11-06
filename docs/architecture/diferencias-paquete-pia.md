# Paquete de datos del PIA y dominio de FitZone

El profesor entrega un paquete genérico (`actores.csv`, `catalogo.csv`, `operaciones.csv`, `detalle_operaciones.csv`, `casos_prueba.csv`, `transiciones_prueba.csv`). Este documento explica cómo se tradujo al dominio de FitZone y en qué difiere del BRD de la Unidad 2.

## 1. Traducción de conceptos

| Paquete | Campo | FitZone | En el código |
|---|---|---|---|
| actor | `actor_id`, `activo` | Socio | `Socio.id`, `Socio.activo` |
| actor | `es_preferente` | Socio Premium | `Socio.es_premium` |
| recurso (catálogo) | `recurso_id`, `precio_mxn` | Plan de membresía | `Plan.id`, `Plan.precio` (`Dinero`) |
| recurso | `capacidad_o_stock` | Cupo de contratación del plan | `Plan.cupo` (RN-39) |
| recurso | `habilitado` | Plan habilitado | `Plan.habilitado` |
| operación | `operacion_id` | Solicitud de membresía | `SolicitudDeMembresia.id` |
| operación | `autorizado` | Solicitud validada | `validada` |
| operación | `promocion_activa` | Cortesía activa | `cortesia_activa` |
| detalle | `recurso_id`, `cantidad` | Línea: plan y periodos contratados | `LineaSolicitud` |
| estados | SOLICITADA, ACTIVA, SUSPENDIDA, VENCIDA, CANCELADA | Ciclo de vida de la membresía | `EstadoMembresia` |

La duración del plan (1, 3, 6 o 12 meses) es un dato (`duracion_meses`), no un tipo distinto de plan.

## 2. Reglas del paquete frente al BRD

| Regla del paquete | Regla del BRD | Implementación |
|---|---|---|
| Validar actor activo, detalle no vacío y autorización | RN-37 | `SolicitudProcesable` (AND de tres Specifications) |
| Beneficio: preferente, total de 1500 MXN o más y sin promoción | RN-40 | `BeneficioDeReferencia` (AND con NOT) |
| Total de la operación | RN-38 | `SolicitudDeMembresia.total` con `Decimal` |
| Cupo del recurso | RN-39 | `CupoDisponible` |
| Transiciones válidas | RN-41 | `TRANSICIONES` |
| Un solo contrato activo por actor | RN-03 | `SinMembresiaActiva` (los 20 socios con dos solicitudes lo ejercitan) |

## 3. Diferencias que se resolvieron

| # | Diferencia | Decisión |
|---|---|---|
| 1 | El paquete carga solicitudes con planes deshabilitados | Se pueden crear y se rechazan al activar con un error claro (422, RN-38), en vez de impedir cargarlas |
| 2 | 20 socios tienen dos solicitudes | Sus transiciones se ejecutan cada una sobre un estado nuevo (`fabrica_servicio`) para que no choquen entre sí por RN-03 |
| 3 | El paquete usa `autorizado` y el BRD habla de validación | Se usa `validada`, que expresa mejor lo que verifica Recepción |
| 4 | El paquete no trae edad, deslinde, clases ni reservas | RN-01 y RN-02 quedan analizadas pero no programadas. Las reservas sí se programaron, con clases de demostración propias que no vienen del paquete ([ADR-008](adr/ADR-008-alcance-del-codigo.md)) |
| 5 | RN-40 no sale de la entrevista, es una regla ilustrativa del paquete | Se documenta como tal en el BRD |
| 6 | El paquete incluye planes de 6 meses; el BRD solo reconoce mensual, trimestral y anual | Se conserva el dato del paquete; el catálogo oficial del negocio sigue siendo el del BRD |

El detalle de los refinamientos del BRD respecto a la Unidad 2 está en su Anexo B.
