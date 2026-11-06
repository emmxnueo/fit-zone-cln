# ADR-008: Alcance del código

**Estado:** Aceptada

## Contexto
El BRD, los BPMN y la Actividad 3 cubren todo FitZone: membresías, acceso, reservas, lista de espera, no-shows, cancelación de clases, excepciones y reportes. El paquete de datos del PIA es genérico (actor, recurso, operación) y su ciclo de vida corresponde a la contratación de membresías (BN-09, BN-10). El tiempo del proyecto es limitado.

## Alternativas
- **Programar todo el negocio:** cubre el BRD completo, pero no alcanza con calidad, pruebas y despliegue.
- **Programar solo el módulo que ejercita el paquete, con DDD, Specification, State Machine, API y persistencia completos.**
- **Programar un poco de cada módulo:** todo queda superficial.

## Decisión
Se implementan tres módulos completos, con dominio, API, persistencia y pruebas:

1. **Contratación de membresías:** RN-37 a RN-41, junto con RN-03, RN-08, RN-09 y RN-10. Es la entrada al sistema y el módulo que ejercita el paquete del PIA.
2. **Clases, reservas, lista de espera, sanciones y cancelación de clases:** RN-05, RN-11, RN-13 a RN-31. Cubre BN-01, BN-02 y BN-03, los problemas centrales del negocio. El paquete no trae clases, así que este módulo usa datos de demostración propios.

3. **Reportes de afluencia y demanda:** RN-35 y RN-36, como Table Module (ADR-001). Son lecturas sobre datos que los otros módulos ya guardan.

El resto de las reglas se mantiene en el BRD, los BPMN y los ADR como análisis y diseño, y la [matriz de trazabilidad](../trazabilidad.md) marca cada regla como implementada, parcial o solo diseñada.

## Consecuencias
- Beneficio: el código refleja el problema de FitZone y conserva la verificación con los 120 casos y las 20 transiciones del paquete, con cobertura, CI y despliegue.
- Costo: excepciones, alta con edad y deslinde, cambio de plan y ajuste de aforo no tienen endpoints ni pruebas.
- Tiempo: lo que dispara el reloj (RN-17, RN-20) corre al llamar `POST /clases/procesar-reloj`; hace falta una tarea programada externa que lo invoque.
- Evolución natural: el siguiente módulo sería el de excepciones (RN-32 y RN-33), que reemplazaría el campo `aprobada` de congelar, dar de baja y cancelar clases.

## Trazabilidad
BN-01 a BN-05, BN-09, BN-10 · RN-05, RN-11, RN-13 a RN-31, RN-35 a RN-41 · US-01, US-02, US-04 a US-10, US-14, US-18 a US-22 · [diferencias-paquete-pia.md](../diferencias-paquete-pia.md)
