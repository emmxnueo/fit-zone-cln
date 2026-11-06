# Architecture Decision Records

Cada ADR tiene contexto, alternativas, decisión, consecuencias y trazabilidad.

| ADR | Decisión | Estado | Origen |
|---|---|---|---|
| [ADR-001](ADR-001-patron-de-logica-de-negocio.md) | Domain Model como patrón de lógica de negocio; Table Module solo en reportes | Aceptada | Actividad 3 (U2) |
| [ADR-002](ADR-002-lista-de-espera-automatica.md) | Lista de espera automática con dos casos de asignación | Aceptada, implementada | Actividad 3 (U2) |
| [ADR-003](ADR-003-sancion-por-no-show.md) | Sanción por no-show automática, aplicada por el Socio | Aceptada, implementada | Actividad 3 (U2) |
| [ADR-004](ADR-004-specification.md) | Reglas de negocio como Specifications combinables | Aceptada, implementada | PIA |
| [ADR-005](ADR-005-state-machine-por-tabla.md) | Máquina de estados definida por tabla de transiciones | Aceptada, implementada | PIA |
| [ADR-006](ADR-006-puertos-y-adaptadores.md) | Puertos y adaptadores; repositorios en memoria y SQL | Aceptada, implementada | PIA |
| [ADR-007](ADR-007-errores-de-dominio-a-http.md) | Los errores de dominio llevan su código HTTP | Aceptada, implementada | PIA |
| [ADR-008](ADR-008-alcance-del-codigo.md) | Alcance del código: membresías, reservas, lista de espera y sanciones | Aceptada | PIA |

Los ADR-001 a ADR-003 vienen de la Unidad 2 y conservan su numeración, porque el BRD los cita (RN-03, RN-18, RN-16, RN-21, RN-23, RN-27). El ADR-002 y el ADR-003 se diseñaron en la Unidad 2 y su código entró al alcance en el PIA (ver ADR-008).
