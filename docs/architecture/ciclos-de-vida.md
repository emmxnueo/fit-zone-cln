# Ciclos de vida y secuencias

## 1. Membresía / solicitud de membresía (implementado)

Es la tabla `TRANSICIONES` de `src/domain/state_machine.py` (RN-41). Cualquier par estado-acción que no esté en la tabla se rechaza con 409.

```mermaid
stateDiagram-v2
  [*] --> SOLICITADA : crear solicitud
  SOLICITADA --> ACTIVA : activar [RN-37, RN-38, RN-03, RN-39]
  SOLICITADA --> CANCELADA : cancelar
  ACTIVA --> SUSPENDIDA : congelar [RN-09, aprobada por Administrador]
  SUSPENDIDA --> ACTIVA : descongelar
  ACTIVA --> VENCIDA : vencer [RN-04]
  SUSPENDIDA --> VENCIDA : vencer
  VENCIDA --> ACTIVA : renovar [RN-08, pago confirmado]
  ACTIVA --> CANCELADA : dar de baja [RN-10, aprobada por Administrador]
  SUSPENDIDA --> CANCELADA : dar de baja [RN-10]
  CANCELADA --> [*]
```

| Desde | Acción | Hacia | Evento |
|---|---|---|---|
| SOLICITADA | activar | ACTIVA | `MembresiaActivada` |
| SOLICITADA | cancelar | CANCELADA | `SolicitudCancelada` |
| ACTIVA | congelar | SUSPENDIDA | `MembresiaCongelada` |
| SUSPENDIDA | descongelar | ACTIVA | `MembresiaDescongelada` |
| ACTIVA, SUSPENDIDA | vencer | VENCIDA | `MembresiaVencida` |
| VENCIDA | renovar | ACTIVA | `MembresiaRenovada` |
| ACTIVA, SUSPENDIDA | dar de baja | CANCELADA | `MembresiaDadaDeBaja` |

Reglas del ciclo:
- **CANCELADA es final**: no sale ninguna acción.
- **Saltar un estado** (por ejemplo vencer una SOLICITADA) o **repetir una aprobación** devuelve 409 con `regla: RN-41`.
- **Falta una autorización o un pago** (congelar y dar de baja sin aprobación, renovar sin pago): primero se valida la transición (409) y después la regla (422, RN-09, RN-10 o RN-08).
- **El estado no cambia si el dominio rechaza**: el servicio no guarda ni publica nada.

> La Actividad 3 llamaba a este concepto `Membresía` con `afiliarSocio`. En el código la entidad que atraviesa el ciclo es la solicitud (ver [diferencias-paquete-pia.md](diferencias-paquete-pia.md)).

## 2. Reserva y lista de espera (implementado)

Es la tabla `TRANSICIONES_RESERVA` de `src/domain/state_machine.py`.

```mermaid
stateDiagram-v2
  direction LR
  state "Reserva" as R {
    [*] --> CONFIRMADA
    CONFIRMADA --> CANCELADA : cancelar con 1 h o más (RN-15)
    CONFIRMADA --> CANCELADA_TARDE : cancelar con menos de 1 h (RN-16)
    CONFIRMADA --> NO_SHOW : más de 10 min sin ingreso (RN-17)
  }
```

```mermaid
stateDiagram-v2
  direction LR
  state "Entrada de la lista de espera" as L {
    [*] --> EN_ESPERA
    EN_ESPERA --> OFERTADA : lugar por cancelación (RN-20)
    EN_ESPERA --> ASIGNADA : lugar por retraso, presente y elegible (RN-21)
    OFERTADA --> ASIGNADA : confirma en 15 min o menos (RN-20)
    OFERTADA --> EXPIRADA : no confirma (RN-20)
  }
```

Decisiones que el BRD no fija y que el código resuelve así:
- **Membresía vigente** es tener una membresía en estado `ACTIVA`. El código no guarda fecha de vencimiento (RN-04 sigue parcial); una `SUSPENDIDA` no reserva ni ingresa.
- **Clase iniciada:** ya no se reserva ni se cancela (409). Tampoco se hacen ofertas nuevas: desde ese momento los lugares solo se asignan por RN-21.
- **Lugar ofrecido:** sigue apartado hasta que la oferta se resuelva, y quien reserva con socios esperando entra a la lista, aunque quede un lugar libre (RN-19).
- **Confirmar una oferta** vuelve a exigir RN-13: si el socio perdió la elegibilidad se rechaza (422) y la oferta sigue hasta expirar.
- **Orden de validación** (BPMN 12.2): clase iniciada (409), elegibilidad (422), reserva o lista repetida (409, RN-24).
- **Fecha de la falta:** es la hora de inicio de la clase, para que el mes calendario (RN-26) no dependa de cuándo corra el reloj.
- **Sanción activa:** las faltas nuevas se acumulan sin extenderla (RN-28) y cuentan para la siguiente sanción si son del mismo mes.

## 3. Otros ciclos del BRD (diseñados, no programados)

```mermaid
stateDiagram-v2
  direction LR
  state "Clase" as C {
    [*] --> PROGRAMADA
    PROGRAMADA --> CANCELACION_SOLICITADA : instructor solicita (2 h o más, RN-29)
    CANCELACION_SOLICITADA --> CANCELADA : Administrador aprueba (RN-30)
    CANCELACION_SOLICITADA --> PROGRAMADA : Administrador rechaza (RN-30)
  }
```

```mermaid
stateDiagram-v2
  direction LR
  state "Solicitud de excepción" as X {
    [*] --> PENDIENTE : Recepción crea (RN-32)
    PENDIENTE --> APROBADA : Administrador (RN-33)
    PENDIENTE --> RECHAZADA : Administrador (RN-33)
  }
```

Una excepción ya resuelta no se resuelve dos veces (RN-33, 409). En el código, la aprobación del Administrador llega como el campo `aprobada` de `congelar` y `dar-de-baja`; el agregado `SolicitudExcepcion` completo no se programó.

## 4. Secuencia: activar una solicitud

```mermaid
sequenceDiagram
  autonumber
  actor Recepcion as Recepción
  participant API as POST /solicitudes/{id}/activar
  participant SV as ServicioDeMembresias
  participant REP as Repositorios (puertos)
  participant AG as SolicitudDeMembresia
  participant PUB as PublicadorDeEventos

  Recepcion->>API: activar
  API->>SV: activar(id)
  SV->>REP: obtener(id)
  REP-->>SV: solicitud (SOLICITADA)
  SV->>REP: socio, planes, vigentes_por_plan, vigentes_del_socio
  REP-->>SV: datos para el contexto
  SV->>AG: activar(ctx)
  AG->>AG: siguiente_estado(SOLICITADA, ACTIVAR)  (RN-41)
  AG->>AG: Specifications: procesable, planes habilitados, sin membresía activa, cupo
  alt alguna regla falla
    AG-->>SV: ErrorDeDominio (409 o 422)
    SV-->>API: propaga el error, no guarda ni publica
    API-->>Recepcion: 409 / 422 con regla RN-xx
  else todo cumple
    AG->>AG: estado = ACTIVA, registra MembresiaActivada
    SV->>REP: guardar(solicitud)
    SV->>PUB: publicar(pull_events())
    SV-->>API: solicitud ACTIVA
    API-->>Recepcion: 200 con estado ACTIVA
  end
```

## 5. Secuencia: congelar con aprobación del Administrador

```mermaid
sequenceDiagram
  autonumber
  actor Admin as Administrador
  participant API as POST /solicitudes/{id}/congelar
  participant SV as ServicioDeMembresias
  participant AG as SolicitudDeMembresia
  participant REP as RepositorioSolicitudes
  participant PUB as PublicadorDeEventos

  Admin->>API: { "aprobada": true }
  API->>SV: congelar(id, aprobada=true)
  SV->>REP: obtener(id)
  SV->>AG: congelar(True)
  AG->>AG: siguiente_estado(ACTIVA, CONGELAR)
  AG->>AG: aprobada? (RN-09)
  AG-->>SV: estado SUSPENDIDA, evento MembresiaCongelada
  SV->>REP: guardar
  SV->>PUB: publicar
  API-->>Admin: 200 SUSPENDIDA
  Note over AG,API: con aprobada=false el agregado lanza ReglaDeNegocioViolada (RN-09) y la API responde 422
```
