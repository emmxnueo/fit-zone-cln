# ADR-003: Sanción por no-show

**Estado:** Aceptada (implementada en `Socio.registrar_falta`, ver ADR-008)

## Contexto
Con 3 faltas en un mismo mes calendario el socio no puede reservar durante 7 días naturales, y BN-02 y US-06 piden que sea automático. La entrevista (P7) incluía las sanciones entre lo que autoriza el Administrador, lo cual se contradecía. Como no existe otro caso de sanción, se resuelve a favor de la sanción automática.

## Alternativas
- **Bloqueo automático sin autorización:** cumple BN-02 y US-06. Es la elegida.
- **Solo manual:** respeta P7, pero depende de que alguien revise las faltas.
- **Detección automática con autorización del Administrador:** el socio seguiría reservando mientras no se autorice y el Administrador tendría más trabajo.

## Decisión
El agregado Socio registra cada falta y, al registrar la tercera del mismo mes, aplica la sanción de 7 días. Mientras esté vigente no puede reservar, pero conserva el acceso al gimnasio. El Administrador ya no autoriza sanciones (RN-26, RN-27, RN-28).

## Consecuencias
- Beneficio: cumple BN-02 y US-06 sin intervención manual, y la regla vive en un solo lugar.
- Costo: no hay mecanismo para levantar una sanción aplicada por error (mejora futura).
- Consistencia eventual: como la Reserva vive en la Clase, el Socio se entera del no-show por el evento `NoShowRegistrado`.

## Trazabilidad
BN-02 · US-06, US-14 · BPMN 12.3
