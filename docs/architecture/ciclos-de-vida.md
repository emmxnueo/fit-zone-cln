# Ciclos de vida y secuencias

## 1. Membresía / solicitud de membresía (implementado)

Es la tabla `TRANSICIONES` de `src/domain/state_machine.py` (RN-41). Cualquier par estado-acción que no esté en la tabla se rechaza con 409.

```mermaid
---
config:
  theme: redux-color
---
stateDiagram-v2
  [*] --> SOLICITADA : crear solicitud
  SOLICITADA --> ACTIVA : activar [RN-03, RN-37, RN-38, RN-39]
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
---
config:
  theme: redux-color
---
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
---
config:
  theme: redux-color
---
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
---
config:
  theme: redux-color
---
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
---
config:
  theme: redux-color
---
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
---
config:
  theme: redux-color
---
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
  AG->>AG: Specifications: sin membresía activa, procesable, planes habilitados, cupo
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
---
config:
  theme: redux-color
---
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

## 6. Secuencia: reservar una clase

```mermaid
---
config:
  theme: redux-color
---
sequenceDiagram
  autonumber
  actor Socio
  participant API as POST /clases/{id}/reservas
  participant SV as ServicioDeClases
  participant REP as Repositorios (puertos)
  participant AG as Clase
  participant PUB as PublicadorDeEventos

  Socio->>API: socio_id
  API->>SV: reservar(clase_id, socio_id)
  SV->>REP: clase, socio, tiene_activa(socio_id)
  REP-->>SV: datos para ContextoReserva
  SV->>AG: reservar(ctx)
  AG->>AG: ¿la clase ya inició?
  AG->>AG: Specifications de elegibilidad (RN-13, RN-26)
  AG->>AG: ¿ya reservó o está en la lista? (RN-24)
  alt alguna regla falla
    AG-->>SV: ErrorDeDominio (409 o 422)
    SV-->>API: propaga el error, no guarda ni publica
    API-->>Socio: 409 / 422 con regla RN-xx
  else hay lugar y nadie espera
    AG->>AG: crea Reserva CONFIRMADA, registra ReservaConfirmada
    SV->>REP: guardar(clase)
    SV->>PUB: publicar(pull_events())
    API-->>Socio: 201 RESERVA_CONFIRMADA
  else clase llena o socios esperando
    AG->>AG: crea EntradaListaEspera (RN-19), registra SocioEnListaDeEspera
    SV->>REP: guardar(clase)
    SV->>PUB: publicar(pull_events())
    API-->>Socio: 201 EN_LISTA_DE_ESPERA
  end
```

## 7. Secuencia: cancelar y ofrecer el lugar

```mermaid
---
config:
  theme: redux-color
---
sequenceDiagram
  autonumber
  actor Socio
  actor Siguiente as Primer socio de la lista
  participant API as API de clases
  participant SV as ServicioDeClases
  participant AG as Clase
  participant REP as RepositorioClases
  participant PUB as PublicadorDeEventos
  participant SO as Socio (agregado)

  Socio->>API: POST /clases/{id}/reservas/{rid}/cancelar
  API->>SV: cancelar_reserva(clase_id, reserva_id)
  SV->>AG: cancelar_reserva(reserva, ahora)
  AG->>AG: ¿faltan menos de 1 h? (RN-15, RN-16)
  AG->>AG: libera el lugar, registra ReservaCancelada y LugarLiberado
  AG->>AG: ofrece al primero, registra LugarOfrecidoASocio (RN-20, RN-22)
  SV->>REP: guardar(clase)
  SV->>PUB: publicar(pull_events())
  opt cancelación tardía
    PUB->>SV: CancelacionTardiaRegistrada
    SV->>SO: registrar_falta(falta) (RN-25)
  end
  API-->>Socio: 200 con la clase actualizada
  alt confirma en 15 minutos o menos
    Siguiente->>API: POST /clases/{id}/oferta/confirmar
    API->>SV: confirmar_oferta(clase_id, socio_id)
    SV->>AG: confirmar_oferta(ctx)
    AG->>AG: valida oferta y RN-13, registra ReservaConfirmada
    SV->>REP: guardar(clase)
    API-->>Siguiente: 200 reserva CONFIRMADA
  else no confirma
    Note over SV,AG: el reloj llama expirar_oferta, registra OfertaDeLugarExpirada y ofrece al siguiente
  end
```

## 8. Secuencia: tolerancia, no-show y sanción

```mermaid
---
config:
  theme: redux-color
---
sequenceDiagram
  autonumber
  actor Reloj as Sistema (reloj)
  participant API as POST /clases/procesar-reloj
  participant SV as ServicioDeClases
  participant ING as RepositorioIngresos
  participant AG as Clase
  participant REP as RepositorioClases
  participant PUB as PublicadorDeEventos
  participant SO as Socio (agregado)

  Reloj->>API: ahora (opcional)
  API->>SV: procesar_reloj(ahora)
  loop cada clase
    SV->>AG: expirar_oferta(ahora)
    SV->>ING: presentes_el(día de la clase) (RN-18)
    ING-->>SV: socios presentes
    SV->>SV: filtra presentes que siguen elegibles (RN-21)
    SV->>AG: aplicar_tolerancia(ahora, presentes, asignables)
    alt pasaron más de 10 minutos y el titular no ingresó
      AG->>AG: reserva NO_SHOW, registra NoShowRegistrado y LugarLiberado (RN-17)
      opt hay alguien en la lista presente y elegible
        AG->>AG: confirma al primero, registra ReservaConfirmada (RN-21)
      end
    else llegó el titular o no ha pasado la tolerancia
      AG->>AG: no cambia nada
    end
    SV->>REP: guardar(clase)
    SV->>PUB: publicar(pull_events())
    PUB->>SV: NoShowRegistrado
    SV->>SO: registrar_falta(falta) (RN-25)
    opt tercera falta del mes calendario
      SO->>SO: consume las faltas y sanciona 7 días (RN-26 a RN-28)
      SV->>PUB: publicar SancionAplicada
    end
  end
  API-->>Reloj: 200 con el resumen
```
