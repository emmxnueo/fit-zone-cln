# ADR-002: Lista de espera automática

**Estado:** Aceptada (implementada en `src/domain/clase.py`, ver ADR-008)

## Contexto
Hoy Recepción lleva la lista en una libreta y hay quejas por falta de transparencia. Un lugar se libera por una cancelación (con o sin penalización según su anticipación) o por un retraso de más de 10 minutos. Para la cancelación, el negocio quiere ofrecer el lugar al primero de la lista con 15 minutos para confirmar; para el retraso, asignarlo de inmediato al primero que esté presente. La prioridad es reducir los lugares vacíos.

## Alternativas
- **Manual por Recepción:** no cambia nada; siguen la falta de transparencia y los lugares vacíos.
- **Una sola regla de 15 minutos para ambos casos:** simple, pero un lugar liberado por retraso tardaría en ocuparse con la clase ya iniciada.
- **Una sola regla de asignación inmediata:** no sirve para cancelaciones anticipadas, porque aún no hay socio presente y se perdería el orden de registro.

## Decisión
Sistema automático con dos casos. Por cancelación, se avisa al primero (FIFO) con 15 minutos para confirmar y, si no lo hace, pasa al siguiente. Por retraso, el lugar se asigna de inmediato al primero que esté presente. Recepción ya no interviene. (RN-19 a RN-24)

## Consecuencias
- Beneficio: orden claro, sin depender de Recepción, y los lugares por retraso se ocupan al instante.
- Costo: dos reglas de asignación que mantener; si nadie está presente, el lugar queda libre.
- Supuesto: la presencia es el ingreso registrado al gimnasio (RN-18), porque el BRD no define asistencia por clase. Mejora futura: registrarla en el salón.

## Trazabilidad
BN-01 · US-04, US-05, US-19, US-20 · BPMN 12.2 y 12.3
