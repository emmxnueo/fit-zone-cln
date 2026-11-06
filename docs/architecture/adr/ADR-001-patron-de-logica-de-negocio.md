# ADR-001: Patrón de lógica de negocio

**Estado:** Aceptada

## Contexto
FitZone tiene más de diez reglas que dependen unas de otras (membresía vigente, cupo, cancelaciones, tolerancia de retraso, no-shows, lista de espera y permisos por rol) y sus límites pueden cambiar. Además debe generar reportes de tráfico y demanda (BN-04, BN-05).

## Alternativas
- **Transaction Script:** un procedimiento por operación. Rápido, pero repite las reglas y cambiar un límite obliga a corregir varios lugares.
- **Table Module:** reglas por tabla. Sirve para reportes, no para reglas que cruzan varias tablas.
- **Domain Model:** cada regla vive en el concepto al que pertenece. Exige más diseño al inicio.

## Decisión
Domain Model para membresías, reservas, lista de espera, no-shows y autorizaciones; Table Module solo para los reportes. Transaction Script se descarta.

## Consecuencias
- Beneficio: cada regla se escribe en un solo lugar; menos estados inválidos.
- Costo: más diseño inicial y el equipo debe dominar agregados y repositorios.
- En el código: `SolicitudDeMembresia` es el agregado que protege sus invariantes.
- Riesgo: los reportes dependen de cómo se guarden los datos.

## Trazabilidad
BN-02, BN-04, BN-05, BN-08 · US-08, US-09, US-11, US-12 · `src/domain/`
